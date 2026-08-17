from __future__ import annotations
import logging
import threading
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select

from app.db import Base, engine, SessionLocal
from app.models import CoverageRate
from app.routes import coverage, adverse_events, adherence

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(title="Vaccine Surveillance", version="2.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(coverage.router)
app.include_router(adverse_events.router)
app.include_router(adherence.router)


@app.on_event("startup")
def on_startup():
    # Create all tables (idempotent)
    Base.metadata.create_all(engine)

    # If the coverage table is empty, seed in background
    with SessionLocal() as session:
        count = session.execute(select(func.count(CoverageRate.id))).scalar_one()

    if count == 0:
        log.info("Database is empty — starting background seed (takes ~5 min) ...")
        from app.seed import run_seed
        thread = threading.Thread(target=run_seed, daemon=True)
        thread.start()
    else:
        log.info("Database has %d coverage rows — skipping seed", count)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/seed-status")
def seed_status() -> dict:
    with SessionLocal() as session:
        cov  = session.execute(select(func.count(CoverageRate.id))).scalar_one()
    return {"coverage_rows": cov, "seeded": cov > 0}


# ── Serve built React UI ────────────────────────────────────────────────────
UI_DIST = Path(__file__).parent.parent / "ui" / "dist"

if UI_DIST.exists():
    if (UI_DIST / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(UI_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str) -> FileResponse:
        return FileResponse(str(UI_DIST / "index.html"))
