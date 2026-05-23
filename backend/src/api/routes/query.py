"""
Natural-language query endpoint.

Flow:
  1. LLM converts the question to a SQLite SELECT.
  2. The query runs against the jobs table.
  3. LLM turns the raw rows into a plain-English answer.

Only SELECT statements are permitted — no writes possible through this endpoint.
"""

import json
import logging

import aiosqlite
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.config import settings
from src.db.connection import DB_PATH
from src.llm_client import get_model, llm_client

logger = logging.getLogger(__name__)

router = APIRouter()

_DB_SCHEMA = """
Table: jobs
Columns:
  job_id       TEXT  -- UUID primary key
  status       TEXT  -- 'pending' | 'extracting' | 'validating' | 'routing' | 'complete' | 'failed'
  customer_id  TEXT
  doc_type     TEXT  -- 'BoL' | 'CommercialInvoice' | 'PackingList' | 'CertificateOfOrigin'
  file_path    TEXT
  extraction   TEXT  -- JSON blob (ExtractionResult)
  validation   TEXT  -- JSON blob (ValidationResult)
  decision     TEXT  -- JSON blob: {"decision": "approve"|"review"|"amend", "reasoning": "...", "draft_message": "..."}
  retry_count  INTEGER
  token_usage  INTEGER
  created_at   TEXT  -- ISO datetime (UTC)
  updated_at   TEXT
  completed_at TEXT

Useful SQLite expressions:
  -- Extract decision type:       json_extract(decision, '$.decision')
  -- Jobs flagged (review/amend): json_extract(decision, '$.decision') IN ('review','amend')
  -- This week:                   created_at >= date('now', '-7 days')
  -- Today:                       date(created_at) = date('now')
  -- Auto-approved:               json_extract(decision, '$.decision') = 'approve'
"""

_SQL_SYSTEM = f"""You are a SQLite query generator.
Convert natural-language questions about trade document pipeline jobs to SQL.

Schema:
{_DB_SCHEMA}

Rules:
1. Return ONLY the SQL query — no explanation, no markdown fences.
2. Use only SELECT statements.
3. Limit to 100 rows unless the user asks for a specific number.
4. Use SQLite syntax (json_extract, date(), datetime()).
"""


class QueryRequest(BaseModel):
    question: str


@router.post("")
async def natural_language_query(request: QueryRequest):
    # Step 1: NL → SQL
    sql_response = await llm_client.chat.completions.create(
        model=get_model(settings.router_model),
        max_tokens=400,
        messages=[
            {"role": "system", "content": _SQL_SYSTEM},
            {"role": "user", "content": request.question},
        ],
    )
    sql = sql_response.choices[0].message.content.strip()

    # Strip any accidental markdown fencing
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    # Safety: only SELECT allowed
    if not sql.upper().lstrip().startswith("SELECT"):
        raise HTTPException(
            status_code=400,
            detail="Generated query is not a SELECT statement — rejected for safety",
        )

    # Step 2: Execute
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql) as cursor:
                rows = await cursor.fetchall()
                cols = [d[0] for d in (cursor.description or [])]
                result_rows = [dict(zip(cols, row)) for row in rows]
    except Exception as exc:
        logger.warning("NL query execution failed: %s | sql=%s", exc, sql)
        raise HTTPException(
            status_code=400,
            detail=f"Query execution error: {exc}",
        )

    # Step 3: Rows → natural-language answer
    answer_prompt = (
        f"Question: {request.question}\n"
        f"SQL: {sql}\n"
        f"Rows returned ({len(result_rows)}):\n"
        f"{json.dumps(result_rows[:20], indent=2)}\n\n"
        "Provide a concise, direct answer to the question based on these results."
    )
    answer_response = await llm_client.chat.completions.create(
        model=get_model(settings.router_model),
        max_tokens=300,
        messages=[{"role": "user", "content": answer_prompt}],
    )

    return {
        "answer": answer_response.choices[0].message.content.strip(),
        "sql_used": sql,
        "rows": result_rows,
    }
