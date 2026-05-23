from pydantic import BaseModel
from typing import Optional, Literal


class FieldRule(BaseModel):
    expected_value: Optional[str] = None
    allowed_values: Optional[list[str]] = None
    match_type: Literal["exact", "fuzzy", "format_regex"]
    pattern: Optional[str] = None  # regex if match_type == 'format_regex'
    severity: Literal["hard", "soft"]  # hard = mismatch blocks approval
    required: bool


class CustomerRuleSet(BaseModel):
    customer_id: str
    customer_name: str
    rules: dict[str, FieldRule]  # keyed by field name
