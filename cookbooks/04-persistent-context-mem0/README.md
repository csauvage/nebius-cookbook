# Memory — Persistent Context with Mem0

> 🚧 **Scaffold only.** This recipe is planned but not yet implemented. This
> folder currently holds metadata (`recipe.json`) and this documentation. The
> `app/`, tests, and Docker setup will land in a later pass.

Recipe **04 of 6** in the Nebius Cookbook arc:

> Foundation → Retrieval → Awareness → **Memory** → Reliability → Confidence

Every agent so far is amnesiac. Cookbook #1 added in-request conversation
history, but the moment the session ends, the agent forgets the user entirely.
This recipe gives it a durable, per-user memory.

## What you'll build

A FastAPI service that wires [Mem0](https://mem0.ai) into the agent loop:

1. **Extracts** durable facts from each conversation turn (preferences,
   identity, prior decisions) instead of storing the raw transcript.
2. **Stores** them per `user_id` in Mem0.
3. **Recalls** the relevant memories at the start of each request and conditions
   the response on them — so the agent stays personal without resending the
   whole history every call.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- A Nebius API key — get one from the [Nebius console](https://nebius.com)
- A Mem0 API key — [mem0.ai](https://mem0.ai) — or a self-hosted Mem0 store

## Planned architecture

```
turn ──► Mem0 extract (LLM) ──► per-user memory store
                                        │
request ──► Mem0 recall (user_id) ──► relevant memories ──► chat model ──► SSE
```

- **Answer model:** `meta-llama/Llama-3.3-70B-Instruct`.
- **Embedding model:** `BAAI/bge-en-icl` — Mem0 uses it to index and search memories.

## Design decisions

**Why store extracted facts, not the transcript?** A raw transcript grows
without bound and is mostly noise — "thanks", "ok", restated questions.
Extraction distils each turn into a few durable claims. That keeps the recall
payload small and the injected context relevant. The cost is an extra LLM call
per turn; it runs *off the response hot path* (see below).

**This recipe deliberately breaks Cookbook #1's statelessness — correctly.**
The agent now has state, but it lives in Mem0, an *external* store. The FastAPI
process stays stateless and horizontally scalable; what changed is that "the
conversation" is no longer the client's responsibility alone. In-request
`history` handles the current turn; Mem0 handles everything across sessions.

**When to write memory.** Extraction on the response path adds latency the user
feels. Prefer to write *after* the response is streamed — fire-and-forget, or a
background task — so recall (read) is on the hot path and extraction (write) is
not. Accept that a memory from turn N may not be visible until turn N+2.

**What to recall.** Inject a bounded set of memories, ranked by relevance to the
current prompt, not the entire store. Memory is a context-budget line item; an
unbounded recall just reintroduces the token blow-up you were avoiding.

## Failure modes to design for

| Symptom | Cause | Handling |
|---|---|---|
| Agent "remembers" a false fact | User asserted something untrue; it got extracted | Treat memory as *claims*, not *truth*; never let memory override authoritative sources |
| Contradictory memories | Preferences changed over time | Prefer recency on conflict; let Mem0's update path supersede rather than append |
| Recall latency on the hot path | Memory store slow or large | Time-box the recall; on timeout, answer without memory rather than block |
| Cross-user leakage | `user_id` is client-supplied and spoofable | Derive `user_id` from an authenticated identity, never from the request body |
| Right-to-be-forgotten request | Privacy / compliance | `DELETE /memory/{user_id}` must hard-delete, not soft-flag |

## Planned endpoints

| Method | Path                  | Purpose                                      |
| ------ | --------------------- | -------------------------------------------- |
| POST   | `/agent/run`          | Run the agent with per-user memory recall.   |
| GET    | `/memory/{user_id}`   | List the durable memories stored for a user. |
| DELETE | `/memory/{user_id}`   | Forget everything stored for a user.         |
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

Next in the arc: **[Reliability — Hardening Agents with Guardrails](../05-hardening-agents-guardrails/)** —
a personal, capable agent now needs to be made safe to put in front of users.

## License

MIT
