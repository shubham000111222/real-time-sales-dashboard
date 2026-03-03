"""
FastAPI application entry point
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .database import engine, Base
from .routers.sales import router as sales_router
from .routers.forecast import router as forecast_router

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (idempotent)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("✅ Database tables ready")
    yield
    await engine.dispose()
    log.info("🔌 Engine disposed")


app = FastAPI(
    title="Real-Time Sales Analytics API",
    description=(
        "FastAPI backend for the Real-Time Sales Dashboard.\n\n"
        "Ingests simulated sales streams, persists to PostgreSQL, "
        "and serves analytics + forecast endpoints."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # lock down in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
PREFIX = "/api/v1"
app.include_router(sales_router,    prefix=PREFIX)
app.include_router(forecast_router, prefix=PREFIX)


# ─── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def root():
    return JSONResponse({"message": "Sales Analytics API — visit /docs"})
