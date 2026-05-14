import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { getRecipes } from "@/lib/recipes";
import { Badge, Container, NebiusLogo } from "@/components";
import { GITHUB_REPO_URL } from "@/lib/site";

export default function HomePage() {
  const recipes = getRecipes();

  return (
    <main className="min-h-dvh">
      <Container size="lg" className="pt-24 pb-24 sm:pt-32">
        {/* Masthead */}
        <header className="mb-20 grid gap-8 sm:grid-cols-[auto_1fr] sm:items-end">
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <NebiusLogo height={28} />
              <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-ink-soft">
                / Cookbook · v0.1
              </span>
              <span className="ml-1 inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
                <span className="size-1.5 rounded-full bg-accent phosphor-dot" aria-hidden />
                live
              </span>
            </div>
            <h1 className="font-display text-[88px] leading-[0.85] tracking-[0.01em] text-ink sm:text-[128px]">
              Production agents,
              <br />
              <span className="text-accent">unforked.</span>
            </h1>
          </div>

          <p className="max-w-md text-lg italic leading-snug text-ink-soft sm:justify-self-end sm:text-right">
            Runnable, observable, deployable recipes for building AI agents on Nebius AgentKit. No
            magic, no toy code.
          </p>
        </header>

        {/* Stat row */}
        <div className="mb-16 grid grid-cols-2 gap-px border-y border-edge bg-edge sm:grid-cols-4">
          <Stat label="recipes" value={String(recipes.length)} />
          <Stat label="frameworks" value="fastapi" />
          <Stat label="runtime" value="python 3.12" />
          <Stat label="provider" value="nebius" />
        </div>

        {/* Recipes index */}
        <section>
          <div className="mb-6 flex items-baseline justify-between">
            <h2 className="font-mono text-[11px] uppercase tracking-[0.22em] text-ink-soft">
              ▸ Recipes
            </h2>
            <span className="font-mono text-[11px] text-ink-dim">
              {String(recipes.length).padStart(2, "0")} ↦ ∞
            </span>
          </div>

          {recipes.length === 0 ? (
            <p className="font-mono text-sm text-ink-dim">No recipes yet.</p>
          ) : (
            <ul className="border-t border-edge">
              {recipes.map((r) => (
                <li key={r.slug} className="border-b border-edge">
                  <Link
                    href={`/recipes/${r.slug}`}
                    className="group flex flex-col gap-2 py-6 transition sm:flex-row sm:items-baseline sm:gap-6 sm:py-7"
                  >
                    <span className="font-mono text-xs text-ink-dim sm:w-16">
                      {String(r.order).padStart(2, "0")}
                    </span>
                    <div className="min-w-0 flex-1 space-y-1">
                      <div className="flex items-baseline gap-3">
                        <h3 className="font-display text-3xl leading-none text-ink transition group-hover:text-accent sm:text-4xl">
                          {r.title}
                        </h3>
                        <ArrowUpRight className="size-4 shrink-0 text-ink-dim transition group-hover:text-accent group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                      </div>
                      <p className="text-sm leading-relaxed text-ink-soft">{r.tagline}</p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2 sm:flex-col sm:items-end sm:gap-1.5 sm:text-right">
                      <Badge tone={r.difficulty === "beginner" ? "neutral" : r.difficulty === "intermediate" ? "accent" : "warn"}>
                        {r.difficulty}
                      </Badge>
                      <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-dim">
                        {r.estimatedReadingTime}
                      </span>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Footer */}
        <footer className="mt-24 flex flex-wrap items-center justify-between gap-4 border-t border-edge pt-6 font-mono text-[11px] uppercase tracking-[0.16em] text-ink-dim">
          <span>// June 4, 2026 · 5 recipes for launch</span>
          <a
            href={GITHUB_REPO_URL}
            className="transition hover:text-accent"
            target="_blank"
            rel="noreferrer"
          >
            github ↗
          </a>
        </footer>
      </Container>
    </main>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-paper px-5 py-5">
      <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-dim">{label}</div>
      <div className="mt-1 font-display text-4xl leading-none text-ink">{value}</div>
    </div>
  );
}
