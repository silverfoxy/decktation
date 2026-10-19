import assert from "node:assert/strict";
import { readdirSync } from "node:fs";
import test from "node:test";
import worker from "../src/index.js";

const origin = "https://silverfoxy.github.io/decktation";
const request = (path, method = "GET") => new Request(`https://decktation.com${path}`, { method });

test("HTTP redirects to HTTPS before assets, downloads, or catalog preflight", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", () => { throw new Error("Unexpected origin fetch"); });
  for (const [host, path, method] of [
    ["decktation.com", "/?language=es", "GET"],
    ["www.decktation.com", "/es/", "HEAD"],
    ["decktation.com", "/latest.zip?download=1", "GET"],
    ["decktation.com", "/plugins.json", "OPTIONS"],
    ["decktation.com", "/plugins.json", "POST"],
  ]) {
    const response = await worker.fetch(new Request(`http://${host}${path}`, { method }));
    assert.equal(response.status, 308);
    assert.equal(response.headers.get("Location"), `https://${host}${path}`);
  }
  assert.equal(fetch.mock.callCount(), 0);
});

test("download index, branch pages and metadata use the Pages origin", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", async (url, init) => {
    assert.equal(init.redirect, "manual");
    return new Response("download page", { headers: { "Content-Type": "text/html" } });
  });
  for (const path of ["/downloads/", "/branches/master/", "/releases/v1.0/metadata.json?test=1"]) {
    const response = await worker.fetch(request(path));
    assert.equal(fetch.mock.calls.at(-1).arguments[0], `${origin}${path === "/downloads/" ? "/index.html" : path}`);
    assert.equal(response.headers.get("Content-Type"), "text/html");
    assert.equal(await response.text(), "download page");
  }
});

test("ZIP redirects preserve release/branch paths and queries without fetching bytes", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", () => { throw new Error("Unexpected fetch"); });
  for (const method of ["GET", "HEAD"]) {
    for (const path of ["/branches/feature%2Btest/decktation.zip?download=1", "//external.example/file.zip"]) {
      const response = await worker.fetch(request(path, method));
      assert.equal(response.status, 302);
      assert.equal(response.headers.get("Location"), `${origin}${path.replace("/decktation.zip", "/Decktation.zip")}`);
      assert.equal(response.headers.get("Cache-Control"), "no-store");
      assert.equal(await response.text(), "");
    }
  }
  assert.equal(fetch.mock.callCount(), 0);
});

test("HEAD reaches the origin as HEAD", async (t) => {
  t.mock.method(globalThis, "fetch", async (url, init) => {
    assert.equal(init.method, "HEAD");
    return new Response(null, { headers: { "Content-Length": "1234" } });
  });
  const response = await worker.fetch(request("/downloads/", "HEAD"));
  assert.equal(await response.text(), "");
  assert.equal(response.headers.get("Content-Length"), "1234");
});

test("Pages directory redirects remain on the public hostname", async (t) => {
  t.mock.method(globalThis, "fetch", async () => new Response(null, {
    status: 301, headers: { Location: `${origin}/branches/master/?test=1` },
  }));
  const response = await worker.fetch(request("/branches/master?test=1"));
  assert.equal(response.status, 301);
  assert.equal(response.headers.get("Location"), "https://decktation.com/branches/master/?test=1");
});

test("a misconfigured Pages custom domain cannot loop through the Worker", async (t) => {
  t.mock.method(globalThis, "fetch", async () => new Response(null, {
    status: 301, headers: { Location: "https://decktation.com/" },
  }));
  for (const path of ["/downloads/", "/plugins.json"]) {
    const response = await worker.fetch(request(path));
    assert.equal(response.status, 502);
  }
});

test("unknown pages preserve origin 404s and network failures become 502s", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", async () => new Response("missing", { status: 404 }));
  assert.equal((await worker.fetch(request("/missing"))).status, 404);
  fetch.mock.mockImplementation(async () => { throw new Error("offline"); });
  const response = await worker.fetch(request("/downloads/", "HEAD"));
  assert.equal(response.status, 502);
  assert.equal(await response.text(), "");
});

