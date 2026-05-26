# Simulation — Testing Before Production with Snowglobe

> 🚧 **Scaffold only.** This recipe is planned but not yet implemented. This folder currently holds metadata and documentation for the Snowglobe testing cookbook.

Recipe **09 of 10** in the Nebius Cookbook arc:

> Foundation → Retrieval → Grounding → Orchestration → Thread Memory → User Memory → Observability → Guardrails → **Simulation** → Actions

You've built, remembered, observed, and guarded the agent.
You still do not know how it behaves across the thousands of conversations you will never hand-test.

## What you'll build

A FastAPI service plus a simulation harness around Snowglobe:

1. **Generate** — Snowglobe produces synthetic personas and scenarios.
2. **Run** — each scenario is played against the agent.
3. **Score** — transcripts are judged for failures, regressions, and edge-case behavior.
4. **Gate** — a smoke suite can run in CI before release.

## Planned endpoints

| Method | Path | Purpose |
| ------ | ---- | ------- |
| POST | `/agent/run` | Run the agent under test and stream SSE events. |
| POST | `/simulate` | Launch a Snowglobe simulation batch and return scored results. |
| GET | `/healthz` | Liveness probe. |
| GET | `/readyz` | Readiness probe. |
| GET | `/metrics` | Prometheus scrape endpoint. |

## Design decisions

**Simulation complements tests.** Unit tests verify known cases.
Snowglobe samples the unknown conversational surface.

**Gate on deltas.** Absolute LLM-judge scores are noisy.
The CI story should compare against a baseline and fail on meaningful regression.

**Mock Snowglobe in tests.** No network calls run by default.
Live simulation requires LangSmith/Snowglobe credentials.

## Reference

- Snowglobe — [snowglobetx.com](https://snowglobetx.com)
- LangSmith — [docs.langchain.com/langsmith/home](https://docs.langchain.com/langsmith/home)

## License

MIT
