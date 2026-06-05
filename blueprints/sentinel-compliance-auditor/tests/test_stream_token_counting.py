"""Test that SSE token counting doesn't double-count outer + sub-agent tokens.

Regression: the UI was showing 2x the real cost because the `values` usage
event (outer-agent tokens) and the `Total tokens:` line from tool results
(sub-agent tokens) were being added on top of each other incorrectly.
"""
from __future__ import annotations

import json
import queue
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest


def _make_values_event(input_tokens: int, output_tokens: int):
    """Simulate a LangGraph `values` stream event with usage_metadata."""
    return SimpleNamespace(
        event="values",
        data={
            "messages": [
                {
                    "type": "ai",
                    "content": "thinking...",
                    "usage_metadata": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                    },
                }
            ]
        },
    )


def _make_tool_result_event(text: str):
    """Simulate a LangGraph `messages` stream event carrying a tool result."""
    return SimpleNamespace(
        event="messages",
        data=[{"type": "tool", "content": text, "tool_calls": []}],
    )


def _make_ai_token_event(text: str):
    """Simulate a LangGraph `messages` stream event with AI text."""
    return SimpleNamespace(
        event="messages",
        data=[{"type": "ai", "content": text, "tool_calls": []}],
    )


def _collect_usage_events(out_q: queue.Queue) -> list[dict]:
    """Drain the queue and return only usage events."""
    events = []
    while not out_q.empty():
        raw = out_q.get_nowait()
        if raw is None:
            continue
        parsed = json.loads(raw)
        if parsed.get("type") == "usage":
            events.append(parsed)
    return events


@pytest.fixture
def stream_one():
    """Import _stream_one with mocked LangGraph client."""
    from ui.server import _stream_one
    return _stream_one


def _run_stream(stream_one_fn, events):
    """Run _stream_one with a mocked LangGraph client that yields given events."""
    out_q = queue.Queue()

    mock_client = MagicMock()
    mock_stream = MagicMock()
    mock_stream.__iter__ = lambda self: iter(events)
    mock_client.runs.stream.return_value = mock_stream
    mock_client.threads.create.return_value = {"thread_id": "test-thread"}

    with patch("ui.server._langgraph_client", return_value=mock_client):
        stream_one_fn("test-thread", "audit all", "sentinel_optimized", out_q, "test")

    return out_q