test("unsupported methods are rejected without reaching the origin", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", () => { throw new Error("Unexpected fetch"); });
  for (const path of ["/", "/latest.zip", "/plugins.json"]) {
    assert.equal((await worker.fetch(request(path, "POST"))).status, 405);
  }
  assert.equal(fetch.mock.callCount(), 0);
});

test("catalog aliases and legacy homebrew domains retain CORS", async (t) => {
  t.mock.method(globalThis, "fetch", async (url) => {
    assert.equal(url, `${origin}/store/plugins.json`);
    return new Response("[]");
  });
  for (const host of ["decktation.com", "homebrew.imsilverfoxy.com"]) {
    for (const path of ["/plugins.json", "/store/plugins.json"]) {
      const response = await worker.fetch(new Request(`https://${host}${path}`));
      assert.equal(response.status, 200);
      assert.equal(response.headers.get("Access-Control-Allow-Origin"), "*");
    }
  }
});

test("landing locales and assets are served from the Worker asset binding", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", () => { throw new Error("Unexpected origin fetch"); });
  const env = { ASSETS: { fetch: async (req) => new Response(new URL(req.url).pathname) } };
  for (const path of ["/", "/es/", "/styles.css?v=1", "/app.js", "/assets/decktation-logo.png", "/vendor/fontawesome/css/all.min.css", "/robots.txt", "/sitemap.xml"]) {
    const response = await worker.fetch(request(path), env);
    assert.equal(await response.text(), new URL(request(path).url).pathname);
  }
  assert.equal(fetch.mock.callCount(), 0);
});

test("every translated landing route uses assets for GET and HEAD", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", () => { throw new Error("Unexpected origin fetch"); });
  const locales = readdirSync(new URL("../../site/src/i18n/", import.meta.url))
    .filter(name => name.endsWith(".json")).map(name => name.slice(0, -5));
  const env = { ASSETS: { fetch: async (req) => new Response(null, {
    headers: { "X-Asset-Path": new URL(req.url).pathname },
  }) } };
  for (const locale of locales) {
    const paths = locale === "en" ? ["/", "/index.html"]
      : [`/${locale}`, `/${locale}/`, `/${locale}/index.html`];
    for (const path of paths) {
      for (const method of ["GET", "HEAD"]) {
        const response = await worker.fetch(request(`${path}?test=1`, method), env);
        assert.equal(response.status, 200);
        assert.equal(response.headers.get("X-Asset-Path"), path);
      }
    }
  }
  assert.equal(fetch.mock.callCount(), 0);
});

test("downloads directory canonicalizes its trailing slash and preserves queries", async () => {
  const response = await worker.fetch(request("/downloads?channel=test"));
  assert.equal(response.status, 308);
  assert.equal(response.headers.get("Location"), "https://decktation.com/downloads/?channel=test");
});


test("stable aliases and versioned ZIPs download from GitHub Releases", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", () => { throw new Error("Unexpected fetch"); });
  for (const method of ["GET", "HEAD"]) {
    for (const path of ["/latest.zip", "/Decktation.zip", "/decktation.zip",
      "/releases/latest/decktation.zip", "/releases/latest/Decktation.zip"]) {
      const response = await worker.fetch(request(`${path}?download=1`, method));
      assert.equal(response.status, 302);
      assert.equal(response.headers.get("Location"),
        "https://github.com/silverfoxy/decktation/releases/latest/download/decktation.zip?download=1");
    }
    for (const name of ["decktation.zip", "Decktation.zip"]) {
      const response = await worker.fetch(request(`/releases/v0.3.20/${name}`, method));
      assert.equal(response.headers.get("Location"),
        "https://github.com/silverfoxy/decktation/releases/download/v0.3.20/decktation.zip");
    }
  }
  assert.equal(fetch.mock.callCount(), 0);
});
