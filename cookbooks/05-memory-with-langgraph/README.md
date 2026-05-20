# Memory — Memory with LangGraph

> 🚧 **Scaffold only.** This recipe is planned but not yet implemented. This
> folder currently holds metadata (`recipe.json`) and this documentation. The
> `app/`, tests, and Docker setup will land in a later pass.

Recipe **05 of 7** in the Nebius Cookbook arc:

> Foundation → Retrieval → Awareness → Orchestration → **Memory** → Reliability → Confidence

The LangGraph cookbook introduced graph state and streaming orchestration.
This recipe adds LangGraph memory: checkpointers for short-term thread state and stores for long-term user or application context.

## What you'll build

A FastAPI service that follows the official LangGraph memory model:

1. **Short-term memory** — a checkpointer keeps a thread's conversation state across turns.
2. **Long-term memory** — a store keeps user-specific or application-level facts across sessions.
3. **Bounded recall** — the graph retrieves only the memories relevant to the current prompt before calling the Nebius chat model.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- A Nebius API key — get one from the [Nebius console](https://nebius.com)
- Docker (optional)

## Planned architecture

```text
request ──► thread_id ──► LangGraph checkpointer ──► graph state
             user_id  ──► LangGraph store ─────────► relevant memories
                                                        │
                                                        ▼
                                             Nebius chat model ──► SSE
```

- **Answer model:** `meta-llama/Llama-3.3-70B-Instruct`.
- **Memory runtime:** LangGraph checkpointers and stores, following
  `https://docs.langchain.com/oss/python/langgraph/add-memory`.
- **Production backing store:** Postgres is the default recommendation for both
  checkpointer and store examples; local quickstarts can use in-memory variants
  only for development.

## Design decisions

**Two memory scopes, two primitives.** Checkpointers track short-term thread memory: the sequence of messages and graph state for one conversation thread. Stores track long-term memory: user facts, preferences, and application context that can be recalled across threads.

**Memory is explicit graph state, not route state.** The FastAPI route passes `thread_id` and authenticated user context into graph invocation. Nodes read and write memory through LangGraph runtime primitives; route handlers should not become memory orchestration code.

**Local memory is not production memory.** `InMemorySaver` and `InMemoryStore` are acceptable for a five-minute local run, but they disappear on process restart. The production path uses database-backed checkpointers and stores before relying on memory across deploys.

**Recall stays bounded.** Long-term memory can grow without bound, so every recall must use a limit and relevance ranking. Injecting the entire store is just transcript replay with extra steps.

## Failure modes to design for

| Symptom | Cause | Handling |
|---|---|---|
| Agent forgets earlier turns | Missing or unstable `thread_id` | Require `thread_id` for conversational endpoints and return it in responses |
| Cross-user leakage | User context comes from the request body | Derive `user_id` from authenticated identity before using store namespaces |
| Stale long-term memory | Facts or preferences changed | Include timestamps and prefer recent facts when conflicts appear |
| Token blow-up | Too many memories injected | Cap recall count and summarize or trim thread messages |
| Privacy request | User asks to delete stored context | Delete store records and checkpoints tied to that user or thread |

## Planned endpoints

| Method | Path                  | Purpose                                      |
| ------ | --------------------- | -------------------------------------------- |
| POST   | `/agent/run`          | Run the agent with thread and long-term memory recall. |
| GET    | `/memory/{user_id}`   | List long-term memories stored for a user.   |
| DELETE | `/memory/{user_id}`   | Delete long-term memories stored for a user. |
| DELETE | `/threads/{thread_id}` | Delete short-term checkpoints for a thread. |
| GET    | `/healthz`            | Liveness probe.                              |
| GET    | `/readyz`             | Readiness probe.                             |
| GET    | `/metrics`            | Prometheus scrape endpoint.                  |

## Status

- [x] `recipe.json` metadata
- [x] Documentation scaffold
- [ ] `app/` implementation
- [ ] Tests
- [ ] Dockerfile + Makefile
- [ ] `docs/deployment.md`

## Going further

Next in the arc: **[Reliability — Hardening Agents with Guardrails](../06-hardening-agents-guardrails/)** —
a stateful agent now needs validation before it is put in front of users.

## Reference

- LangGraph memory — [docs.langchain.com/oss/python/langgraph/add-memory](https://docs.langchain.com/oss/python/langgraph/add-memory)

## License

MIT
