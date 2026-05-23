"""
Unit tests for the Validator agent.
All fuzzy-match LLM calls are mocked.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.schemas.extraction import ExtractionResult, FieldExtraction
from src.schemas.rules import CustomerRuleSet, FieldRule
from src.schemas.validation import ValidationResult


def _make_extraction(**overrides) -> ExtractionResult:
    defaults = {
        "job_id": "job-test",
        "doc_type": "BoL",
        "consignee_name":    FieldExtraction(value="Acme Imports Pvt Ltd", confidence=0.97),
        "hs_code":           FieldExtraction(value="8471.30", confidence=0.95),
        "port_of_loading":   FieldExtraction(value="CNSHA", confidence=0.92),
        "port_of_discharge": FieldExtraction(value="INNSA", confidence=0.94),
        "incoterms":         FieldExtraction(value="CIF", confidence=0.90),
        "description_goods": FieldExtraction(value="Laptop Computers", confidence=0.88),
        "gross_weight":      FieldExtraction(value="1250.50 KG", confidence=0.91),
        "invoice_number":    FieldExtraction(value="INV-20240001", confidence=0.96),
        "avg_confidence":    0.93,
    }
    defaults.update(overrides)
    return ExtractionResult(**defaults)


def _acme_ruleset() -> CustomerRuleSet:
    import json
    from pathlib import Path
    path = Path(__file__).parent.parent / "configs" / "rules" / "acme_imports.json"
    with open(path) as f:
        data = json.load(f)
    return CustomerRuleSet(**data)


@pytest.mark.asyncio
async def test_all_match_clean_document():
    """A clean document matching all rules should produce all-match verdicts."""
    extraction = _make_extraction()
    rule_set = _acme_ruleset()

    with patch("src.agents.validator._fuzzy_match", new=AsyncMock(return_value=(True, "Acme Imports Pvt Ltd"))):
        from src.agents.validator import run_validator
        result = await run_validator(extraction, rule_set)

    assert result.mismatch_count == 0
    assert result.uncertain_count == 0
    assert result.has_uncertain is False


@pytest.mark.asyncio
async def test_hs_code_mismatch_detected():
    """Wrong HS code must produce a mismatch verdict."""
    extraction = _make_extraction(hs_code=FieldExtraction(value="9999.99", confidence=0.95))
    rule_set = _acme_ruleset()

    with patch("src.agents.validator._fuzzy_match", new=AsyncMock(return_value=(True, "Acme Imports Pvt Ltd"))):
        from src.agents.validator import run_validator
        result = await run_validator(extraction, rule_set)

    assert result.verdicts["hs_code"].status == "mismatch"
    assert result.verdicts["hs_code"].found == "9999.99"
    assert result.mismatch_count >= 1


@pytest.mark.asyncio
async def test_low_confidence_field_is_uncertain():
    """Field with confidence below threshold must be marked uncertain, not approved."""
    extraction = _make_extraction(
        port_of_discharge=FieldExtraction(value="INNSA", confidence=0.50)
    )
    rule_set = _acme_ruleset()

    with patch("src.agents.validator._fuzzy_match", new=AsyncMock(return_value=(True, "Acme Imports Pvt Ltd"))):
        from src.agents.validator import run_validator
        result = await run_validator(extraction, rule_set)

    verdict = result.verdicts["port_of_discharge"]
    assert verdict.status == "uncertain"
    assert result.has_uncertain is True


@pytest.mark.asyncio
async def test_missing_required_field_is_uncertain():
    """A null required field must surface as uncertain, not silently pass."""
    extraction = _make_extraction(
        hs_code=FieldExtraction(value=None, confidence=0.0)
    )
    rule_set = _acme_ruleset()

    with patch("src.agents.validator._fuzzy_match", new=AsyncMock(return_value=(True, "Acme Imports Pvt Ltd"))):
        from src.agents.validator import run_validator
        result = await run_validator(extraction, rule_set)

    assert result.verdicts["hs_code"].status == "uncertain"
    assert result.uncertain_count >= 1


@pytest.mark.asyncio
async def test_fuzzy_mismatch_consignee():
    """A wrong consignee name must produce a mismatch via fuzzy path."""
    extraction = _make_extraction(
        consignee_name=FieldExtraction(value="Wrong Company Ltd", confidence=0.95)
    )
    rule_set = _acme_ruleset()

    with patch("src.agents.validator._fuzzy_match", new=AsyncMock(return_value=(False, None))):
        from src.agents.validator import run_validator
        result = await run_validator(extraction, rule_set)

    assert result.verdicts["consignee_name"].status == "mismatch"
