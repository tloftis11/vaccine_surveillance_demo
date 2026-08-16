from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

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
    allow_origins=settings.cors_origins,
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


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")
