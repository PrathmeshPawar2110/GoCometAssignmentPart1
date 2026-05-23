"""
Unit tests for the Extractor agent.
All LLM calls are mocked — no real API keys needed.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.schemas.extraction import ExtractionResult, FieldExtraction


MOCK_EXTRACTION_ARGS = {
    "consignee_name":    {"value": "Acme Imports Pvt Ltd", "confidence": 0.97, "source_region": "page 1, header"},
    "hs_code":           {"value": "8471.30", "confidence": 0.95, "source_region": "page 1, table row 3"},
    "port_of_loading":   {"value": "CNSHA", "confidence": 0.92, "source_region": "page 1, shipping details"},
    "port_of_discharge": {"value": "INNSA", "confidence": 0.94, "source_region": "page 1, shipping details"},
    "incoterms":         {"value": "CIF", "confidence": 0.90, "source_region": "page 1, terms section"},
    "description_goods": {"value": "Laptop Computers", "confidence": 0.88, "source_region": "page 2, cargo description"},
    "gross_weight":      {"value": "1250.50 KG", "confidence": 0.91, "source_region": "page 2, weight table"},
    "invoice_number":    {"value": "INV-20240001", "confidence": 0.96, "source_region": "page 1, top-right"},
}


def _make_mock_openai_response(args: dict) -> MagicMock:
    tool_call = MagicMock()
    tool_call.function.arguments = json.dumps(args)
    choice = MagicMock()
    choice.message.tool_calls = [tool_call]
    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.mark.asyncio
async def test_extractor_returns_all_required_fields():
    """Extractor must return all 8 required fields with confidence scores."""
    mock_response = _make_mock_openai_response(MOCK_EXTRACTION_ARGS)

    with (
        patch("src.agents.extractor.client") as mock_client,
        patch("src.agents.extractor._pdf_to_b64_images", return_value=["fakeb64"]),
    ):
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        from src.agents.extractor import run_extractor
        result = await run_extractor("job-001", "test.pdf", "BoL")

    assert isinstance(result, ExtractionResult)
    assert result.consignee_name.value == "Acme Imports Pvt Ltd"
    assert result.hs_code.value == "8471.30"
    assert result.port_of_loading.value == "CNSHA"
    assert result.port_of_discharge.value == "INNSA"
    assert result.incoterms.value == "CIF"
    assert result.gross_weight.value == "1250.50 KG"
    assert result.invoice_number.value == "INV-20240001"


@pytest.mark.asyncio
async def test_extractor_avg_confidence_computed():
    mock_response = _make_mock_openai_response(MOCK_EXTRACTION_ARGS)

    with (
        patch("src.agents.extractor.client") as mock_client,
        patch("src.agents.extractor._pdf_to_b64_images", return_value=["fakeb64"]),
    ):
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        from src.agents.extractor import run_extractor
        result = await run_extractor("job-002", "test.pdf", "BoL")

    assert 0.0 < result.avg_confidence <= 1.0


@pytest.mark.asyncio
async def test_extractor_null_field_has_zero_confidence():
    args = {**MOCK_EXTRACTION_ARGS, "hs_code": {"value": None, "confidence": 0.0}}
    mock_response = _make_mock_openai_response(args)

    with (
        patch("src.agents.extractor.client") as mock_client,
        patch("src.agents.extractor._pdf_to_b64_images", return_value=["fakeb64"]),
    ):
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        from src.agents.extractor import run_extractor
        result = await run_extractor("job-003", "test.pdf", "BoL")

    assert result.hs_code.value is None
    assert result.hs_code.confidence == 0.0


@pytest.mark.asyncio
async def test_extractor_confidence_clamped():
    """Confidence values > 1.0 reported by LLM must be clamped."""
    args = {**MOCK_EXTRACTION_ARGS, "incoterms": {"value": "CIF", "confidence": 1.5}}
    mock_response = _make_mock_openai_response(args)

    with (
        patch("src.agents.extractor.client") as mock_client,
        patch("src.agents.extractor._pdf_to_b64_images", return_value=["fakeb64"]),
    ):
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        from src.agents.extractor import run_extractor
        result = await run_extractor("job-004", "test.pdf", "BoL")

    assert result.incoterms.confidence == 1.0
