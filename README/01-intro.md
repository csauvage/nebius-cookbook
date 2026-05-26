<h1 align="center">Nebius Cookbook</h1>

<p align="center">
  <strong>Production-grade recipes for building AI agents on <a href="https://nebius.com/services/token-factory">Nebius AgentKit</a>.</strong>
</p>

<p align="center">
  <a href="https://github.com/csauvage/nebius-cookbook/actions/workflows/validate-recipes.yml"><img alt="validate" src="https://img.shields.io/github/actions/workflow/status/csauvage/nebius-cookbook/validate-recipes.yml?label=validate"></a>
  <a href="https://github.com/csauvage/nebius-cookbook/actions/workflows/test-cookbooks.yml"><img alt="tests" src="https://img.shields.io/github/actions/workflow/status/csauvage/nebius-cookbook/test-cookbooks.yml?label=tests"></a>
  <a href="./LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
</p>

---

The Nebius Cookbook is a curated collection of runnable, production-shaped recipes for building AI agents on Nebius AgentKit. Every recipe is a real FastAPI application — typed, observable, containerized, and tested — that you can clone, configure, and deploy in five minutes.

It is for engineers who have called an LLM API from a script and want to know what the gap looks like between that script and something they would actually ship.

**What "production-shaped" means here:**

- Type hints on every signature and Pydantic models on every boundary
- Structured JSON logging with request IDs
- Prometheus metrics and healthcheck endpoints out of the box
- Rate limiting, CORS, security headers, graceful shutdown
- A multi-stage Dockerfile and a one-command deployment recipe
- Tests that pass with no network access

Each recipe is **autonomous** — cloning a single cookbook directory is enough to run it, with no shared base packages and no implicit dependencies on the rest of the repo.

The recipes are also a **sequence**. They form a narrative arc — Foundation → Retrieval → Grounding → Orchestration → Thread Memory → User Memory → Observability → Guardrails → Actions → Simulation — and each one assumes the concepts of the one before it: #2 builds on #1, #3 on #2, and so on. You *can* run any cookbook on its own, but the documentation is written for a reader following them in order.
