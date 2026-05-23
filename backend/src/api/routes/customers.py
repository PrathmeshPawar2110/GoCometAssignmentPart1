import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from src.config import settings
from src.schemas.rules import CustomerRuleSet

router = APIRouter()


@router.get("/{customer_id}/rules")
async def get_customer_rules(customer_id: str):
    rules_path = Path(settings.rules_dir) / f"{customer_id}.json"
    if not rules_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No rule set found for customer '{customer_id}'",
        )
    with open(rules_path, encoding="utf-8") as f:
        data = json.load(f)
    return CustomerRuleSet(**data)


@router.put("/{customer_id}/rules")
async def upsert_customer_rules(customer_id: str, rule_set: CustomerRuleSet):
    rules_dir = Path(settings.rules_dir)
    rules_dir.mkdir(parents=True, exist_ok=True)
    rules_path = rules_dir / f"{customer_id}.json"
    with open(rules_path, "w", encoding="utf-8") as f:
        json.dump(rule_set.model_dump(), f, indent=2)
    return rule_set
