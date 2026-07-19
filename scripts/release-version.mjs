#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";

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
  const packageLock = readJson("package-lock.json");

  return {
    packageJson,
    pluginJson,
    packageLock,
    version: packageJson.version,
    values: {
      "package.json": packageJson.version,
      "plugin.json": pluginJson.version,
      "package-lock.json": packageLock.version,
      "package-lock.json root package": packageLock.packages?.[""]?.version,
    },
  };
}

function fail(message) {
  console.error(`error: ${message}`);
  process.exitCode = 1;
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

const [command = "check", argument] = process.argv.slice(2);

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
    state.packageLock.version = argument;
    state.packageLock.packages[""].version = argument;
    writeJson("package.json", state.packageJson);
    writeJson("plugin.json", state.pluginJson);
    writeJson("package-lock.json", state.packageLock);
    console.log(`Updated release manifests to ${argument}.`);
  }
} else {
  fail(`unknown command ${JSON.stringify(command)}`);
}
