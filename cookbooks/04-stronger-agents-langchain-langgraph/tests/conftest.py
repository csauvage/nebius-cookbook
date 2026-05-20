"""Shared test fixtures. No network is ever hit: respx mocks Nebius."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("NEBIUS_API_KEY", "test-key")
os.environ.setdefault("ENV", "development")
os.environ.setdefault("LOG_LEVEL", "warning")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    """Ensure settings are re-read for every test."""
    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
