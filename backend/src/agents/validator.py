"""
Validator Agent — verifier layer.

Compares the Extractor's structured output against a CustomerRuleSet.
Deterministic Python logic handles exact/regex matching.
An LLM is called only for fuzzy string matching (e.g. entity name variants).

The Validator has NO access to the original document — it only sees what
the Extractor reported.  This keeps trust boundaries clean and lets each
agent fail independently.
"""

import json
import logging
import re
from typing import Optional

from src.config import settings
from src.llm_client import get_model, llm_client
from src.schemas.extraction import ExtractionResult, FieldExtraction
from src.schemas.rules import CustomerRuleSet, FieldRule
from src.schemas.validation import FieldVerdict, ValidationResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fuzzy match via LLM — used only when rule.match_type == 'fuzzy'
# ---------------------------------------------------------------------------

async def _fuzzy_match(found: str, expected_values: list[str]) -> tuple[bool, Optional[str]]:
    """
    Ask the LLM whether `found` semantically matches any value in `expected_values`.
    Returns (is_match, closest_expected_value).
    """
    prompt = (
        f'Determine if the found value semantically matches any expected value.\n'
        f'Consider: abbreviations, legal entity variants (Pvt Ltd vs Private Limited), '
        f'common synonyms, OCR artefacts.\n\n'
        f'Found: "{found}"\n'
        f'Expected (any one acceptable): {json.dumps(expected_values)}\n\n'
        f'Respond with ONLY a JSON object like:\n'
        f'{{"match": true, "closest": "Acme Imports Pvt Ltd"}}\n'
        f'or\n'
        f'{{"match": false, "closest": null}}'
    )
    response = await llm_client.chat.completions.create(
        model=get_model(settings.validator_model),
        max_tokens=120,
        messages=[{"role": "user", "content": prompt}],
    )
    try:
        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences that gpt-4o sometimes adds
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        data = json.loads(raw)
        return bool(data.get("match", False)), data.get("closest")
    except (json.JSONDecodeError, IndexError, KeyError):
        logger.warning("Fuzzy match response could not be parsed; defaulting to no-match")
        return False, None


# ---------------------------------------------------------------------------
# Deterministic validation (exact / regex) — zero LLM cost
# ---------------------------------------------------------------------------

