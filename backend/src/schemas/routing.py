from pydantic import BaseModel
from typing import Literal, Optional


class RouterDecision(BaseModel):
    job_id: str
    decision: Literal["approve", "review", "amend"]
    reasoning: str  # mandatory: agent must explain, not just label
    draft_message: Optional[str] = None  # populated when decision == 'amend'
