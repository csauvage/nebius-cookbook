#!/usr/bin/env bun
import { readdir } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, "..");
const cookbooksDir = join(repoRoot, "cookbooks");

function run(cmd: string, args: string[], cwd: string): Promise<number> {
  return new Promise((resolveP) => {
    const child = spawn(cmd, args, { cwd, stdio: "inherit" });
    child.on("exit", (code) => resolveP(code ?? 1));
  });
}

const entries = await readdir(cookbooksDir, { withFileTypes: true });
const cookbooks = entries
  .filter((e) => e.isDirectory() && e.name !== "_template" && !e.name.startsWith("."))
  .map((e) => e.name)
  .sort();

let failed = 0;

for (const name of cookbooks) {
  const cwd = join(cookbooksDir, name);
  console.log(`\n=== ${name} ===`);

  for (const step of [
    ["uv", ["sync", "--frozen"]],
    ["uv", ["run", "ruff", "check"]],
    ["uv", ["run", "ruff", "format", "--check"]],
    ["uv", ["run", "pytest"]],
  ] as const) {
    const code = await run(step[0], step[1] as string[], cwd);
    if (code !== 0) {
      console.error(`✗ ${name}: ${step[0]} ${step[1].join(" ")} (exit ${code})`);
      failed++;
      break;
    }
  }
}

if (failed > 0) {
  console.error(`\n${failed} cookbook${failed === 1 ? "" : "s"} failed.`);
  process.exit(1);
}

console.log(`\nAll ${cookbooks.length} cookbook${cookbooks.length === 1 ? "" : "s"} passed.`);
