# Observability — Observability with LangSmith

> Trace, inspect, annotate, and debug a stateful Nebius-backed agent with LangSmith.

Recipe **07 of 10** in the Nebius Cookbook arc:

> Foundation → Retrieval → Grounding → Orchestration → Thread Memory → User Memory → **Observability** → Guardrails → Actions → Simulation

By this point the agent can answer, orchestrate, remember a thread, and persist user memory in Postgres.
The next production problem is visibility.
When a run is bad, slow, expensive, or surprising, logs alone do not show the full chain of prompt, memory, route, model call, and output.

This recipe keeps everything from Cookbook #6 and adds LangSmith as the agent-run observability layer.
Prometheus still answers aggregate service questions.
LangSmith answers per-run behavior questions.

## What you'll build

A FastAPI service that extends the long-term-memory agent:

1. **Inherited orchestration** — the LangGraph route from Cookbook #4 still chooses the response path.
2. **Inherited memory** — `thread_id`, `user_id`, Postgres memory, memory summary, and deletion endpoints remain intact.
3. **LangSmith tracing** — each run can be traced with metadata, tags, and redacted previews.
4. **Feedback capture** — reviewers can attach feedback to a LangSmith run.
5. **Privacy-aware telemetry** — traces store previews and identifiers, not raw secrets or unnecessary PII.
6. **Credential-free local runs** — tracing is off by default so the recipe works without a LangSmith account.

