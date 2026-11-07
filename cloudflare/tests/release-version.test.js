import assert from "node:assert/strict";
import { test } from "node:test";

import { nextDevelopmentVersion } from "../../scripts/release-version.mjs";

test("development versions identify the branch in Decky's test-store selector", () => {
  assert.equal(
    nextDevelopmentVersion("0.3.19", "abcdef0123456789", "feat/candidate"),
    "0.3.20-dev.feat-candidate.abcdef0",
  );
});

test("numeric branch names remain valid SemVer prerelease labels", () => {
  assert.equal(nextDevelopmentVersion("0.3.19", "abcdef0123456789", "007"),
    "0.3.20-dev.branch-007.abcdef0");
});

test("increments a stable version for a development build", () => {
  assert.equal(
    nextDevelopmentVersion("0.3.17", "9ea7c5d840c5602e"),
    "0.3.18-dev.9ea7c5d",
  );
});


test("increments a version with a prerelease suffix", () => {
  assert.equal(
    nextDevelopmentVersion("0.3.18-dev.overlay.1", "9ea7c5d840c5602e"),
    "0.3.19-dev.9ea7c5d",
  );
});


test("increments a version with build metadata", () => {
  assert.equal(
    nextDevelopmentVersion("1.2.3+build.9", "abcdef0123456789"),
    "1.2.4-dev.abcdef0",
  );
});
