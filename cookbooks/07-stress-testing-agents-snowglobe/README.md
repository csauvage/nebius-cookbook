# Confidence — Stress-Testing Agents with Snowglobe

> 🚧 **Scaffold only.** This recipe is planned but not yet implemented. This
> folder currently holds metadata (`recipe.json`) and this documentation. The
> `app/`, tests, and Docker setup will land in a later pass.

Recipe **07 of 7** in the Nebius Cookbook arc:

> Foundation → Retrieval → Awareness → Orchestration → Memory → Reliability → **Confidence**

You've built, grounded, hardened the agent. You still don't know how it behaves
across the thousands of conversations you'll never hand-test. This recipe closes
the arc by replacing hope with evidence.

## What you'll build

A FastAPI service plus a simulation harness around [Snowglobe](https://snowglobetx.com):

1. **Generate** — Snowglobe produces synthetic personas and conversation
   scenarios from a description of your agent.
2. **Run** — each scenario is played against the agent at scale.
3. **Score** — transcripts are graded for failures, regressions, and
   edge-case behaviour, with a summary you can gate a CI pipeline on.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- A Nebius API key — get one from the [Nebius console](https://nebius.com)
- A LangSmith API key — [Snowglobe](https://snowglobetx.com) runs on LangChain's
  platform, so it authenticates with a LangSmith key. Get one and read the docs
  at [docs.langchain.com/langsmith](https://docs.langchain.com/langsmith/home).
  The service reads it from `LANGSMITH_API_KEY`.

## Planned architecture

```
agent description ──► Snowglobe ──► personas + scenarios
                                          │
                                          ▼
                          run each scenario vs /agent/run
                                          │
                                          ▼
                  critic model scores transcripts ──► report ──► CI gate
```

- **Agent model:** `meta-llama/Llama-3.3-70B-Instruct` — the agent under test.
- **Critic model:** `Qwen/Qwen3-30B-A3B-Instruct` — scores transcripts against
  the success criteria.

## Design decisions

**Simulation catches what unit tests cannot.** A unit test asserts a known
input yields a known output. An agent's risk surface is the *unknown* inputs —
paraphrases, adversarial users, multi-turn drift. Simulation samples that space;
it complements the `respx`-mocked suites in earlier recipes, it does not replace
them.

**Gate on regression delta, not absolute score.** An LLM-judged score has no
meaningful absolute zero — "82%" is not a fact, it is a measurement under one
rubric and one judge. What *is* reliable is the *change* between two runs of the
same suite. CI should fail on a drop versus the baseline, not on missing an
arbitrary bar.

**Treat a sampled suite statistically.** Sampling variance means a single run
can pass or fail by luck. Either fix the seeds for reproducibility, or run
enough scenarios that the gate compares distributions, not point values — and
size the gate's tolerance to the suite's noise floor. A flaky gate gets muted,
and a muted gate protects nothing.

**The judge is a component — version and audit it.** The critic model decides
what counts as a failure, so judge drift *is* score drift. Pin the judge model,
keep its rubric in version control, and periodically check it against a small
human-labelled set. An un-audited judge silently redefines "passing."

**Beware overfitting to the simulator.** Tune the agent until it pleases
Snowglobe and you have built an agent that is good at Snowglobe. Keep a holdout
set of scenarios out of the tuning loop, the same discipline as a train/test
split.

## Failure modes to design for

| Symptom | Cause | Handling |
|---|---|---|
| Green CI, unhappy users | Agent overfit to the simulator | Hold out scenarios; refresh the persona set periodically |
| Gate flaps run-to-run | Sampling variance | Fix seeds, or widen the gate to the measured noise floor |
| Scores drift with no code change | Judge model updated | Pin the judge; treat a judge change as a baseline reset |
| Simulation cost explodes | Full matrix run on every commit | Smoke set per-commit, full suite nightly / pre-release |
| A real regression slips through | Scenario coverage gap | Add the missed case to the suite when an incident is found — sims grow from production |

## Planned endpoints

| Method | Path          | Purpose                                                    |
| ------ | ------------- | ---------------------------------------------------------- |
| POST   | `/agent/run`  | Run the agent under test, streamed as SSE.                 |
| POST   | `/simulate`   | Launch a Snowglobe simulation batch and return scored results. |
| GET    | `/healthz`    | Liveness probe.                                            |
| GET    | `/readyz`     | Readiness probe.                                           |
| GET    | `/metrics`    | Prometheus scrape endpoint.                                |

## Status

- [x] `recipe.json` metadata
- [x] Documentation scaffold
- [ ] `app/` implementation
- [ ] Tests
- [ ] Dockerfile + Makefile
- [ ] `docs/deployment.md`

## Reference

- Snowglobe — [snowglobetx.com](https://snowglobetx.com)
- LangSmith — [docs.langchain.com/langsmith](https://docs.langchain.com/langsmith/home)

## Going further

This is the final recipe in the arc. From here, point the simulation harness at
your own agent and wire `/simulate` into your CI pipeline — a smoke set on every
commit, the full suite before each release.

## License

MIT
