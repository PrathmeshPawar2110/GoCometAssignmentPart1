import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import customers, jobs, query
from src.db.connection import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

app = FastAPI(
    title="Nova Trade Pipeline API",
    description="Multi-Agent Trade Document Processing Pipeline",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # Create React App fallback
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup() -> None:
    await init_db()


app.include_router(jobs.router,      prefix="/jobs",      tags=["jobs"])
app.include_router(query.router,     prefix="/query",     tags=["query"])
app.include_router(customers.router, prefix="/customers", tags=["customers"])


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "version": "1.0.0"}
