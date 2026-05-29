"""FastAPI app entry point. Lifespan, middleware, and route wiring."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app import __version__
from app.config import get_settings
from app.observability.logging import configure_logging
from app.observability.metrics import metrics_middleware
from app.observability.middleware import (
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    SizeLimitMiddleware,
)
from app.routes import agent, health

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Runs once on startup (before `yield`) and once on shutdown (after).

    Use this for things that need the event loop: warm caches, open connection
    pools, register background tasks. Replaces the older `@app.on_event(...)`.
    """
    settings = get_settings()
    configure_logging(settings.log_level, settings.env)
    logger.info(
        "startup",
        version=__version__,
        env=settings.env,
        model=settings.nebius_model,
    )
    try:
        yield
    finally:
        logger.info("shutdown")
        await asyncio.sleep(0)


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Your First Agent on Nebius",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

settings = get_settings()
app.state.limiter = limiter
app.state.cookbook_slug = "01-first-agent-on-nebius"

# Middleware order matters: ASGI wraps last-added → first-added, so the LAST
# `add_middleware` call runs FIRST on the request (and LAST on the response).
# Read the list bottom-up to follow the request path: size check → security
# headers → request ID → metrics timing → CORS → route.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    allow_credentials=False,
    max_age=600,
)
app.add_middleware(BaseHTTPMiddleware, dispatch=metrics_middleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SizeLimitMiddleware, max_bytes=settings.max_request_bytes)


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(health.router)
app.include_router(agent.router, prefix="/agent")
