import json
import uuid
from typing import Optional

import aiosqlite

from src.db.connection import DB_PATH


async def create_job(customer_id: str, doc_type: str, file_path: str) -> str:
    job_id = str(uuid.uuid4())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO jobs (job_id, status, customer_id, doc_type, file_path,
                              created_at, updated_at)
            VALUES (?, 'pending', ?, ?, ?, datetime('now'), datetime('now'))
            """,
            (job_id, customer_id, doc_type, file_path),
        )
        await db.commit()
    return job_id


async def get_job(job_id: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
        ) as cursor:
            row = await cursor.fetchone()
    if row is None:
        return None
    record = dict(row)
    for key in ("extraction", "validation", "decision"):
        if record.get(key):
            record[key] = json.loads(record[key])
    return record


async def list_jobs(
    customer_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    query = "SELECT * FROM jobs WHERE 1=1"
    params: list = []
    if customer_id:
        query += " AND customer_id = ?"
        params.append(customer_id)
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()

    result = []
    for row in rows:
        record = dict(row)
        for key in ("extraction", "validation", "decision"):
            if record.get(key):
                record[key] = json.loads(record[key])
        result.append(record)
    return result


async def update_job_status(job_id: str, status: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE jobs SET status = ?, updated_at = datetime('now') WHERE job_id = ?",
            (status, job_id),
        )
        await db.commit()


async def update_job_extraction(job_id: str, extraction: dict) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE jobs
               SET extraction  = ?,
                   status      = 'extracting',
                   updated_at  = datetime('now')
             WHERE job_id = ?
            """,
            (json.dumps(extraction), job_id),
        )
        await db.commit()


async def update_job_validation(job_id: str, validation: dict) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE jobs
               SET validation = ?,
                   status     = 'validating',
                   updated_at = datetime('now')
             WHERE job_id = ?
            """,
            (json.dumps(validation), job_id),
        )
        await db.commit()


async def update_job_decision(
    job_id: str, decision: dict, final_status: str = "complete"
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        if final_status == "complete":
            await db.execute(
                """
                UPDATE jobs
                   SET decision     = ?,
                       status       = ?,
                       updated_at   = datetime('now'),
                       completed_at = datetime('now')
                 WHERE job_id = ?
                """,
                (json.dumps(decision), final_status, job_id),
            )
        else:
            await db.execute(
                """
                UPDATE jobs
                   SET decision   = ?,
                       status     = ?,
                       updated_at = datetime('now')
                 WHERE job_id = ?
                """,
                (json.dumps(decision), final_status, job_id),
            )
        await db.commit()


async def increment_retry(job_id: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE jobs
               SET retry_count = retry_count + 1,
                   updated_at  = datetime('now')
             WHERE job_id = ?
            """,
            (job_id,),
        )
        await db.commit()
        async with db.execute(
            "SELECT retry_count FROM jobs WHERE job_id = ?", (job_id,)
        ) as cursor:
            row = await cursor.fetchone()
    return row[0] if row else 0
