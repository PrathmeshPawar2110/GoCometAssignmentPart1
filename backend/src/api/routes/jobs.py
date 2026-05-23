import json
import uuid
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Query, UploadFile

from src.config import settings
from src.db import jobs_repo
from src.graph.pipeline import run_pipeline
from src.schemas.rules import CustomerRuleSet

router = APIRouter()


def _load_customer_rules(customer_id: str) -> CustomerRuleSet:
    rules_dir = Path(settings.rules_dir)
    # Try exact customer ID file first, then fall back to acme_imports for demo
    for candidate in [f"{customer_id}.json", "acme_imports.json"]:
        rules_path = rules_dir / candidate
        if rules_path.exists():
            with open(rules_path, encoding="utf-8") as f:
                data = json.load(f)
            # Patch customer_id so it matches the request
            if candidate != f"{customer_id}.json":
                data["customer_id"] = customer_id
            return CustomerRuleSet(**data)
    raise HTTPException(
        status_code=404,
        detail=f"No rule set found for customer '{customer_id}'",
    )


@router.post("")
async def create_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    customer_id: str = Form(...),
    doc_type: str = Form(...),
):
    """Upload a trade document and start the pipeline."""
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename or "doc").suffix or ".pdf"
    unique_name = f"{uuid.uuid4()}{suffix}"
    file_path = str(upload_dir / unique_name)

    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    rule_set = _load_customer_rules(customer_id)
    job_id = await jobs_repo.create_job(customer_id, doc_type, file_path)

    background_tasks.add_task(
        run_pipeline,
        job_id=job_id,
        file_path=file_path,
        doc_type=doc_type,
        customer_id=customer_id,
        rule_set=rule_set.model_dump(),
    )

    return {"job_id": job_id, "status": "pending"}


@router.get("/{job_id}")
async def get_job(job_id: str):
    job = await jobs_repo.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("")
async def list_jobs(
    customer_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    jobs = await jobs_repo.list_jobs(customer_id, status, limit)
    return {"jobs": jobs, "count": len(jobs)}


@router.post("/{job_id}/approve")
async def approve_job(job_id: str, operator_note: Optional[str] = None):
    job = await jobs_repo.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    await jobs_repo.update_job_status(job_id, "complete")
    return {"job_id": job_id, "status": "complete", "operator_note": operator_note}