def _validate_deterministic(
    field_name: str,
    extraction: FieldExtraction,
    rule: FieldRule,
    low_threshold: float,
) -> FieldVerdict:
    expected_display = (
        rule.expected_value
        or (", ".join(rule.allowed_values) if rule.allowed_values else "present")
    )

    # 1. Field not found
    if extraction.value is None:
        if rule.required:
            return FieldVerdict(
                status="uncertain",
                found=None,
                expected=expected_display,
                reason="Field not found in document (value is null)",
            )
        return FieldVerdict(
            status="match",
            found=None,
            expected=None,
            reason="Field is not required and was not found",
        )

    # 2. Low confidence → uncertain (never silently approve)
    if extraction.confidence < low_threshold:
        return FieldVerdict(
            status="uncertain",
            found=extraction.value,
            expected=expected_display,
            reason=(
                f"Confidence {extraction.confidence:.2f} is below threshold "
                f"{low_threshold:.2f} — human review required"
            ),
        )

    found_val = extraction.value.strip()

    # 3. Exact match
    if rule.match_type == "exact":
        if rule.expected_value and found_val == rule.expected_value:
            return FieldVerdict(
                status="match", found=found_val,
                expected=rule.expected_value, reason="Exact match"
            )
        if rule.allowed_values:
            # Support multi-value extraction (e.g. "8541.10, 8541.21" from multi-line invoices)
            # Split by comma and check every individual value is in the allowed list
            extracted_parts = [v.strip() for v in found_val.split(",") if v.strip()]
            if extracted_parts and all(p in rule.allowed_values for p in extracted_parts):
                label = found_val if len(extracted_parts) == 1 else f"{found_val} (all values allowed)"
                return FieldVerdict(
                    status="match", found=found_val,
                    expected=expected_display, reason=label if len(extracted_parts) == 1 else "All extracted values are in the allowed list"
                )
            # Identify which specific values are not allowed
            rejected = [p for p in extracted_parts if p not in rule.allowed_values]
            return FieldVerdict(
                status="mismatch",
                found=found_val,
                expected=expected_display,
                reason=(
                    f"Value(s) not in allowed list: {', '.join(rejected)}"
                    if rejected else
                    f"Expected one of [{expected_display}], found '{found_val}'"
                ),
            )
        # Mismatch (no allowed_values, expected_value already checked above)
        return FieldVerdict(
            status="mismatch",
            found=found_val,
            expected=expected_display,
            reason=f"Expected '{rule.expected_value}', found '{found_val}'",
        )

    # 4. Regex format check
    if rule.match_type == "format_regex":
        if rule.pattern and re.fullmatch(rule.pattern, found_val):
            return FieldVerdict(
                status="match", found=found_val,
                expected=f"matches /{rule.pattern}/", reason="Format regex matched"
            )
        return FieldVerdict(
            status="mismatch",
            found=found_val,
            expected=f"must match /{rule.pattern}/",
            reason=f"'{found_val}' does not satisfy required format",
        )

    # 5. Fuzzy — handled async in the caller; should not reach here
    return FieldVerdict(
        status="uncertain",
        found=found_val,
        expected=expected_display,
        reason="Fuzzy match deferred to LLM — unexpected code path",
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run_validator(
    extraction: ExtractionResult, rule_set: CustomerRuleSet
) -> ValidationResult:
    low_threshold = settings.confidence_low_threshold

    field_map: dict[str, FieldExtraction] = {
        "consignee_name":   extraction.consignee_name,
        "hs_code":          extraction.hs_code,
        "port_of_loading":  extraction.port_of_loading,
        "port_of_discharge": extraction.port_of_discharge,
        "incoterms":        extraction.incoterms,
        "description_goods": extraction.description_goods,
        "gross_weight":     extraction.gross_weight,
        "invoice_number":   extraction.invoice_number,
    }

    verdicts: dict[str, FieldVerdict] = {}

    for field_name, field_extraction in field_map.items():
        rule = rule_set.rules.get(field_name)

        if rule is None:
            verdicts[field_name] = FieldVerdict(
                status="match",
                found=field_extraction.value,
                expected=None,
                reason="No validation rule defined for this field",
            )
            continue

        # Fuzzy match — needs async LLM call
        if (
            rule.match_type == "fuzzy"
            and field_extraction.value is not None
            and field_extraction.confidence >= low_threshold
        ):
            expected_values = rule.allowed_values or (
                [rule.expected_value] if rule.expected_value else []
            )
            if expected_values:
                is_match, closest = await _fuzzy_match(
                    field_extraction.value, expected_values
                )
                if is_match:
                    verdicts[field_name] = FieldVerdict(
                        status="match",
                        found=field_extraction.value,
                        expected=closest or ", ".join(expected_values),
                        reason=f"Fuzzy match accepted (closest: {closest})",
                    )
                else:
                    verdicts[field_name] = FieldVerdict(
                        status="mismatch",
                        found=field_extraction.value,
                        expected=", ".join(expected_values),
                        reason=(
                            f"Fuzzy match failed — '{field_extraction.value}' "
                            f"does not match any allowed value"
                        ),
                    )
            else:
                verdicts[field_name] = FieldVerdict(
                    status="match",
                    found=field_extraction.value,
                    expected=None,
                    reason="Fuzzy rule defined but no expected values to compare against",
                )
        else:
            verdicts[field_name] = _validate_deterministic(
                field_name, field_extraction, rule, low_threshold
            )

    mismatch_count = sum(1 for v in verdicts.values() if v.status == "mismatch")
    uncertain_count = sum(1 for v in verdicts.values() if v.status == "uncertain")

    result = ValidationResult(
        job_id=extraction.job_id,
        customer_id=rule_set.customer_id,
        verdicts=verdicts,
        has_uncertain=uncertain_count > 0,
        mismatch_count=mismatch_count,
        uncertain_count=uncertain_count,
    )
    logger.info(
        "Validation complete | job=%s mismatches=%d uncertain=%d",
        extraction.job_id,
        mismatch_count,
        uncertain_count,
    )
    return result
