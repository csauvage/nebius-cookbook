# Deployment

This doc covers two deployment targets that ship together:

1. **The catalog site** — Next.js app, hosted on [Clever Cloud](https://www.clever-cloud.com), auto-deployed on push to `main`.
2. **Each cookbook** — a FastAPI service, deployed to [Nebius Compute](https://nebius.com) on demand.

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

A push to `main` triggers `.github/workflows/deploy-app.yml`, which:

1. Builds the app in CI
2. Pushes to the Clever Cloud git remote (`clever`)
3. Clever Cloud builds and rolls out the new release

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

The recommended path is Nebius Compute with a managed container service. Verify the exact target (VM image vs. serverless containers) against the current Nebius docs — this is an open question on the project (see [`AGENTS.md`](../AGENTS.md) §16).

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
| `test-cookbooks.yml` | push, PR | For each cookbook: `uv sync --frozen`, `ruff check`, `ruff format --check`, `pytest` |
| `build-app.yml` | push, PR | `bun install`, `bun run build:recipes`, `cd app && bun run build` |
| `deploy-app.yml` | push to `main` | Build the app and push to Clever Cloud |

All four are defined in `.github/workflows/`.

## Disaster recovery

- **Catalog site outage:** Clever Cloud rollback as above. The site is static enough that traffic can also be served by any static host from the build artifact.
- **A cookbook outage:** Each cookbook is independently deployable; rolling back one does not affect any other.
- **A leaked Nebius key:** Rotate via the Nebius console, update the deploy env, restart the service. The catalog site does not have a Nebius key — only individual cookbooks do.
