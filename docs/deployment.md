# Deployment

This doc covers two deployment targets that ship together:

1. **The catalog site** — Next.js app, hosted on [Clever Cloud](https://www.clever-cloud.com), auto-deployed on push to `main`.
2. **Each cookbook** — a FastAPI service, deployable independently to Clever Cloud or Nebius Compute.

The two are intentionally decoupled. The catalog never makes a runtime call to a cookbook.

## The catalog site (Clever Cloud)

### What runs in prod

A standard Next.js standalone build, served by Node 22 LTS. Build is performed by Bun in CI; production runtime is Node — never Bun.

### Configuration

The Clever Cloud app is configured to:

- Use the **Node 22** runtime
- Run `bun install && bun run build:recipes && bun run build` as the build command
- Start with `node app/.next/standalone/server.js`
- Read env vars from the Clever Cloud dashboard

Required env vars:

| Var | Value | Purpose |
|---|---|---|
| `NEXT_PUBLIC_SITE_URL` | `https://cookbook.nebius.com` | Canonical URL, OG tags |
| `NEXT_PUBLIC_GITHUB_REPO` | `https://github.com/csauvage/nebius-cookbook` | "Edit on GitHub" links |
| `NODE_ENV` | `production` | Standard |
| `PORT` | (set by Clever Cloud) | Bound automatically |

### Deploy

A push to `main` runs `test-cookbooks`, then `lint-app`, then `.github/workflows/deploy-app.yml`, which:

1. validates and tests the changed cookbooks;
2. validates, lints, typechecks, and builds the web deploy artifact;
3. asks Clever Cloud to rebuild and roll out the catalog app.

Manual deploy from a developer machine is supported but unusual:

```bash
clever login
clever link <app-id>
clever deploy
```

### Rollback

```bash
clever activity   # find the previous successful commit
clever deploy --commit <sha>
```

## Cookbook backends on Clever Cloud

Cookbook FastAPI backends can also be deployed as independent Clever Cloud Python/uv apps.
The workflow only rebuilds a backend when runtime code in that cookbook changed.

### Configuration

Create one Clever Cloud app per cookbook backend you want to deploy, then add a repository variable named `COOKBOOK_CLEVER_CONFIG`.
It is a JSON object keyed by cookbook folder name.
Each cookbook entry contains:

- `app_id` — the GitHub repository variable name that stores the Clever app ID;
- `vars` — GitHub repository variable names to sync into Clever;
- `secrets` — GitHub repository secret names to sync into Clever.

```json
{
  "09-actions-with-mcp-stripe": {
    "app_id": "CLEVER_APP_ID_09",
    "vars": [
      "ENV",
      "LOG_LEVEL",
      "CORS_ORIGINS",
      "LANGSMITH_PROJECT",
      "BOOK_CATALOG_PATH",
      "APPROVAL_TTL_SECONDS"
    ],
    "secrets": [
      "NEBIUS_API_KEY",
      "STRIPE_MCP_API_KEY",
      "MEMORY_DATABASE_URL",
      "LANGSMITH_API_KEY"
    ]
  }
}
```

The workflow uses the shared `CLEVER_TOKEN` and `CLEVER_SECRET` repository secrets.
GitHub Actions is also the source of truth for backend runtime configuration.
Before each deploy, it resolves the configured GitHub variable and secret names, then pushes those values into the target Clever app using the same environment variable names.
For the example above, create a repository variable named `CLEVER_APP_ID_09`, repository variables such as `ENV` and `BOOK_CATALOG_PATH`, and repository secrets such as `NEBIUS_API_KEY` and `STRIPE_MCP_API_KEY`.
Use plain shared names by default.
Only introduce a cookbook-specific prefix, such as `COOKBOOK_09_NEBIUS_API_KEY`, when that cookbook must use a different value from the shared `NEBIUS_API_KEY`.

### What triggers a backend rebuild

`.github/workflows/test-cookbooks.yml` detects changed runtime paths per cookbook.
It tests only changed cookbooks, then publishes the changed cookbook list as a short-lived artifact.
`.github/workflows/deploy-cookbooks.yml` consumes that artifact and deploys only changed cookbooks that are present in `COOKBOOK_CLEVER_APPS`.

Runtime-impacting paths include:

- `app/**`
- `scripts/**`
- `pyproject.toml`
- `uv.lock`
- `.python-version`
- `Dockerfile`
- `Makefile`
- `.env.example`

Docs and metadata changes such as `README.md`, `docs/**`, `recipe.json`, and `assets/**` do not trigger backend tests or deploys.

### Clever runtime

The backend deploy workflow configures each mapped Clever app with:

```text
APP_FOLDER=cookbooks/<slug>
CC_PYTHON_BACKEND=uvicorn
CC_PYTHON_UV_RUN_COMMAND=uv run uvicorn app.main:app --host 0.0.0.0 --port 8080
PORT=8080
```

## A cookbook on Nebius Compute

Each cookbook ships as a containerized FastAPI service.

### Build the image

```bash
cd cookbooks/NN-<slug>
make docker
```

The Dockerfile is multi-stage, ends in a slim `python:3.12-slim` runtime as a non-root user, and includes a healthcheck wired to `/healthz`.

### Push to Nebius Container Registry

```bash
docker tag <slug>:dev registry.nebius.com/<your-project>/<slug>:$(git rev-parse --short HEAD)
docker push registry.nebius.com/<your-project>/<slug>:$(git rev-parse --short HEAD)
```

(Authentication via `docker login registry.nebius.com` — see the Nebius docs for the exact flow.)

### Deploy

The recommended path is Nebius Compute with a managed container service. Verify the exact target (VM image vs. serverless containers) against the current Nebius docs — this is still an open question and may evolve before launch.

A reference `make deploy` target lives in each cookbook's Makefile. It is intentionally a no-op stub: customize once you know your deployment target.

### Secrets

Never bake secrets into the image. The cookbook reads `NEBIUS_API_KEY` (and any partner keys) from environment variables, validated at boot by `pydantic-settings`. Inject these via the Nebius Compute env config or a secrets store.

### Healthchecks

Every cookbook exposes:

- `GET /healthz` — liveness (process is up)
- `GET /readyz` — readiness (process is up and dependencies, if any, are reachable)

Configure your orchestrator to use `/readyz` for traffic admission and `/healthz` for restart decisions.

### Observability

The cookbook emits Prometheus metrics on `/metrics`. Point your Prometheus scraper at it, or pipe to a managed service. JSON logs go to stdout — capture them via your container runtime's standard log stream.

## CI workflows

| Workflow | Trigger | What it does |
|---|---|---|
| `validate-recipes.yml` | push, PR | `bun run validate`, `bun run build:readme --check` |
| `test-cookbooks.yml` | push, PR | For changed cookbook runtime code: `uv sync --frozen`, `ruff check`, `ruff format --check`, `pytest` |
| `lint-app.yml` | after `test-cookbooks`, PR | `bun install`, recipe validation, README check, recipe manifest, app lint/typecheck, deploy artifact build |
| `deploy-app.yml` | after `lint-app` on `main` | Ask Clever Cloud to rebuild and roll out the catalog app |
| `deploy-cookbooks.yml` | after `test-cookbooks` on `main` | Deploy changed mapped cookbook backends to Clever Cloud |

All workflows are defined in `.github/workflows/`.

## Disaster recovery

- **Catalog site outage:** Clever Cloud rollback as above. The site is static enough that traffic can also be served by any static host from the build artifact.
- **A cookbook outage:** Each cookbook is independently deployable; rolling back one does not affect any other.
- **A leaked Nebius key:** Rotate via the Nebius console, update the deploy env, restart the service. The catalog site does not have a Nebius key — only individual cookbooks do.
