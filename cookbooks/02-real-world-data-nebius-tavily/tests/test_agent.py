"""Agent route tests. Both Nebius and Tavily are mocked — no network."""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.main import app


def _sse_chunk(data: dict[str, object]) -> bytes:
    return b"data: " + json.dumps(data).encode("utf-8") + b"\n\n"


def _completion_stream(tokens: list[str]) -> bytes:
    chunks = [{"choices": [{"delta": {"content": t}, "index": 0}]} for t in tokens]
    chunks.append({"choices": [{"delta": {}, "index": 0, "finish_reason": "stop"}]})
    return b"".join(_sse_chunk(c) for c in chunks) + b"data: [DONE]\n\n"


@pytest.mark.asyncio
@respx.mock
async def test_agent_run_three_step_flow() -> None:
    planner_response = httpx.Response(
        200,
        content=_completion_stream(['["latest nebius launches", "nebius pricing 2026"]']),
        headers={"content-type": "text/event-stream"},
    )
    writer_response = httpx.Response(
        200,
        content=_completion_stream(["Nebius ", "shipped ", "X [1]."]),
        headers={"content-type": "text/event-stream"},
    )

    nebius_route = respx.post("https://api.studio.nebius.ai/v1/chat/completions").mock(
        side_effect=[planner_response, writer_response]
    )

    tavily_route = respx.post("https://api.tavily.com/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "Nebius blog",
                        "url": "https://nebius.com/blog/post",
                        "content": "Nebius launched X.",
                        "score": 0.91,
                    },
                    {
                        "title": "Industry roundup",
                        "url": "https://example.com/roundup",
                        "content": "Coverage of Nebius launch.",
                        "score": 0.72,
                    },
                ]
            },
        )
    )

    with TestClient(app) as client:
        with client.stream(
            "POST", "/agent/run", json={"prompt": "What did Nebius launch this week?"}
        ) as resp:
            assert resp.status_code == 200
            body = b"".join(resp.iter_bytes()).decode("utf-8")

    assert nebius_route.call_count == 2  # planner + writer
    assert tavily_route.called
    assert "event: status" in body
    assert 'phase": "planning"' in body
    assert 'phase": "searching"' in body
    assert 'phase": "writing"' in body
    assert "event: sources" in body
    assert "event: token" in body
    assert "event: done" in body
