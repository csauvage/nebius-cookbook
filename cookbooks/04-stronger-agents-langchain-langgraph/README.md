# Orchestration — Stronger Agents with LangChain and LangGraph

> Turn the hand-wired Nebius agent into a typed graph with explicit state and streaming.

Recipe **04 of 7** in the Nebius Cookbook arc:

> Foundation → Retrieval → Awareness → **Orchestration** → Memory → Reliability → Confidence

The first three cookbooks prove the Nebius integration path: call the model, ground it in private data, then add fresh web context.
The next production problem is shape.
Once planning, retrieval, writing, interrupts, and evaluators all live in one route handler, the agent becomes hard to reason about.
This cookbook introduces LangChain and LangGraph as the point where orchestration becomes an explicit graph.

## What you'll build

A production-shape FastAPI service that keeps the same SSE contract as the earlier recipes, but moves agent orchestration into a LangGraph state graph:

1. **Plan** — normalize the user request into a small state update.
2. **Write** — build the Nebius chat messages from graph state.
3. **Stream** — emit named SSE events while the Nebius model streams tokens.

Persistent context and memory primitives are deliberately saved for Cookbook #5.
This recipe stays focused on graph shape, typed state, and streaming events.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- A Nebius API key — get one from the [Nebius console](https://nebius.com)
- Docker (optional)

## Run it

```bash
cp .env.example .env
# Open .env and fill NEBIUS_API_KEY

uv sync
make dev
```

Then in another terminal:

```bash
curl -N -X POST http://localhost:8000/agent/run \
  -H 'content-type: application/json' \
  -d '{"prompt":"Explain why graph state helps production agents."}'
```

You should see named SSE events:

```text
event: status
data: {"phase":"planning"}

event: status
data: {"phase":"writing"}

event: token
data: {"text":"Graph"}

event: done
data: {}
```

## Walk-through

The FastAPI route stays intentionally boring.
It validates the request, creates an `Agent`, and translates the agent's typed events into SSE.
The graph lives in [`app/core/agent.py`](app/core/agent.py).

```text
request ──► route ──► LangGraph plan node ──► write node ──► Nebius stream ──► SSE
```

The graph is small on purpose.
The lesson is not "use LangGraph because two nodes need a framework."
The lesson is that graph state gives the next cookbooks a stable place to attach persistent context, guardrails, simulation, and eventually interrupts without turning the HTTP layer into orchestration glue.

## Memory boundary

This cookbook does not introduce persistent context or memory primitives.
The state graph only carries the data needed for the current request.
Cookbook #5 introduces LangGraph memory: checkpointers for thread state and stores for durable user/application context.

## Test it

```bash
uv run pytest
uv run ruff check
uv run ruff format --check
```

The tests mock the Nebius streaming endpoint with `respx`, so they do not call the network by default.

## Going further

- Replace the simple `plan` node with a real small-model planner.
- Add a retrieval/tool node between planning and writing.
- Cookbook #5 adds LangGraph memory for thread and user/application context.

## Reference

- LangGraph quickstart — [docs.langchain.com/oss/python/langgraph/quickstart](https://docs.langchain.com/oss/python/langgraph/quickstart)

## License

MIT
