"""Shared test fixtures."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("NEBIUS_API_KEY", "test-nebius")
os.environ.setdefault("PINECONE_API_KEY", "test-pinecone")
os.environ.setdefault("PINECONE_INDEX_NAME", "test-index")
os.environ.setdefault("NEBIUS_ENABLE_PRICING_LOOKUP", "false")


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
