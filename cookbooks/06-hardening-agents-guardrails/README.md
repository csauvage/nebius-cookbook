# Reliability — Hardening Agents with Guardrails

> 🚧 **Scaffold only.** This recipe is planned but not yet implemented. This
> folder currently holds metadata (`recipe.json`) and this documentation. The
> `app/`, tests, and Docker setup will land in a later pass.

Recipe **06 of 7** in the Nebius Cookbook arc:

> Foundation → Retrieval → Awareness → Orchestration → Memory → **Reliability** → Confidence

By now the agent is capable — and capability is a liability. It can leak PII,
emit unsafe content, drift off-topic, or return malformed output that breaks
the code downstream of it. This recipe makes it safe to expose.

## What you'll build

A FastAPI service that wraps the agent in [Guardrails](https://www.guardrailsai.com/):

1. **Input validation** — PII detection, prompt-injection screening, and
   topic restriction run before the prompt ever reaches the model.
2. **Output validation** — schema conformance, toxicity, and groundedness
   checks run on the model's response.
3. **Re-ask loop** — when an output check fails, the agent is re-prompted with
   the validator's feedback rather than returning a bad answer.

The agent **fails closed**: a request that can't be validated is rejected, not
guessed at.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- A Nebius API key — get one from the [Nebius console](https://nebius.com)

## Planned architecture

```
request ──► input validators ──┬─► reject (fail closed)
                               └─► chat model ──► output validators ──┬─► re-ask (bounded)
                                                                      └─► SSE
```

- **Answer model:** `meta-llama/Llama-3.3-70B-Instruct`.
- **Critic model:** `Qwen/Qwen3-30B-A3B-Instruct` — backs the LLM-based
  validators (groundedness, topic) at a fraction of the cost.

## Design decisions

**Fail closed, not open.** A validator that can't reach a verdict — timeout,
error, ambiguous — must block the request. Failing open turns the guardrail
into decoration: it protects you exactly until the moment it is needed.

**Two gates, two cost tiers.** Input and output validation are distinct stages
with distinct economics. Cheap deterministic checks (regex PII, JSON schema)
run first and reject most bad traffic for microseconds. Expensive LLM-based
checks (groundedness, topic) run only on what survives. Ordering validators
cheapest-first is the single biggest lever on the latency tax.

**The streaming tension — and how to resolve it.** You cannot validate a token
you have not generated yet, so output validation and token streaming are in
genuine conflict. Two honest options: (a) **buffer then validate** — generate
fully, validate, then stream the approved text; the user waits but never sees
unsafe output; or (b) **stream optimistically, validate on completion** — fast,
but a failed check means retracting text already on screen. This recipe takes
(a): for a *hardening* recipe, correctness beats perceived speed. Document the
choice; do not let it be accidental.

**Bound the re-ask loop.** A re-ask loop with no ceiling is an unbounded cost
and latency sink — a stubborn failure retries forever. Cap it (2–3 attempts),
and on exhaustion fail closed with a clean error rather than returning the last
bad answer.

**Where guardrails run.** In-process keeps it simple and is the right default
here. At organisation scale, a validation *sidecar* lets multiple agents share
one policy — but that is a deployment topology decision, not a code one.

## Failure modes to design for

| Symptom | Cause | Handling |
|---|---|---|
| Legitimate traffic rejected | Validator false positive | Tune thresholds against a labelled set; log every rejection with the failing validator |
| Latency spikes | LLM-based validators on the hot path | Cheapest-first ordering; time-box LLM validators; cache verdicts where inputs repeat |
| Re-ask never converges | Model can't satisfy a validator | Hard cap on attempts; fail closed on exhaustion |
| Validator itself is injected | Prompt injection targets the groundedness check | Keep validator prompts separate from user content; never let user text reach a validator as instructions |
| Guardrail metrics flat | Validators wired but not firing | Emit pass/fail counters per validator; alert on a validator with zero traffic |

## Planned endpoints

| Method | Path          | Purpose                                                  |
| ------ | ------------- | -------------------------------------------------------- |
| POST   | `/agent/run`  | Run the guarded agent — validated I/O — streamed as SSE. |
| GET    | `/healthz`    | Liveness probe.                                          |
| GET    | `/readyz`     | Readiness probe.                                         |
| GET    | `/metrics`    | Prometheus scrape — includes guardrail pass/fail counters. |

## Status

- [x] `recipe.json` metadata
- [x] Documentation scaffold
- [ ] `app/` implementation
- [ ] Tests
- [ ] Dockerfile + Makefile
- [ ] `docs/deployment.md`

## Going further

Next in the arc: **[Confidence — Stress-Testing Agents with Snowglobe](../07-stress-testing-agents-snowglobe/)** —
a hardened agent still needs proof it holds up at scale.

## License

MIT
