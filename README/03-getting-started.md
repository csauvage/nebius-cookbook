## Getting started

### Run a recipe

Every recipe is independent. Pick one, clone the repo, and follow the recipe's own README.

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

You should see Server-Sent Events streaming back, with `status`, `token`, and `done` events.

### Prerequisites

A laptop with:

- **Python 3.12** and [**uv**](https://docs.astral.sh/uv/) — for running cookbook recipes
- **Node 22** and [**Bun ≥ 1.1**](https://bun.sh) — only if you're working on the catalog site or build scripts
- A **Nebius API key** — get one from the [Nebius console](https://nebius.com)
- Optional: **Docker** — for building production images

If you only plan to read code and run one recipe, Python and uv are all you need.

### Work on the catalog site

The Next.js site that hosts this catalog lives in `app/`.

```bash
bun install
bun run build:recipes   # compile cookbook READMEs to MDX
cd app
bun run dev
```
