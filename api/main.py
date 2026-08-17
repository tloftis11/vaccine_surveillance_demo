from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from db import Base
from routers import coverage, adverse_events, adherence

app = FastAPI(
    title="Vaccine Surveillance API",
    description="API for vaccine coverage rates, adverse event reporting, and adherence data.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(coverage.router, prefix="/api")
app.include_router(adverse_events.router, prefix="/api")
app.include_router(adherence.router, prefix="/api")


@app.on_event("startup")
def on_startup() -> None:
    import subprocess
    subprocess.run(["alembic", "upgrade", "head"], check=True, cwd=Path(__file__).parent)


@app.get("/health", tags=["meta"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


# ── Serve built React app ────────────────────────────────────────────────────
# In production the UI is built into ui/dist/ by the Render build command.
# FastAPI serves the static assets and falls back to index.html for all
# non-API paths so that React Router handles client-side navigation.

UI_DIST = Path(__file__).parent.parent / "ui" / "dist"

if UI_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(UI_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str) -> FileResponse:
        return FileResponse(str(UI_DIST / "index.html"))
