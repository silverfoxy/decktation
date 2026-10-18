#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

const VERSION_RE = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$/;

function readJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

function writeJson(path, value) {
  writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`);
}

function versions() {
  const packageJson = readJson("package.json");
  const pluginJson = readJson("plugin.json");

  return {
    packageJson,
    pluginJson,
    version: packageJson.version,
    values: {
      "package.json": packageJson.version,
      "plugin.json": pluginJson.version,
    },
  };
}

function fail(message) {
  console.error(`error: ${message}`);
  process.exitCode = 1;
}

export function nextDevelopmentVersion(version, commitSha, branch) {
  const match = VERSION_RE.exec(version);
  if (!match || !commitSha) {
    return null;
  }

  const [, major, minor, patch] = match;
  let branchLabel = "";
  if (branch && branch !== "master") {
    if (typeof branch !== "string") return null;
    const slug = branch.replace(/[^A-Za-z0-9-]+/g, "-").replace(/^-|-$/g, "");
    if (!slug) return null;
    const label = /^\d+$/.test(slug) ? `branch-${slug}` : slug;
    const needsHash = label.length > 36 || /[^A-Za-z0-9/-]/.test(branch);
    const suffix = needsHash ? `-${createHash("sha256").update(branch).digest("hex").slice(0, 8)}` : "";
    branchLabel = `${label.slice(0, 36).replace(/-$/g, "")}${suffix}.`;
  }
  return `${major}.${minor}.${Number(patch) + 1}-dev.${branchLabel}${commitSha.slice(0, 7)}`;
}

function exactHeadTags() {
  try {
    return execFileSync("git", ["tag", "--points-at", "HEAD"], {
      encoding: "utf8",
    }).trim().split("\n").filter((tag) => tag.startsWith("v"));
  } catch {
    return [];
  }
}

function check(expectedTag) {
  const state = versions();

  if (!VERSION_RE.test(state.version)) {
    fail(`package.json version ${JSON.stringify(state.version)} is not valid SemVer`);
  }

  for (const [path, value] of Object.entries(state.values)) {
    if (value !== state.version) {
      fail(`${path} has ${JSON.stringify(value)}; expected ${state.version}`);
    }
  }

  const tags = expectedTag ? [expectedTag] : exactHeadTags();
  for (const tag of tags) {
    if (tag !== `v${state.version}`) {
      fail(`tag ${tag} does not match manifest version v${state.version}`);
    }
  }

  if (process.exitCode) return;
  console.log(`Version ${state.version} is synchronized${tags.length ? ` with ${tags.join(", ")}` : ""}.`);
}

function main() {
  const [command = "check", argument, extraArgument, branch] = process.argv.slice(2);

  if (command === "print") {
    console.log(versions().version);
  } else if (command === "check") {
    check(argument);
  } else if (command === "set") {
    if (!argument || !VERSION_RE.test(argument)) {
      fail("usage: release-version.mjs set X.Y.Z");
    } else {
      const state = versions();
      state.packageJson.version = argument;
      state.pluginJson.version = argument;
      writeJson("package.json", state.packageJson);
      writeJson("plugin.json", state.pluginJson);
      console.log(`Updated release manifests to ${argument}.`);
    }
  } else if (command === "next-dev") {
    const version = nextDevelopmentVersion(argument, extraArgument, branch);
    if (!version) {
      fail("usage: release-version.mjs next-dev X.Y.Z COMMIT_SHA [BRANCH]");
    } else {
      console.log(version);
    }
  } else {
    fail(`unknown command ${JSON.stringify(command)}`);
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main();
}
