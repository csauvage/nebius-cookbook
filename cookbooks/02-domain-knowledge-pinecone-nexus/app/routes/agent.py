"""SSE endpoint for book recommendations."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Request
from starlette.responses import StreamingResponse

from app.config import Settings, get_settings
from app.core.book_rag import BookRag, UsageSummary
from app.schemas.agent import AgentRunRequest


router = APIRouter()


def _sse(event: str, data: dict[str, object]) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode()


def _combine_usage(*items: UsageSummary) -> UsageSummary:
    return UsageSummary(
        embedding_tokens=sum(item.embedding_tokens for item in items),
        input_tokens=sum(item.input_tokens for item in items),
        output_tokens=sum(item.output_tokens for item in items),
        cost_usd=sum(item.cost_usd for item in items),
    )


@router.post("/run")
async def run_agent(
    payload: AgentRunRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    """Retrieve Goodreads book context and stream a grounded recommendation answer."""

    async def event_stream() -> AsyncIterator[bytes]:
        if await request.is_disconnected():
            return

        yield _sse("status", {"phase": "embedding"})
        rag = BookRag(settings)

        try:
            yield _sse("status", {"phase": "sending_to_nebius", "message": "Sending to Nebius Token Factory"})
            query_vector, embedding_tokens = await asyncio.to_thread(rag.embed_query, payload.prompt)
            prices = await asyncio.to_thread(rag.pricing.get_prices)
            embedding_cost = embedding_tokens * prices.embedding_per_million / 1_000_000
            retrieval_usage = UsageSummary(
                embedding_tokens=embedding_tokens,
                cost_usd=embedding_cost,
            )

            yield _sse("status", {"phase": "retrieving", "message": "Requesting Pinecone Results"})
            books = await asyncio.to_thread(
                rag.retrieve_books_from_vector,
                query_vector,
                payload.top_k,
                payload.related_top_k,
                payload.include_related,
            )
            yield _sse("context", {"books": [book.to_public_dict() for book in books]})

            yield _sse("status", {"phase": "synthesizing", "message": "Synthesizing"})
            synthesis = await asyncio.to_thread(
                rag.synthesize,
                payload.prompt,
                books,
            )
            usage = _combine_usage(retrieval_usage, synthesis.usage)
            yield _sse("answer", {"text": synthesis.answer})
            yield _sse(
                "status",
                {
                    "phase": "done",
                    "message": (
                        f"Done ({usage.input_tokens} token in | "
                        f"{usage.output_tokens} token out | "
                        f"Cost: {usage.cost_usd:.6f} USD)"
                    ),
                    "usage": usage.to_public_dict(),
                },
            )
            yield _sse("done", usage.to_public_dict())
        except Exception:
            yield _sse("error", {"detail": "book recommendation failed"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"cache-control": "no-cache", "x-accel-buffering": "no"},
    )
