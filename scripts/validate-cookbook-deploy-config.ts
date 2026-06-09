#!/usr/bin/env bun
import { existsSync } from "node:fs";
import { readdir, readFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, "..");
const cookbooksDir = join(repoRoot, "cookbooks");
const configPath = join(repoRoot, ".github", "cookbook-clever-config.json");
const workflowPath = join(repoRoot, ".github", "workflows", "deploy-cookbooks.yml");

type DeployConfig = {
  app_id?: unknown;
  values?: unknown;
  mapped_vars?: unknown;
  addons?: unknown;
  vars?: unknown;
  secrets?: unknown;
  unset?: unknown;
};

const errors: string[] = [];

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string" && item.length > 0);
}

function isStringRecord(value: unknown): value is Record<string, string> {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value) &&
    Object.entries(value).every(
      ([key, item]) => key.length > 0 && typeof item === "string" && item.length > 0,
    )
  );
}

function collectWorkflowEnvNames(workflow: string): Set<string> {
  const names = new Set<string>();
  const envBindingPattern =
    /^\s{10}([A-Z0-9_]+):\s*\$\{\{\s*(?:vars|secrets)\.[A-Z0-9_]+\s*\}\}/gm;
  for (const match of workflow.matchAll(envBindingPattern)) {
    const name = match[1];
    if (name) names.add(name);
  }
  return names;
}

const config = JSON.parse(await readFile(configPath, "utf8")) as unknown;
if (typeof config !== "object" || config === null || Array.isArray(config)) {
  errors.push(`${configPath}: must be a JSON object keyed by cookbook directory`);
}

const workflow = await readFile(workflowPath, "utf8");
const workflowEnvNames = collectWorkflowEnvNames(workflow);

const entries = await readdir(cookbooksDir, { withFileTypes: true });
const cookbookDirs = entries
  .filter((entry) => entry.isDirectory())
  .map((entry) => entry.name)
  .filter((name) => name !== "_template" && !name.startsWith("."))
  .sort();

const deployableCookbooks = cookbookDirs.filter((name) =>
  existsSync(join(cookbooksDir, name, "pyproject.toml")),
);
const scaffoldCookbooks = cookbookDirs.filter((name) => !deployableCookbooks.includes(name));
const configByCookbook = (config ?? {}) as Record<string, DeployConfig>;

for (const cookbook of deployableCookbooks) {
  if (!configByCookbook[cookbook]) {
    errors.push(`${cookbook}: missing .github/cookbook-clever-config.json entry`);
  }
}

for (const cookbook of Object.keys(configByCookbook).sort()) {
  const entry = configByCookbook[cookbook];
  if (!cookbookDirs.includes(cookbook)) {
    errors.push(`${cookbook}: config entry does not match a cookbooks/ directory`);
    continue;
  }
  if (scaffoldCookbooks.includes(cookbook)) {
    errors.push(`${cookbook}: scaffold-only cookbook has Clever config but no pyproject.toml`);
  }

  if (typeof entry.app_id !== "string" || entry.app_id.length === 0) {
    errors.push(`${cookbook}: app_id must be a non-empty GitHub secret name`);
  } else if (!workflowEnvNames.has(entry.app_id)) {
    errors.push(`${cookbook}: app_id "${entry.app_id}" is not exposed in deploy-cookbooks.yml`);
  }

  for (const key of ["vars", "secrets", "addons", "unset"] as const) {
    const value = entry[key];
    if (value !== undefined && !isStringArray(value)) {
      errors.push(`${cookbook}: ${key} must be an array of non-empty strings`);
    }
  }

  if (entry.values !== undefined && !isStringRecord(entry.values)) {
    errors.push(`${cookbook}: values must be an object of string values`);
  }
  if (entry.mapped_vars !== undefined && !isStringRecord(entry.mapped_vars)) {
    errors.push(`${cookbook}: mapped_vars must map Clever env names to GitHub variable names`);
  }

  const referencedNames = [
    ...(isStringArray(entry.vars) ? entry.vars : []),
    ...(isStringArray(entry.secrets) ? entry.secrets : []),
    ...(isStringArray(entry.addons) ? entry.addons : []),
    ...(isStringRecord(entry.mapped_vars) ? Object.values(entry.mapped_vars) : []),
  ];
  for (const name of referencedNames) {
    if (!workflowEnvNames.has(name)) {
      errors.push(`${cookbook}: "${name}" is referenced but not exposed in deploy-cookbooks.yml`);
    }
  }
}

if (errors.length > 0) {
  console.error(
    `Cookbook deploy config validation failed (${errors.length} error${errors.length > 1 ? "s" : ""}):`,
  );
  for (const error of errors) console.error(`  - ${error}`);
  process.exit(1);
}

console.log(
  `Validated Clever deploy config for ${deployableCookbooks.length} deployable cookbook${deployableCookbooks.length === 1 ? "" : "s"}.`,
);
if (scaffoldCookbooks.length > 0) {
  console.log(
    `Skipped scaffold-only cookbook${scaffoldCookbooks.length === 1 ? "" : "s"}: ${scaffoldCookbooks.join(", ")}.`,
  );
}
