const UPSTREAM_CATALOG =
  "https://silverfoxy.github.io/decktation/store/plugins.json";

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "X-Decky-Version",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
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

function handleOptions() {
  return new Response(null, {
    status: 204,
    headers: CORS_HEADERS,
  });
}

async function handleCatalog(request) {
  const headers = new Headers({ Accept: "application/json" });
  const deckyVersion = request.headers.get("X-Decky-Version");

  if (deckyVersion) {
    headers.set("X-Decky-Version", deckyVersion);
  }

  try {
    const upstream = await fetch(UPSTREAM_CATALOG, { headers });
    return withCors(upstream);
  } catch {
    return new Response(
      JSON.stringify({
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

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/plugins.json") {
      if (request.method === "OPTIONS") {
        return handleOptions();
      }

      if (request.method === "GET") {
        return handleCatalog(request);
      }

      return new Response("Method Not Allowed", {
        status: 405,
        headers: { ...CORS_HEADERS, Allow: "GET, OPTIONS" },
      });
    }

    return env.ASSETS.fetch(request);
  },
};
