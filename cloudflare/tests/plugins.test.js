import assert from "node:assert/strict";
import test from "node:test";

import worker from "../src/index.js";

const assets = {
  fetch: () => new Response("static asset"),
};

test("OPTIONS permits Decky's custom header", async () => {
  const response = await worker.fetch(
    new Request("https://decktation.com/plugins.json", {
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
    "GET, HEAD, OPTIONS",
  );
});

test("GET and OPTIONS serve the opt-in test catalog without changing stable", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", async (url, init) => {
    assert.equal(url, "https://silverfoxy.github.io/decktation/store/testing/plugins.json");
    assert.equal(init.redirect, "manual");
    return new Response('[{"name":"Decktation","versions":[]}]', {
      headers: { "Content-Type": "application/json" },
    });
  });
  const url = "https://decktation.com/testing/plugins.json";
  const preflight = await worker.fetch(new Request(url, { method: "OPTIONS" }));
  assert.equal(preflight.status, 204);
  assert.equal(preflight.headers.get("Access-Control-Allow-Origin"), "*");
  const response = await worker.fetch(new Request(url));
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("Access-Control-Allow-Origin"), "*");
  assert.equal((await response.json())[0].name, "Decktation");
  assert.equal(fetch.mock.callCount(), 1);
  assert.equal((await worker.fetch(new Request(url, { method: "POST" }))).status, 405);
});

test("test catalog disables automatic branch updates but keeps manual versions", async () => {
  const response = await worker.fetch(new Request("https://decktation.com/testing/plugins.json/versions"));
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), {});
  assert.equal(response.headers.get("access-control-allow-origin"), "*");
  const preflight = await worker.fetch(new Request("https://decktation.com/testing/plugins.json/versions", { method: "OPTIONS" }));
  assert.equal(preflight.status, 204);
  assert.equal((await worker.fetch(new Request("https://decktation.com/testing/plugins.json/versions", { method: "POST" }))).status, 405);
});

test("GET proxies the catalog and adds CORS headers", async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async (url, init) => {
    assert.equal(
      url,
      "https://silverfoxy.github.io/decktation/store/plugins.json",
    );
    assert.equal(init.headers.get("X-Decky-Version"), "3.0.0");
    assert.equal(init.redirect, "manual");

    return new Response('[{"name":"Decktation"}]', {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const response = await worker.fetch(
      new Request("https://decktation.com/plugins.json", {
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
      new Request("https://decktation.com/plugins.json"),
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

test("legacy custom-store hostname still permits Decky preflight", async () => {
  const response = await worker.fetch(
    new Request("https://homebrew.imsilverfoxy.com/plugins.json", { method: "OPTIONS" }),
    { ASSETS: assets },
  );
  assert.equal(response.status, 204);
  assert.equal(response.headers.get("Access-Control-Allow-Headers"), "X-Decky-Version");
});
