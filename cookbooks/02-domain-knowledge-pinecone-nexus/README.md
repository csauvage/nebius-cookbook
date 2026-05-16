# Retrieval — Domain Knowledge with Pinecone Nexus

> 🚧 **Scaffold only.** This recipe is planned but not yet implemented. This
> folder currently holds metadata (`recipe.json`) and this documentation. The
> `app/`, tests, and Docker setup will land in a later pass.

Recipe **02 of 6** in the Nebius Cookbook arc:

> Foundation → **Retrieval** → Awareness → Memory → Reliability → Confidence

Cookbook #1 gave you a fluent agent. But fluency isn't knowledge — ask it about
your own product or internal docs and it will guess. Classic RAG patches this
by handing the model raw document chunks at inference time, which burns tokens,
adds latency, and still invites hallucination. This recipe takes a different
route: a **knowledge engine**.

## What you'll build

A FastAPI service that uses [Pinecone Nexus](https://www.pinecone.io/blog/knowledge-infrastructure-for-agents/)
as the agent's knowledge layer. Nexus moves reasoning *upstream — from retrieval
to knowledge compilation* — so the agent queries curated, task-ready knowledge
instead of sifting raw chunks.

The three Nexus pieces this recipe leans on:

1. **Context Compiler** — turns a raw data estate into task-specific *knowledge
   artifacts* (one estate, many agents, distinct artifacts per task).
2. **Composable Retriever** — serves those artifacts with low latency, typed
   fields, per-field citations, and confidence scores.
3. **KnowQL** — a declarative query language; the agent expresses *what it
   needs* via six primitives: intent, filter, provenance, output shape,
   confidence, and budget.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- A Nebius API key — get one from the [Nebius console](https://nebius.com)
- A Pinecone API key with Nexus access — [pinecone.io](https://www.pinecone.io)

## Planned architecture

```
documents ──► /ingest ──► Nexus Context Compiler ──► knowledge artifacts
                                                            │
question ──► KnowQL query ──► Composable Retriever ──► typed, cited context
                                                            │
                                                            ▼
                                          chat model (Nebius) ──► SSE answer
```

- **Answer model:** `meta-llama/Llama-3.3-70B-Instruct` on Nebius.
- **Knowledge engine:** Pinecone Nexus — compilation, retrieval, and governance
  (PII tagging, versioning, RBAC) happen here, not in app code.

The ingest path and the query path are **deliberately separate**. Compilation is
expensive and write-time; querying is cheap and read-time. Splitting them lets
you recompile on a schedule (or a data-change webhook) without coupling it to
request latency.

## Design decisions

**Why a knowledge engine instead of classic RAG?** RAG's failure mode is
structural: it retrieves *then* reasons, so the model pays — in tokens, latency,
and hallucination risk — to re-derive structure from raw chunks on every call.
Nexus compiles that structure once, write-time, into typed artifacts. The agent
reads a fact with a confidence score; it does not infer a fact from prose.

**Why KnowQL over a raw vector query?** A `top_k` similarity search returns
"things that look like the question." KnowQL lets the agent state *intent*,
*provenance* requirements, an *output shape*, and a *budget* — so retrieval is a
contract, not a guess. It also makes retrieval **auditable**: the query is a
declarative object you can log, diff, and replay.

**Where governance lives.** PII tagging, versioning, and RBAC are Nexus
concerns, not app concerns. Keeping them in the knowledge layer means every
consumer of an artifact inherits the same policy — you cannot accidentally ship
an agent that bypasses redaction by querying differently.

**Trade-off to accept.** A knowledge engine adds a compilation step and a
freshness window: an artifact is only as current as its last compile. For
slowly-changing domain knowledge that is the right trade. For *fast*-changing
facts, that is the wrong tool — which is exactly why Cookbook #3 reaches for
live web search instead.

## Failure modes to design for

| Symptom | Cause | Handling |
|---|---|---|
| Agent answers from stale facts | Data estate changed, artifacts not recompiled | Recompile on a data-change event; surface artifact `compiledAt` in the answer |
| Low-confidence retrieval | The question has no good artifact coverage | Gate on the KnowQL `confidence` primitive; fall back to "I don't have that" rather than guess |
| Conflicting facts | Two sources disagree | Lean on Nexus's deterministic conflict resolution; expose the resolved provenance in citations |
| Cold start — no artifacts | Service deployed before first `/ingest` | `/readyz` should report not-ready until at least one artifact set is compiled |

## Planned endpoints

| Method | Path          | Purpose                                                  |
| ------ | ------------- | -------------------------------------------------------- |
| POST   | `/ingest`     | Feed source documents into the Nexus data estate.        |
| POST   | `/agent/run`  | Answer from Nexus-compiled knowledge, streamed as SSE.   |
| GET    | `/healthz`    | Liveness probe.                                          |
| GET    | `/readyz`     | Readiness probe — not-ready until knowledge is compiled. |
| GET    | `/metrics`    | Prometheus scrape endpoint.                              |

## Status

- [x] `recipe.json` metadata
- [x] Documentation scaffold
- [ ] `app/` implementation
- [ ] Tests
- [ ] Dockerfile + Makefile
- [ ] `docs/deployment.md`

## Reference

- Pinecone — [Knowledge infrastructure for agents](https://www.pinecone.io/blog/knowledge-infrastructure-for-agents/)

## Going further

Next in the arc: **[Awareness — Real-Time Data with Tavily](../03-real-time-data-tavily/)** —
once your agent knows your compiled domain knowledge, teach it to reach for
fresh facts on the open web.

## License

MIT
