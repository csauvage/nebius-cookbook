# Actions — Making Actions with MCP and Stripe

> 🚧 **Scaffold only.** This recipe is planned but not yet implemented. This folder currently holds metadata and documentation for the MCP actions cookbook.

Recipe **09 of 10** in the Nebius Cookbook arc:

> Foundation → Retrieval → Grounding → Orchestration → Thread Memory → User Memory → Observability → Guardrails → **Actions** → Simulation

After guardrails, the next step is letting the agent do something outside chat.
In this cookbook, the book agent creates a Stripe test-mode checkout link for a fictional book purchase through MCP.

## What you'll build

A FastAPI service that connects an action-capable agent to Stripe through MCP:

1. **MCP tool access** — the agent discovers Stripe actions through an MCP server.
2. **Human approval** — payment-link creation pauses until explicitly approved.
3. **Test-mode Stripe** — live runs use Stripe test keys only.
4. **Auditable action events** — SSE reports pending, approved, rejected, and completed action states.

## Planned flow

```text
user asks to buy a fake book
  └─► agent proposes Stripe payment link
      └─► approval required
          ├─► reject: no external action
          └─► approve: Stripe MCP creates test-mode payment link
```

## Planned endpoints

| Method | Path | Purpose |
| ------ | ---- | ------- |
| POST | `/agent/run` | Run the action-capable agent and stream approval/action events. |
| POST | `/approvals/{approval_id}` | Approve or reject a pending Stripe action. |
| GET | `/healthz` | Liveness probe. |
| GET | `/readyz` | Readiness probe. |
| GET | `/metrics` | Prometheus scrape endpoint. |

## Design decisions

**Use Stripe test mode.** The cookbook should demonstrate a real external action without moving real money.

**Require approval before side effects.** The model can propose an action, but the server controls whether the MCP tool call executes.

**Mock actions in tests.** CI never calls Stripe or an MCP server by default.

## Reference

- Stripe MCP — [docs.stripe.com/mcp](https://docs.stripe.com/mcp?locale=en-GB)
- LangChain MCP — [docs.langchain.com/oss/python/langchain/mcp](https://docs.langchain.com/oss/python/langchain/mcp)

## License

MIT
