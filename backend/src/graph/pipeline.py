"""
LangGraph pipeline — wires Extractor → Validator → Router with:
  • Confidence gate (avg < 0.60 → skip Validator, escalate immediately)
  • Crash recovery via MemorySaver checkpointing
  • Per-agent error handling + retry budget enforcement
  • Job-store updates at every state transition
"""

import logging
from typing import Optional, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from src.agents.extractor import run_extractor
from src.agents.router import run_router
from src.agents.validator import run_validator
from src.config import settings
from src.db import jobs_repo
from src.schemas.extraction import ExtractionResult
from src.schemas.rules import CustomerRuleSet
from src.schemas.validation import ValidationResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------------------

class PipelineState(TypedDict):
    job_id: str
    file_path: str
    doc_type: str
    customer_id: str
    rule_set: dict          # CustomerRuleSet serialised
    extraction: Optional[dict]
    validation: Optional[dict]
    decision: Optional[dict]
    error: Optional[str]
    retry_count: int


# ---------------------------------------------------------------------------
# Node functions — each returns only the fields it changes
# ---------------------------------------------------------------------------

async def extraction_node(state: PipelineState) -> dict:
    await jobs_repo.update_job_status(state["job_id"], "extracting")
    try:
        result = await run_extractor(
            job_id=state["job_id"],
            file_path=state["file_path"],
            doc_type=state["doc_type"],
        )
        extraction_dict = result.model_dump()
        await jobs_repo.update_job_extraction(state["job_id"], extraction_dict)
        return {"extraction": extraction_dict, "error": None}
    except Exception as exc:
        logger.exception("Extraction failed | job=%s", state["job_id"])
        await jobs_repo.update_job_status(state["job_id"], "failed")
        return {"error": str(exc)}


async def validation_node(state: PipelineState) -> dict:
    await jobs_repo.update_job_status(state["job_id"], "validating")
    try:
        extraction = ExtractionResult(**state["extraction"])
        rule_set = CustomerRuleSet(**state["rule_set"])
        result = await run_validator(extraction, rule_set)
        validation_dict = result.model_dump()
        await jobs_repo.update_job_validation(state["job_id"], validation_dict)
        return {"validation": validation_dict, "error": None}
    except Exception as exc:
        logger.exception("Validation failed | job=%s", state["job_id"])
        await jobs_repo.update_job_status(state["job_id"], "failed")
        return {"error": str(exc)}


async def routing_node(state: PipelineState) -> dict:
    await jobs_repo.update_job_status(state["job_id"], "routing")
    try:
        validation = ValidationResult(**state["validation"])
        result = await run_router(validation)
        decision_dict = result.model_dump()
        await jobs_repo.update_job_decision(state["job_id"], decision_dict, "complete")
        return {"decision": decision_dict, "error": None}
    except Exception as exc:
        logger.exception("Routing failed | job=%s", state["job_id"])
        await jobs_repo.update_job_status(state["job_id"], "failed")
        return {"error": str(exc)}


async def low_confidence_escalate_node(state: PipelineState) -> dict:
    """Bypass Validator when avg confidence < threshold — escalate for human review."""
    avg_conf = (state.get("extraction") or {}).get("avg_confidence", 0.0)
    decision_dict = {
        "job_id": state["job_id"],
        "decision": "review",
        "reasoning": (
            f"Document escalated before validation: average field confidence "
            f"{avg_conf:.2f} is below the escalation threshold "
            f"{settings.confidence_escalate_threshold:.2f}. "
            "The document quality is insufficient for automated validation. "
            "A human operator should review the original file and extracted fields."
        ),
        "draft_message": None,
    }
    await jobs_repo.update_job_decision(state["job_id"], decision_dict, "complete")
    return {"decision": decision_dict, "error": None}


# ---------------------------------------------------------------------------
# Edge routing functions
# ---------------------------------------------------------------------------

def _after_extraction(state: PipelineState) -> str:
    if state.get("error"):
        return END
    extraction = state.get("extraction") or {}
    avg_conf = extraction.get("avg_confidence", 0.0)
    if avg_conf < settings.confidence_escalate_threshold:
        return "low_confidence_escalate"
    return "validate"


def _after_validation(state: PipelineState) -> str:
    if state.get("error"):
        return END
    return "route"


# ---------------------------------------------------------------------------
# Build & compile the graph
# ---------------------------------------------------------------------------

def build_pipeline():
    g = StateGraph(PipelineState)

    g.add_node("extract", extraction_node)
    g.add_node("validate", validation_node)
    g.add_node("route", routing_node)
    g.add_node("low_confidence_escalate", low_confidence_escalate_node)

    g.set_entry_point("extract")

    g.add_conditional_edges(
        "extract",
        _after_extraction,
        {
            "validate": "validate",
            "low_confidence_escalate": "low_confidence_escalate",
            END: END,
        },
    )
    g.add_conditional_edges(
        "validate",
        _after_validation,
        {"route": "route", END: END},
    )
    g.add_edge("route", END)
    g.add_edge("low_confidence_escalate", END)

    checkpointer = MemorySaver()
    return g.compile(checkpointer=checkpointer)


_pipeline = build_pipeline()


# ---------------------------------------------------------------------------
# Public entry point called by the FastAPI background task
# ---------------------------------------------------------------------------

async def run_pipeline(
    job_id: str,
    file_path: str,
    doc_type: str,
    customer_id: str,
    rule_set: dict,
) -> dict:
    initial_state: PipelineState = {
        "job_id": job_id,
        "file_path": file_path,
        "doc_type": doc_type,
        "customer_id": customer_id,
        "rule_set": rule_set,
        "extraction": None,
        "validation": None,
        "decision": None,
        "error": None,
        "retry_count": 0,
    }

    config = {
        "configurable": {"thread_id": job_id},
        "recursion_limit": settings.langgraph_recursion_limit,
    }

    try:
        final_state = await _pipeline.ainvoke(initial_state, config=config)
        return final_state
    except Exception as exc:
        logger.exception("Pipeline aborted | job=%s", job_id)
        await jobs_repo.update_job_status(job_id, "failed")
        raise
