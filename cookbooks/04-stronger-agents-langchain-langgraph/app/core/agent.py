"""LangGraph-backed agent logic. Pure async generator yielding typed events."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from openai.types.chat import ChatCompletionMessageParam

from app.core.nebius_client import NebiusClient

SYSTEM_PROMPT = (
    "You are a helpful, concise assistant. Answer the user's question directly, "
    "without preamble. Use plain text unless markdown adds clarity."
)


@dataclass
class Event:
    name: str
    data: dict[str, object]


class AgentState(TypedDict):
    prompt: str
    plan: str
    messages: list[ChatCompletionMessageParam]


class Agent:
    """Small LangGraph skeleton that keeps orchestration out of the route."""

    def __init__(self, client: NebiusClient, model: str) -> None:
        self._client = client
        self._model = model
        self._graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(AgentState)
        graph.add_node("plan", self._plan)
        graph.add_node("write", self._write)
        graph.add_edge(START, "plan")
        graph.add_edge("plan", "write")
        graph.add_edge("write", END)
        return graph.compile()

    @staticmethod
    def _plan(state: AgentState) -> dict[str, str]:
        prompt = state["prompt"].strip()
        return {"plan": f"Answer directly and mention assumptions if needed: {prompt[:120]}"}

    @staticmethod
    def _write(state: AgentState) -> dict[str, list[ChatCompletionMessageParam]]:
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": f"{SYSTEM_PROMPT}\n\nPlan: {state['plan']}"},
            {"role": "user", "content": state["prompt"]},
        ]
        return {"messages": messages}

    async def run(
        self,
        prompt: str,
        *,
        cancel_event: asyncio.Event | None = None,
    ) -> AsyncIterator[Event]:
        yield Event("status", {"phase": "planning"})

        state = await self._graph.ainvoke({"prompt": prompt})

        yield Event("status", {"phase": "writing"})

        async for token in self._client.stream_chat(
            model=self._model,
            messages=state["messages"],
        ):
            if cancel_event is not None and cancel_event.is_set():
                return
            yield Event("token", {"text": token})

        yield Event("status", {"phase": "done"})
