from pydantic import BaseModel
from typing import Literal, Optional


class FieldVerdict(BaseModel):
    status: Literal["match", "mismatch", "uncertain"]
    found: Optional[str] = None
    expected: Optional[str] = None
    reason: str


class ValidationResult(BaseModel):
    job_id: str
    customer_id: str
    verdicts: dict[str, FieldVerdict]  # keyed by field name
    has_uncertain: bool
    mismatch_count: int
    uncertain_count: int
