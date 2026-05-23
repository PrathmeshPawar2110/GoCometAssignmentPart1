"""
Router / Decision Agent — planner layer.

Reads the Validator's structured output and emits one of three decisions:
  approve  — all fields match, no uncertain fields → auto-store
  review   — uncertain fields present but no hard mismatches → human review
  amend    — one or more mismatches → draft amendment request email

The Router does NOT re-interpret the original document.  It reasons only
over the structured ValidationResult.  It must explain its decision.
"""

import json
import logging

from src.config import settings
from src.llm_client import get_model, llm_client
from src.schemas.routing import RouterDecision
from src.schemas.validation import ValidationResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool schema — OpenAI function-calling format
# ---------------------------------------------------------------------------

ROUTER_TOOL = {
    "type": "function",
    "function": {
        "name": "make_routing_decision",
        "description": "Emit a routing decision with full reasoning for the trade document.",
        "parameters": {
            "type": "object",
            "properties": {
                "decision": {
                    "type": "string",
                    "enum": ["approve", "review", "amend"],
                    "description": (
                        "approve = all clear, store automatically; "
                        "review = uncertain fields, flag for human; "
                        "amend = mismatches found, draft correction request"
                    ),
                },
                "reasoning": {
                    "type": "string",
                    "description": (
                        "Detailed explanation (3+ sentences) of why this decision "
                        "was reached, referencing specific fields."
                    ),
                },
                "draft_message": {
                    "type": ["string", "null"],
                    "description": (
                        "Professional amendment request email listing every "
                        "discrepancy with found vs expected values. "
                        "Required when decision == 'amend'. "
                        "Optional but encouraged when decision == 'review'."
                    ),
                },
            },
            "required": ["decision", "reasoning"],
        },
    },
}

SYSTEM_PROMPT = """You are a trade document routing agent for a customs brokerage.

Your job is to make a routing decision based on field-level validation results.

DECISION RULES (hard constraints — you cannot override these):
- APPROVE  : ALL verdicts are 'match', has_uncertain=false, mismatch_count=0
- REVIEW   : Any uncertain fields, but mismatch_count=0
- AMEND    : Any mismatches (mismatch_count > 0)

ADDITIONAL REQUIREMENTS:
1. You MUST write a reasoning that references the specific fields involved.
2. For AMEND decisions, draft_message MUST be a complete, professional email
   listing every discrepancy with the format:
     Field: <field_name>
     Found: <found_value>
     Expected: <expected_value>
     Action required: <what supplier must correct>
3. For REVIEW decisions, draft_message should summarise which fields are
   uncertain and why human review is needed.
4. Never produce a one-sentence reasoning — explain your thinking.

Call the make_routing_decision function with your output."""


async def run_router(validation: ValidationResult) -> RouterDecision:
    summary = {
        "job_id": validation.job_id,
        "customer_id": validation.customer_id,
        "mismatch_count": validation.mismatch_count,
        "uncertain_count": validation.uncertain_count,
        "has_uncertain": validation.has_uncertain,
        "verdicts": {
            field: {
                "status": v.status,
                "found": v.found,
                "expected": v.expected,
                "reason": v.reason,
            }
            for field, v in validation.verdicts.items()
        },
    }

    user_message = (
        f"Validation results for job {validation.job_id} "
        f"(customer: {validation.customer_id}):\n\n"
        f"{json.dumps(summary, indent=2)}\n\n"
        "Make a routing decision and explain it fully."
    )

    response = await llm_client.chat.completions.create(
        model=get_model(settings.router_model),
        max_tokens=1800,
        tools=[ROUTER_TOOL],
        tool_choice={"type": "function", "function": {"name": "make_routing_decision"}},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    tool_calls = response.choices[0].message.tool_calls
    if not tool_calls:
        raise ValueError("Router did not return a function call")

    data = json.loads(tool_calls[0].function.arguments)

    # Hard-enforce decision rules — the LLM must not override them
    actual_decision = data["decision"]
    if validation.mismatch_count > 0 and actual_decision == "approve":
        actual_decision = "amend"
        data["reasoning"] = (
            "[Auto-corrected: approve blocked by mismatch_count > 0] "
            + data.get("reasoning", "")
        )
    elif validation.has_uncertain and actual_decision == "approve":
        actual_decision = "review"
        data["reasoning"] = (
            "[Auto-corrected: approve blocked by uncertain fields] "
            + data.get("reasoning", "")
        )

    decision = RouterDecision(
        job_id=validation.job_id,
        decision=actual_decision,
        reasoning=data["reasoning"],
        draft_message=data.get("draft_message"),
    )

    logger.info(
        "Routing complete | job=%s decision=%s", validation.job_id, decision.decision
    )
    return decision