```text
request ──► memory recall ──► LangGraph route ──► Nebius stream ──► SSE
              │                    │                  │
              └────────────────────┴──────────────────┘
                              LangSmith trace
```

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker for local Postgres
- A Nebius API key from the [Nebius console](https://nebius.com)
- Optional: a LangSmith API key from [LangSmith](https://docs.langchain.com/langsmith/home)

## Run it

```bash
cp .env.example .env
# Fill NEBIUS_API_KEY.
# Optionally set LANGSMITH_TRACING=true and fill LANGSMITH_API_KEY.

docker compose up -d postgres
uv sync
make dev
```

Run the traced agent:

```bash
curl -N -X POST http://localhost:8000/agent/run \
  -H 'content-type: application/json' \
  -d '{"thread_id":"trace-demo","user_id":"reader-42","prompt":"Recommend one short book about observability."}'
```

When tracing is disabled, the response still works and `langsmithRunId` is `null`.
When tracing is enabled, `memory_loaded` includes the LangSmith run id.

```text
event: status
data: {"phase":"memory_loaded","threadId":"trace-demo","userId":"reader-42","langsmithRunId":"...","messages":0,"longTermMemories":0}
```

Attach feedback to a run:

```bash
curl -X POST http://localhost:8000/feedback \
  -H 'content-type: application/json' \
  -d '{"run_id":"RUN_ID_FROM_STREAM","key":"user_rating","score":1,"comment":"Useful answer."}'
```

## API Contract

### `POST /agent/run`

Runs the inherited memory agent and optionally creates a LangSmith trace.

Request:

```json
{
  "thread_id": "trace-demo",
  "user_id": "reader-42",
  "prompt": "Recommend one short book about observability.",
  "temperature": 0.4,
  "max_tokens": 1024,
  "history": []
}
```

Key SSE additions:

| Field | Location | Meaning |
| ----- | -------- | ------- |
| `langsmithRunId` | `status.phase=memory_loaded` | LangSmith run id, or `null` when tracing is disabled. |
| `userId` | `status.phase=memory_loaded` | User namespace used for memory recall and trace metadata. |
| `longTermMemories` | `status.phase=memory_loaded` | Count of recalled memories. |

### `POST /feedback`

Attaches user or reviewer feedback to a LangSmith run.

Request:

```json
{
  "run_id": "6f1328d2-...",
  "key": "user_rating",
  "score": 1,
  "comment": "Useful answer."
}
```

Response:

```json
{
  "runId": "6f1328d2-...",
  "accepted": true
}
```

If LangSmith is disabled, the endpoint returns `accepted: false` instead of failing local development.

### Inherited Endpoints

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `GET` | `/memory/{user_id}` | List inherited long-term memories. |
| `GET` | `/memory/{user_id}/summary` | Summarize what the agent knows about a user. |
| `DELETE` | `/memory/{user_id}` | Delete inherited long-term memories. |
| `DELETE` | `/threads/{thread_id}` | Delete inherited short-term thread memory. |
| `GET` | `/metrics` | Prometheus scrape endpoint. |
| `GET` | `/healthz` | Liveness probe. |
| `GET` | `/readyz` | Readiness probe. |

## Configuration

| Env var | Default | Purpose |
| ------- | ------- | ------- |
| `LANGSMITH_TRACING` | `false` | Enables LangSmith API calls. |
| `LANGSMITH_API_KEY` | unset | LangSmith API key. |
| `LANGSMITH_PROJECT` | `nebius-cookbook-observability` | LangSmith project name. |
| `LANGSMITH_ENDPOINT` | `https://api.smith.langchain.com` | LangSmith API URL. |
| `MEMORY_BACKEND` | `postgres` | Inherited memory backend. |
| `POSTGRESQL_ADDON_URI` | local Postgres URL | Inherited memory database. Clever Cloud injects this when a Postgres add-on is linked. |
| `NEBIUS_API_KEY` | required | Nebius API key. |

Cookbooks #6-#10 can share one Postgres database by using different schemas.
The schema is derived from `ENV` and the cookbook number: `dev_cbk_07` locally, `prod_cbk_07` when `ENV=production`.
The app creates `prod_cbk_07.user_memories` on first use, separate from cookbook #6's `prod_cbk_06.user_memories`.

## Implementation Notes

`app/core/langsmith_observability.py` is a narrow adapter around `langsmith.Client`.
It creates a run before memory recall and generation, updates the run after the final answer, and stores feedback through `/feedback`.

The adapter redacts emails and phone numbers before sending prompt and output previews.
It records `cookbook`, `env`, `thread_id`, and `user_id` as metadata.
Those identifiers are useful for debugging, but they still count as user-related data in many systems, so treat LangSmith as a production telemetry destination.

Tracing failures do not break the agent response.
If LangSmith is unavailable, the service logs a warning and continues.
That is intentional because observability should not become an availability dependency for the agent path.

## Production Checklist

- Use separate LangSmith projects for development, staging, and production.
- Redact or hash identifiers if your privacy policy requires it.
- Decide which prompt and output previews are allowed in traces.
- Attach deployment version, model id, and cookbook name to every trace.
- Keep Prometheus metrics for service-level latency and error rates.
- Use LangSmith for run-level debugging, feedback review, and qualitative failure analysis.

## Failure Modes

| Symptom | Likely cause | Handling |
| ------- | ------------ | -------- |
| `langsmithRunId` is `null` | Tracing disabled or missing key | Set `LANGSMITH_TRACING=true` and configure `LANGSMITH_API_KEY`. |
| Feedback returns `accepted:false` | LangSmith disabled | Enable tracing before using feedback in production. |
| Traces contain sensitive data | Overly broad previews or metadata | Redact previews and avoid raw PII in metadata. |
| Agent works but trace is missing | LangSmith API error | Check logs for `langsmith_*_failed` warnings. |
| Prometheus looks healthy but answer is bad | Aggregate metrics hide behavior | Inspect the LangSmith trace and attach feedback. |

## Test It

```bash
uv run pytest
uv run ruff check
uv run ruff format --check
```

Tests keep `LANGSMITH_TRACING=false`.
They verify the disabled path and feedback endpoint without calling LangSmith.

## Going Further

- Add trace links to the web playground when `langsmithRunId` is present.
- Add evaluator feedback keys for correctness, helpfulness, and groundedness.
- Export failed-run examples into datasets for future evaluation.
- Continue to Cookbook #8 to enforce guardrails on the same observable agent.

## Reference

- LangSmith docs — [docs.langchain.com/langsmith/home](https://docs.langchain.com/langsmith/home)
- LangChain observability — [docs.langchain.com/oss/python/langchain/observability](https://docs.langchain.com/oss/python/langchain/observability)

## License

MIT
