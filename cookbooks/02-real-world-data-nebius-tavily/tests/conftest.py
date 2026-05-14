"""Shared test fixtures. No network — respx mocks Nebius and Tavily."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("NEBIUS_API_KEY", "test-key")
os.environ.setdefault("TAVILY_API_KEY", "test-tavily")
os.environ.setdefault("ENV", "development")
os.environ.setdefault("LOG_LEVEL", "warning")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
