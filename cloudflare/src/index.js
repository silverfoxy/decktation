// Keep GitHub Pages on its github.io hostname: assigning the Worker domain to
// Pages would redirect the origin back to this Worker.
const UPSTREAM_BASE = "https://silverfoxy.github.io/decktation";
const UPSTREAM_CATALOG = `${UPSTREAM_BASE}/store/plugins.json`;

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "X-Decky-Version",
  "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
  "Access-Control-Max-Age": "86400",
};

function withCors(response) {
  const headers = new Headers(response.headers);
  for (const [name, value] of Object.entries(CORS_HEADERS)) {
    headers.set(name, value);
  }
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

async function handleCatalog(request) {
  const headers = new Headers({ Accept: "application/json" });
  const deckyVersion = request.headers.get("X-Decky-Version");
  if (deckyVersion) headers.set("X-Decky-Version", deckyVersion);

  try {
    const upstream = await fetch(UPSTREAM_CATALOG, {
      method: request.method,
      headers,
      redirect: "manual",
    });
    if (upstream.status >= 300 && upstream.status < 400) {
      throw new Error("Unexpected catalog redirect");
    }
    return withCors(upstream);
  } catch {
    return new Response(
      request.method === "HEAD" ? null : JSON.stringify({
        error: "Unable to fetch the Decktation plugin catalog",
      }),
      {
        status: 502,
        headers: {
          ...CORS_HEADERS,
          "Content-Type": "application/json; charset=utf-8",
        },
      },
    );
  }
}

async function handleSite(request, url) {
  const upstreamPath = url.pathname === "/downloads/" || url.pathname === "/downloads/index.html"
    ? "/index.html" : url.pathname;
  const upstreamUrl = `${UPSTREAM_BASE}${upstreamPath}${url.search}`;

  // ZIPs exceed Workers' static-asset file size limit. Let the artifact origin
  // serve downloads directly, including Range requests and HEAD probes.
  if (url.pathname.endsWith(".zip")) {
    return new Response(null, {
      status: 302,
      headers: { Location: upstreamUrl, "Cache-Control": "no-store" },
    });
  }

  try {
    const upstream = await fetch(upstreamUrl, {
      method: request.method,
      redirect: "manual",
    });
    if (upstream.status >= 300 && upstream.status < 400) {
      const location = upstream.headers.get("Location");
      const target = location && new URL(location, upstreamUrl);
      // Preserve Pages' trailing-slash redirects under the public hostname,
      // while refusing redirects to a custom domain (which could cause a loop).
      if (!target || !target.href.startsWith(`${UPSTREAM_BASE}/`)) {
        throw new Error("Unexpected site redirect");
      }
      return new Response(null, {
        status: upstream.status,
        headers: {
          Location: `${url.origin}${target.href.slice(UPSTREAM_BASE.length)}`,
        },
      });
    }
    return upstream;
  } catch {
    return new Response(request.method === "HEAD" ? null : "Unable to fetch Decktation downloads", {
      status: 502,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.protocol === "http:") {
      url.protocol = "https:";
      return Response.redirect(url.href, 308);
    }
    const isCatalog = url.pathname === "/plugins.json" || url.pathname === "/store/plugins.json";

    if (isCatalog && request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method Not Allowed", {
        status: 405,
        headers: isCatalog
          ? { ...CORS_HEADERS, Allow: "GET, HEAD, OPTIONS" }
          : { Allow: "GET, HEAD" },
      });
    }
    if (isCatalog) return handleCatalog(request);
    if (url.pathname === "/downloads") {
      return new Response(null, {
        status: 308,
        headers: { Location: `${url.origin}/downloads/${url.search}` },
      });
    }
    if (["/", "/index.html", "/es", "/es/", "/es/index.html", "/styles.css", "/app.js", "/robots.txt", "/sitemap.xml"].includes(url.pathname)
      || url.pathname.startsWith("/_astro/") || url.pathname.startsWith("/assets/") || url.pathname.startsWith("/vendor/")) {
      return env.ASSETS.fetch(request);
    }
    return handleSite(request, url);
  },
};
