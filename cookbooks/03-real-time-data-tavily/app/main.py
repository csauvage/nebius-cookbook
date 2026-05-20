"""FastAPI app for the Pinecone-backed book RAG plus Tavily freshness recipe."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import get_settings
from app.routes import agent, health

settings = get_settings()

app = FastAPI(
    title="Real-Time Book Data with Pinecone and Tavily",
    version=__version__,
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    allow_credentials=False,
)

app.include_router(health.router)
app.include_router(agent.router, prefix="/agent")
