# Your First Agent on Nebius

> A production-grade FastAPI agent with streaming, observability, and zero magic.

You called OpenAI from a Python script and it worked. Now what?

This recipe is the bridge between that script and something you would actually deploy. It is a small FastAPI service that streams a Nebius chat completion as Server-Sent Events. The Nebius integration is one line. Everything else — the structured logs, the Prometheus metrics, the rate limit, the security headers, the Dockerfile, the tests — is the shape of a service you can hand to ops without blushing.

## What you'll build

A single-endpoint API:

| Endpoint | Description |
|---|---|
| `POST /agent/run` | Streams `status`, `token`, `done` SSE events |
| `GET /healthz` | Liveness probe |
| `GET /readyz` | Readiness probe |
| `GET /metrics` | Prometheus scrape endpoint |
| `GET /docs` | OpenAPI / Swagger UI |

Everything is typed, every env var validated, every request tagged with a request ID, every Nebius call wrapped in tenacity-backed retries.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- A Nebius API key — get one from the [Nebius console](https://nebius.com)
- (optional) Docker, if you want to build the production image

## Run it

```bash
git clone https://github.com/csauvage/nebius-cookbook.git
cd cookbook/cookbooks/01-first-agent-on-nebius

cp .env.example .env
# Open .env and fill NEBIUS_API_KEY

uv sync
make dev
```

In another terminal:

```bash
curl -N -X POST http://localhost:8000/agent/run \
  -H 'content-type: application/json' \
  -d '{"prompt":"Explain Nebius AgentKit in one paragraph."}'
```

You'll see SSE events arriving:

```
event: status
data: {"phase":"thinking"}

event: token
data: {"text":"Nebius"}

event: token
data: {"text":" Token"}

…

event: status
data: {"phase":"done"}

event: done
data: {}
```

## Walk-through

### The directory

```
app/
├── main.py              # FastAPI app, lifespan, middleware
├── config.py            # Pydantic Settings, validated at boot
├── routes/
│   ├── agent.py         # POST /agent/run with SSE
│   └── health.py        # /healthz, /readyz
├── schemas/
│   └── agent.py         # Pydantic I/O models
├── core/
│   ├── nebius_client.py # OpenAI SDK pointed at Nebius
│   └── agent.py         # The agent logic
└── observability/
    ├── logging.py       # structlog (JSON in prod)
    ├── metrics.py       # Prometheus counters/histograms
    └── middleware.py    # Request IDs, security headers, body-size limit
```

### The Nebius integration

The SDK swap is one line — `base_url` points at Nebius:

```python
AsyncOpenAI(
    api_key=settings.nebius_api_key,
    base_url=str(settings.nebius_base_url),  # https://api.studio.nebius.ai/v1/
    timeout=httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0),
)
```

Timeouts are explicit. Retries on transient errors are owned by [`tenacity`](https://tenacity.readthedocs.io), not the SDK, so you can swap the backoff strategy without touching SDK internals.

### The observability

Every request gets a UUID request ID, returned in the `x-request-id` header and bound to the structlog context so every log line for that request carries it. In production (`ENV=production`) logs render as JSON. In dev they render as human-readable lines.

A sample log line in production:

```json
{
  "event": "agent_started",
  "level": "info",
  "request_id": "9a8f3c…",
  "path": "/agent/run",
  "model": "meta-llama/Llama-3.3-70B-Instruct",
  "timestamp": "2026-06-04T12:31:42.103Z"
}
```

Prometheus metrics include:

- `http_requests_total{method,path,status}` — request counter
- `http_request_duration_seconds{method,path}` — latency histogram
- `nebius_tokens_total{model,type}` — tokens streamed back from Nebius
- `nebius_request_duration_seconds{model}` — Nebius call duration

### The streaming

The route handler returns a `StreamingResponse` with `text/event-stream`. Events are named — `status`, `token`, `done`, `heartbeat`, `error` — rather than raw text, so a client can switch on the event name. A heartbeat is emitted every 15 seconds when there is no other traffic, and the route watches `request.is_disconnected()` to cancel the upstream Nebius call as soon as the client goes away.

### The hardening

- `slowapi` rate-limits `/agent/run` at 10 requests per minute per IP
- CORS is allowlist-based, never `*` in production (validated at boot)
- Security headers: `x-content-type-options`, `referrer-policy`, `strict-transport-security`
- Request bodies above 64 KB are rejected with 413
- Lifespan handlers log startup and shutdown; on shutdown we close the HTTP client and let in-flight requests drain

## Test it

```bash
make test
```

Tests use [respx](https://lundberg.github.io/respx/) to mock every Nebius call. No network is hit. CI passes on a laptop in airplane mode.

## Ship it

Build the production image:

```bash
make docker
```

The Dockerfile is multi-stage, uses [`astral-sh/uv`](https://github.com/astral-sh/uv) for the build, and ends in a slim Python 3.12 image running as a non-root user with a healthcheck wired to `/healthz`.

Deployment-specific instructions for Nebius Compute live in [`docs/deployment.md`](../../docs/deployment.md).

## Going further

- **Cookbook #2 — [Real-World Data: Nebius + Tavily](../02-real-world-data-nebius-tavily/)** — adds fresh web facts via Tavily and per-step model routing for 10× cost savings.
- Adding OpenTelemetry tracing — feed `traceparent` into the request context middleware.
- Adding authentication — drop in a JWT verifier as a FastAPI `Depends`.

## License

MIT — see [`LICENSE`](../../LICENSE).
