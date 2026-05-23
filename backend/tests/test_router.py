"""
Unit tests for the Router agent.
LLM calls are mocked — tests verify hard-constraint enforcement.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.schemas.routing import RouterDecision
from src.schemas.validation import FieldVerdict, ValidationResult


def _clean_validation() -> ValidationResult:
    return ValidationResult(
        job_id="job-r01",
        customer_id="ACME_001",
        verdicts={
            "consignee_name":    FieldVerdict(status="match", found="Acme Imports Pvt Ltd", expected="Acme Imports Pvt Ltd", reason="Fuzzy match"),
            "hs_code":           FieldVerdict(status="match", found="8471.30", expected="8471.30", reason="Exact match"),
            "port_of_discharge": FieldVerdict(status="match", found="INNSA", expected="INNSA", reason="Exact match"),
            "incoterms":         FieldVerdict(status="match", found="CIF", expected="CIF", reason="Exact match"),
        },
        has_uncertain=False,
        mismatch_count=0,
        uncertain_count=0,
    )


def _mismatch_validation() -> ValidationResult:
    return ValidationResult(
        job_id="job-r02",
        customer_id="ACME_001",
        verdicts={
            "hs_code": FieldVerdict(
                status="mismatch",
                found="9999.99",
                expected="8471.30, 8471.41, 8471.49",
                reason="Value not in allowed list",
            ),
        },
        has_uncertain=False,
        mismatch_count=1,
        uncertain_count=0,
    )


def _uncertain_validation() -> ValidationResult:
    return ValidationResult(
        job_id="job-r03",
        customer_id="ACME_001",
        verdicts={
            "hs_code": FieldVerdict(
                status="uncertain",
                found="8471?",
                expected="8471.30",
                reason="Low confidence 0.55",
            ),
        },
        has_uncertain=True,
        mismatch_count=0,
        uncertain_count=1,
    )


def _mock_router_response(decision: str, reasoning: str, draft: str = None):
    import json
    fn_call = MagicMock()
    fn_call.function.arguments = json.dumps(
        {"decision": decision, "reasoning": reasoning, "draft_message": draft}
    )
    msg = MagicMock()
    msg.tool_calls = [fn_call]
    choice = MagicMock()
    choice.message = msg
    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.mark.asyncio
async def test_router_approves_clean_document():
    validation = _clean_validation()
    mock_resp = _mock_router_response("approve", "All fields match, no issues found.")

    with patch("src.agents.router.llm_client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        from src.agents.router import run_router
        decision = await run_router(validation)

    assert decision.decision == "approve"
    assert len(decision.reasoning) > 10


@pytest.mark.asyncio
async def test_router_amends_on_mismatch():
    validation = _mismatch_validation()
    mock_resp = _mock_router_response(
        "amend",
        "HS code mismatch detected.",
        "Dear Supplier, please correct HS code from 9999.99 to 8471.30.",
    )

    with patch("src.agents.router.llm_client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        from src.agents.router import run_router
        decision = await run_router(validation)

    assert decision.decision == "amend"
    assert decision.draft_message is not None


@pytest.mark.asyncio
async def test_router_cannot_approve_uncertain():
    """Hard constraint: Router must not approve when has_uncertain=True."""
    validation = _uncertain_validation()
    # Simulate LLM incorrectly trying to approve
    mock_resp = _mock_router_response("approve", "Looks fine to me.")

    with patch("src.agents.router.llm_client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        from src.agents.router import run_router
        decision = await run_router(validation)

    # Hard rule must override the LLM's approve
    assert decision.decision != "approve"


@pytest.mark.asyncio
async def test_router_cannot_approve_with_mismatch():
    """Hard constraint: Router must not approve when mismatch_count > 0."""
    validation = _mismatch_validation()
    # LLM incorrectly tries to approve
    mock_resp = _mock_router_response("approve", "Everything seems fine.")

    with patch("src.agents.router.llm_client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        from src.agents.router import run_router
        decision = await run_router(validation)

    assert decision.decision == "amend"


@pytest.mark.asyncio
async def test_router_reviews_uncertain_document():
    validation = _uncertain_validation()
    mock_resp = _mock_router_response(
        "review",
        "Field hs_code has low confidence score, requiring human review.",
    )

    with patch("src.agents.router.llm_client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        from src.agents.router import run_router
        decision = await run_router(validation)

    assert decision.decision == "review"
