"""
Extractor Agent — faithful perception layer.

Accepts a raw document (PDF or image), converts it to base64 image(s),
and calls GPT-4o with a strict tool schema.  Returns an ExtractionResult
with a confidence score for every field.  If a field cannot be located,
value=None and confidence=0.0 — no guessing.
"""

import base64
import json
import logging
from pathlib import Path

import fitz  # PyMuPDF
from openai import AsyncAzureOpenAI, AsyncOpenAI

from src.config import settings
from src.schemas.extraction import ExtractionResult, FieldExtraction

logger = logging.getLogger(__name__)

# Build the appropriate client at import time based on config
if settings.use_azure_openai:
    client = AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )
    # Azure uses the deployment name in place of the model name
    _EXTRACTOR_MODEL = settings.azure_openai_deployment or settings.extractor_model
else:
    if not settings.openai_api_key:
        raise ValueError(
            "Set OPENAI_API_KEY for standard OpenAI, "
            "or set AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY for Azure OpenAI."
        )
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    _EXTRACTOR_MODEL = settings.extractor_model

# ---------------------------------------------------------------------------
# Tool schema — forces GPT-4o to emit every required field
# ---------------------------------------------------------------------------

_FIELD_SCHEMA = {
    "type": "object",
    "properties": {
        "value": {"type": ["string", "null"]},
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "0.0 = not found / very uncertain, 1.0 = absolutely certain",
        },
        "source_region": {
            "type": ["string", "null"],
            "description": "Where in the document this was found, e.g. 'page 1, header table'",
        },
    },
    "required": ["value", "confidence"],
}

EXTRACTION_TOOL = {
    "type": "function",
    "function": {
        "name": "extract_trade_document_fields",
        "description": (
            "Extract structured fields from a trade document image. "
            "Return null with confidence 0.0 for any field you cannot locate."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "consignee_name": _FIELD_SCHEMA,
                "hs_code": _FIELD_SCHEMA,
                "port_of_loading": _FIELD_SCHEMA,
                "port_of_discharge": _FIELD_SCHEMA,
                "incoterms": _FIELD_SCHEMA,
                "description_goods": _FIELD_SCHEMA,
                "gross_weight": _FIELD_SCHEMA,
                "invoice_number": _FIELD_SCHEMA,
            },
            "required": [
                "consignee_name",
                "hs_code",
                "port_of_loading",
                "port_of_discharge",
                "incoterms",
                "description_goods",
                "gross_weight",
                "invoice_number",
            ],
        },
    },
}

SYSTEM_PROMPT = """You are a specialized trade document field extractor.

CRITICAL RULES:
1. If you cannot locate a field value in the document, return null with confidence 0.0.
   Do NOT infer, estimate, or fill from context. Never hallucinate a value.
2. Confidence reflects how certain you are the extracted value is verbatim correct:
   - 0.9–1.0  : clearly printed, unambiguous
   - 0.7–0.89 : legible but some ambiguity (e.g. handwriting, partial occlusion)
   - 0.5–0.69 : inferred from context, possible but uncertain
   - 0.0–0.49 : not found or extremely uncertain
3. source_region should describe exactly where you found the field.
4. Always call extract_trade_document_fields with your results — no prose output."""


# ---------------------------------------------------------------------------
# PDF → JPEG images via PyMuPDF
# ---------------------------------------------------------------------------

def _pdf_to_b64_images(file_path: str, max_pages: int = 4) -> list[str]:
    """Render each PDF page as a JPEG and return a list of base64 strings."""
    doc = fitz.open(file_path)
    images: list[str] = []
    for page_num in range(min(len(doc), max_pages)):
        page = doc[page_num]
        # 1.5× zoom ≈ 108 DPI — good balance between quality and payload size
        mat = fitz.Matrix(1.5, 1.5)
        pix = page.get_pixmap(matrix=mat)
        jpeg_bytes = pix.tobytes("jpeg", jpg_quality=85)
        images.append(base64.b64encode(jpeg_bytes).decode("utf-8"))
    doc.close()
    return images


def _image_to_b64(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run_extractor(job_id: str, file_path: str, doc_type: str) -> ExtractionResult:
    ext = Path(file_path).suffix.lower()

    # Build the image content list for GPT-4o
    image_items: list[dict] = []

    if ext == ".pdf":
        b64_images = _pdf_to_b64_images(file_path)
        for b64 in b64_images:
            image_items.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{b64}",
                        "detail": "high",
                    },
                }
            )
    else:
        media_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                     ".png": "image/png", ".webp": "image/webp"}
        media_type = media_map.get(ext, "image/jpeg")
        b64 = _image_to_b64(file_path)
        image_items.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{b64}",
                    "detail": "high",
                },
            }
        )

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"This is a {doc_type} trade document. "
                        "Extract all required fields. "
                        "Call extract_trade_document_fields with the results."
                    ),
                },
                *image_items,
            ],
        }
    ]

    response = await client.chat.completions.create(
        model=_EXTRACTOR_MODEL,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        tools=[EXTRACTION_TOOL],
        tool_choice={
            "type": "function",
            "function": {"name": "extract_trade_document_fields"},
        },
        max_tokens=2000,
    )

    tool_calls = response.choices[0].message.tool_calls
    if not tool_calls:
        raise ValueError("GPT-4o did not return a tool call — cannot extract fields")

    raw = json.loads(tool_calls[0].function.arguments)

    def _field(data: dict) -> FieldExtraction:
        return FieldExtraction(
            value=data.get("value"),
            confidence=float(data.get("confidence", 0.0)),
            source_region=data.get("source_region"),
        )

    result = ExtractionResult(
        job_id=job_id,
        doc_type=doc_type,
        consignee_name=_field(raw["consignee_name"]),
        hs_code=_field(raw["hs_code"]),
        port_of_loading=_field(raw["port_of_loading"]),
        port_of_discharge=_field(raw["port_of_discharge"]),
        incoterms=_field(raw["incoterms"]),
        description_goods=_field(raw["description_goods"]),
        gross_weight=_field(raw["gross_weight"]),
        invoice_number=_field(raw["invoice_number"]),
    )
    result.avg_confidence = result.compute_avg_confidence()

    logger.info(
        "Extraction complete | job=%s avg_conf=%.2f", job_id, result.avg_confidence
    )
    return result
