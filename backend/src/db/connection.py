import aiosqlite

from src.config import settings

# Single source of truth — reads DB_PATH from .env via pydantic-settings
DB_PATH: str = settings.db_path


async def init_db() -> None:
    """Create tables and indexes if they don't exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id      TEXT PRIMARY KEY,
                status      TEXT NOT NULL DEFAULT 'pending',
                customer_id TEXT NOT NULL,
                doc_type    TEXT NOT NULL,
                file_path   TEXT NOT NULL,
                extraction  TEXT,
                validation  TEXT,
                decision    TEXT,
                retry_count INTEGER NOT NULL DEFAULT 0,
                token_usage INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
                completed_at TEXT
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_status   ON jobs(status)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_customer ON jobs(customer_id)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_created  ON jobs(created_at DESC)"
        )
        await db.commit()