class TestStreamTokenCounting:
    def test_outer_only_no_sub_agents(self, stream_one):
        """When no sub-agent tokens are reported, usage = outer tokens only."""
        events = [
            _make_values_event(1000, 200),
            _make_values_event(2000, 400),
        ]
        out_q = _run_stream(stream_one, events)
        usage_events = _collect_usage_events(out_q)

        assert len(usage_events) == 2
        last = usage_events[-1]
        assert last["input_tokens"] == 2000
        assert last["output_tokens"] == 400

    def test_outer_plus_sub_agent_tokens(self, stream_one):
        """Sub-agent tokens from tool result are added to outer tokens."""
        events = [
            _make_values_event(100_000, 20_000),
            _make_tool_result_event(
                "Audit complete: 50 findings\n"
                "  Total tokens: 9,000,000 (8,500,000 in / 500,000 out)\n"
                "  Failed: 0"
            ),
            _make_values_event(150_000, 30_000),
        ]
        out_q = _run_stream(stream_one, events)
        usage_events = _collect_usage_events(out_q)

        last = usage_events[-1]
        assert last["input_tokens"] == 150_000 + 8_500_000
        assert last["output_tokens"] == 30_000 + 500_000

    def test_no_double_counting(self, stream_one):
        """Regression: total must be outer + sub, not 2x.

        Before the fix, the server added sub_tokens on top of values usage
        that might already include them, producing ~2x the real cost.
        """
        outer_in, outer_out = 295_000, 20_000
        sub_in, sub_out = 9_123_000, 128_000

        events = [
            _make_values_event(200_000, 15_000),
            _make_tool_result_event(
                f"  Total tokens: {sub_in + sub_out:,} ({sub_in:,} in / {sub_out:,} out)"
            ),
            _make_values_event(outer_in, outer_out),
            _make_ai_token_event("Done — 200 SOPs audited."),
        ]
        out_q = _run_stream(stream_one, events)
        usage_events = _collect_usage_events(out_q)

        last = usage_events[-1]
        expected_in = outer_in + sub_in
        expected_out = outer_out + sub_out
        assert last["input_tokens"] == expected_in
        assert last["output_tokens"] == expected_out

        # Cost sanity check at Nemotron pricing ($1.00/M in, $3.00/M out)
        cost = (last["input_tokens"] * 1.00 + last["output_tokens"] * 3.00) / 1_000_000
        expected_cost = (expected_in * 1.00 + expected_out * 3.00) / 1_000_000
        assert abs(cost - expected_cost) < 0.01

    def test_sub_agent_tokens_regex_with_commas(self, stream_one):
        """Token counts with thousand separators are parsed correctly."""
        events = [
            _make_values_event(50_000, 5_000),
            _make_tool_result_event(
                "SOP-ISEC-008: 5 findings\n"
                "Sub-agent tokens: 1,234,567 (1,100,000 in / 134,567 out)"
            ),
        ]
        out_q = _run_stream(stream_one, events)
        usage_events = _collect_usage_events(out_q)

        last = usage_events[-1]
        assert last["input_tokens"] == 50_000 + 1_100_000
        assert last["output_tokens"] == 5_000 + 134_567

    def test_total_tokens_replaces_sub_tokens(self, stream_one):
        """A 'Total tokens:' line (from audit_all_sops) replaces accumulated sub_tokens."""
        events = [
            _make_values_event(10_000, 1_000),
            _make_tool_result_event(
                "Sub-agent tokens: 100,000 (80,000 in / 20,000 out)"
            ),
            _make_tool_result_event(
                "  Total tokens: 9,000,000 (8,000,000 in / 1,000,000 out)"
            ),
            _make_values_event(20_000, 2_000),
        ]
        out_q = _run_stream(stream_one, events)
        usage_events = _collect_usage_events(out_q)

        last = usage_events[-1]
        assert last["input_tokens"] == 20_000 + 8_000_000
        assert last["output_tokens"] == 2_000 + 1_000_000

    def test_individual_sub_agent_tokens_accumulate(self, stream_one):
        """Regression: individual audit_single_sop calls must accumulate, not overwrite.

        When the agent calls audit_single_sop N times (instead of audit_all_sops),
        each tool result has its own 'Sub-agent tokens:' line. These must be summed.
        """
        events = [
            _make_values_event(50_000, 5_000),
            _make_tool_result_event(
                "SOP-ISEC-001: 4 findings — 2C/1P/1G\n"
                "Sub-agent tokens: 200,000 (180,000 in / 20,000 out)"
            ),
            _make_values_event(80_000, 8_000),
            _make_tool_result_event(
                "SOP-ISEC-002: 6 findings — 3C/2P/1G\n"
                "Sub-agent tokens: 300,000 (270,000 in / 30,000 out)"
            ),
            _make_values_event(100_000, 10_000),
            _make_tool_result_event(
                "SOP-ISEC-003: 3 findings — 1C/1P/1G\n"
                "Sub-agent tokens: 150,000 (130,000 in / 20,000 out)"
            ),
            _make_values_event(120_000, 12_000),
        ]
        out_q = _run_stream(stream_one, events)
        usage_events = _collect_usage_events(out_q)

        last = usage_events[-1]
        expected_sub_in = 180_000 + 270_000 + 130_000
        expected_sub_out = 20_000 + 30_000 + 20_000
        assert last["input_tokens"] == 120_000 + expected_sub_in
        assert last["output_tokens"] == 12_000 + expected_sub_out
