import assert from "node:assert/strict";
import test from "node:test";

import worker from "../src/index.js";

const assets = {
  fetch: () => new Response("static asset"),
};

test("OPTIONS permits Decky's custom header", async () => {
  const response = await worker.fetch(
    new Request("https://homebrew.imsilverfoxy.com/plugins.json", {
      method: "OPTIONS",
    }),
    { ASSETS: assets },
  );

  assert.equal(response.status, 204);
  assert.equal(response.headers.get("Access-Control-Allow-Origin"), "*");
  assert.equal(
    response.headers.get("Access-Control-Allow-Headers"),
    "X-Decky-Version",
  );
  assert.equal(
    response.headers.get("Access-Control-Allow-Methods"),
    "GET, OPTIONS",
  );
});

test("GET proxies the catalog and adds CORS headers", async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async (url, init) => {
    assert.equal(
      url,
      "https://silverfoxy.github.io/decktation/store/plugins.json",
    );
    assert.equal(init.headers.get("X-Decky-Version"), "3.0.0");

    return new Response('[{"name":"Decktation"}]', {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const response = await worker.fetch(
      new Request("https://homebrew.imsilverfoxy.com/plugins.json", {
        headers: { "X-Decky-Version": "3.0.0" },
      }),
      { ASSETS: assets },
    );

    assert.equal(response.status, 200);
    assert.equal(response.headers.get("Access-Control-Allow-Origin"), "*");
    assert.deepEqual(await response.json(), [{ name: "Decktation" }]);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("GET returns a CORS-enabled error if the upstream request fails", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    throw new Error("upstream unavailable");
  };

  try {
    const response = await worker.fetch(
      new Request("https://homebrew.imsilverfoxy.com/plugins.json"),
      { ASSETS: assets },
    );

    assert.equal(response.status, 502);
    assert.equal(response.headers.get("Access-Control-Allow-Origin"), "*");
    assert.deepEqual(await response.json(), {
      error: "Unable to fetch the Decktation plugin catalog",
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});
