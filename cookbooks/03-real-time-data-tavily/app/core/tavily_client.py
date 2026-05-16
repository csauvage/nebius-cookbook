"""Thin async wrapper around the Tavily search API."""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import Settings, get_settings

logger = structlog.get_logger()

TAVILY_ENDPOINT = "https://api.tavily.com/search"


class TavilyResult:
    __slots__ = ("content", "score", "title", "url")

    def __init__(self, title: str, url: str, content: str, score: float) -> None:
        self.title = title
        self.url = url
        self.content = content
        self.score = score

    def to_dict(self) -> dict[str, Any]:
        return {"title": self.title, "url": self.url, "content": self.content, "score": self.score}


class TavilyClient:
    """Async client for Tavily search. No SDK — keeps the dep surface small."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)
        )

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8.0),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def search(self, query: str) -> list[TavilyResult]:
        payload = {
            "api_key": self._settings.tavily_api_key,
            "query": query,
            "search_depth": self._settings.tavily_search_depth,
            "max_results": self._settings.tavily_max_results,
            "include_answer": False,
        }
        response = await self._http.post(TAVILY_ENDPOINT, json=payload)
        response.raise_for_status()
        body = response.json()
        return [
            TavilyResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                content=item.get("content", ""),
                score=float(item.get("score", 0.0)),
            )
            for item in body.get("results", [])
        ]

    async def aclose(self) -> None:
        await self._http.aclose()


_singleton: TavilyClient | None = None


def build_tavily_client() -> TavilyClient:
    """FastAPI dependency. Reuses a single client per process."""
    global _singleton
    if _singleton is None:
        _singleton = TavilyClient(get_settings())
    return _singleton
