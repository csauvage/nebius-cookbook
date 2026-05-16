"""Three-step agent: plan (cheap) → search Tavily → write (mid-tier) with citations."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass

import structlog

from app.core.nebius_client import NebiusClient
from app.core.tavily_client import TavilyClient, TavilyResult

logger = structlog.get_logger()

PLANNER_SYSTEM_PROMPT = (
    "You plan web searches for a research assistant. Given a user question, "
    "output 2 to 4 concise search queries that together would surface the freshest, "
    "most authoritative facts. Reply with a JSON array of strings, nothing else."
)

WRITER_SYSTEM_PROMPT = (
    "You write concise, factual briefs grounded in the sources provided. "
    "Cite every claim inline using [n] where n is the source index. "
    "Do not invent facts. If sources disagree, say so. Keep the brief under 250 words."
)


@dataclass
class Event:
    name: str
    data: dict[str, object]


@dataclass
class Citation:
    index: int
    title: str
    url: str


class GroundedAgent:
    """Three-step grounded agent. Streams progress as it goes."""

    def __init__(
        self,
        nebius: NebiusClient,
        tavily: TavilyClient,
        *,
        planner_model: str,
        writer_model: str,
    ) -> None:
        self._nebius = nebius
        self._tavily = tavily
        self._planner_model = planner_model
        self._writer_model = writer_model

    async def run(
        self,
        prompt: str,
        *,
        cancel_event: asyncio.Event | None = None,
    ) -> AsyncIterator[Event]:
        # --- Step 1: plan ---
        yield Event("status", {"phase": "planning", "model": self._planner_model})
        plan = await self._plan(prompt)
        yield Event("plan", {"queries": plan})

        if cancel_event is not None and cancel_event.is_set():
            return

        # --- Step 2: search ---
        yield Event("status", {"phase": "searching", "queries": len(plan)})
        sources = await self._search_all(plan)
        citations = [Citation(index=i + 1, title=s.title, url=s.url) for i, s in enumerate(sources)]
        yield Event(
            "sources",
            {"items": [{"index": c.index, "title": c.title, "url": c.url} for c in citations]},
        )

        if cancel_event is not None and cancel_event.is_set():
            return

        # --- Step 3: write ---
        yield Event("status", {"phase": "writing", "model": self._writer_model})
        async for token in self._write(prompt, sources):
            if cancel_event is not None and cancel_event.is_set():
                return
            yield Event("token", {"text": token})

        yield Event("status", {"phase": "done"})

    async def _plan(self, prompt: str) -> list[str]:
        messages = [
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        chunks: list[str] = []
        async for tok in self._nebius.stream_chat(
            model=self._planner_model,
            messages=messages,  # type: ignore[arg-type]
            temperature=0.1,
            max_tokens=256,
        ):
            chunks.append(tok)
        raw = "".join(chunks).strip()
        return _parse_query_list(raw)

    async def _search_all(self, queries: list[str]) -> list[TavilyResult]:
        results = await asyncio.gather(*(self._tavily.search(q) for q in queries))
        flat: list[TavilyResult] = []
        seen: set[str] = set()
        for batch in results:
            for r in batch:
                if r.url in seen:
                    continue
                seen.add(r.url)
                flat.append(r)
        flat.sort(key=lambda r: r.score, reverse=True)
        return flat[:10]

    async def _write(self, prompt: str, sources: list[TavilyResult]) -> AsyncIterator[str]:
        rendered = "\n\n".join(
            f"[{i + 1}] {s.title}\n{s.url}\n{s.content}" for i, s in enumerate(sources)
        )
        messages = [
            {"role": "system", "content": WRITER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Question:\n{prompt}\n\nSources:\n{rendered}",
            },
        ]
        async for tok in self._nebius.stream_chat(
            model=self._writer_model,
            messages=messages,  # type: ignore[arg-type]
            temperature=0.3,
            max_tokens=1024,
        ):
            yield tok


_JSON_ARRAY = re.compile(r"\[.*\]", re.DOTALL)


def _parse_query_list(raw: str) -> list[str]:
    """Parse a JSON array of strings out of a model response, robust to fences."""
    match = _JSON_ARRAY.search(raw)
    if match is None:
        return [raw.strip()]
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        logger.warning("planner_output_not_json", raw=raw)
        return [raw.strip()]
    if not isinstance(parsed, list):
        return [raw.strip()]
    return [str(q) for q in parsed if isinstance(q, (str, int, float)) and str(q).strip()][:4]
