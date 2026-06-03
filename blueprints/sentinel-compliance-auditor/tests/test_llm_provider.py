"""Regression tests for LLM provider switching."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from sentinel.llm import get_client, get_model, set_provider, _clients


@pytest.fixture(autouse=True)
def _reset_provider():
    """Reset provider state between tests."""
    set_provider("nebius")
    _clients.clear()
    yield
    set_provider("nebius")
    _clients.clear()


class TestSetProvider:
    def test_default_is_nebius(self):
        assert get_model() == "deepseek-ai/DeepSeek-V4-Pro"

    def test_switch_to_openai(self):
        set_provider("openai")
        assert get_model() == "gpt-5.5"

    def test_switch_back_to_nebius(self):
        set_provider("openai")
        set_provider("nebius")
        assert get_model() == "deepseek-ai/DeepSeek-V4-Pro"


class TestGetClient:
    @patch("sentinel.llm.NEBIUS_API_KEY", "test-nebius-key")
    def test_nebius_client_cached(self):
        c1 = get_client()
        c2 = get_client()
        assert c1 is c2

    @patch("sentinel.llm.OPENAI_API_KEY", "test-openai-key")
    def test_openai_client_created(self):
        set_provider("openai")
        client = get_client()
        assert client is not None

    @patch("sentinel.llm.NEBIUS_API_KEY", "test-nebius-key")
    @patch("sentinel.llm.OPENAI_API_KEY", "test-openai-key")
    def test_different_providers_different_clients(self):
        nebius_client = get_client()
        set_provider("openai")
        openai_client = get_client()
        assert nebius_client is not openai_client
