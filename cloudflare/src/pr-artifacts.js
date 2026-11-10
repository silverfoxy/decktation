// Only the trusted publisher's public catalog/metadata can authorize a download.
const PAGES = 'https://silverfoxy.github.io/decktation';
const API = 'https://api.github.com/repos/silverfoxy/decktation/actions/artifacts';
const NO_STORE = { 'Cache-Control': 'no-store' };
const unavailable = (status = 404) => new Response('PR build unavailable or expired', { status, headers: NO_STORE });

async function publicJson(path) {
  const response = await fetch(`${PAGES}${path}`, {
    redirect: 'manual', cf: { cacheTtl: 60, cacheEverything: true },
  });
  if (!response.ok) throw new Error('Metadata unavailable');
  return response.json();
}

export async function handlePrArtifact(request, env, url) {
  const match = /^\/pulls\/([1-9][0-9]*)\/([1-9][0-9]*)\/([1-9][0-9]*)\/Decktation\.zip$/.exec(url.pathname);
  if (!match || url.search) return unavailable();
  if (!env?.GITHUB_ARTIFACT_TOKEN || !env.PR_DOWNLOAD_LIMITER || !env.PR_API_LIMITER) return unavailable(503);
  // Rate limits precede both public metadata fetches and authenticated API calls.
  const { success } = await env.PR_DOWNLOAD_LIMITER.limit({ key: request.headers.get('CF-Connecting-IP') || 'unknown' });
  if (!success) return new Response('Too many downloads', { status: 429, headers: { ...NO_STORE, 'Retry-After': '60' } });
  try {
    const [, number, run, attempt] = match;
    const catalog = await publicJson('/store/testing/plugins.json');
    const canonical = `https://decktation.com${url.pathname}`;
    const version = catalog.flatMap(plugin => plugin.versions || []).find(item => item.artifact === canonical);
    if (!version) return unavailable();
    const metadata = await publicJson(`/pulls/${number}/${run}/${attempt}/metadata.json`);
    if (metadata.zip_url !== canonical || metadata.channel !== 'pull_request' ||
        String(metadata.number) !== number || String(metadata.run_id) !== run ||
        String(metadata.run_attempt) !== attempt || version.hash !== metadata.sha256 ||
        !/^[0-9a-f]{64}$/.test(metadata.sha256) ||
        !/^[0-9a-f]{40}$/.test(metadata.commit)) return unavailable();
    // Worker deploys first. Existing catalog-pinned Pages ZIPs remain usable
    // until the trusted publisher replaces them with Actions-backed metadata.
    if (!Object.hasOwn(metadata, 'artifact_id')) {
      return new Response(null, { status: 302, headers: { ...NO_STORE, Location: `${PAGES}${url.pathname}` } });
    }
    if (version.name !== metadata.version ||
        !Number.isSafeInteger(metadata.artifact_id) || metadata.artifact_id <= 0 ||
        !Number.isSafeInteger(metadata.size_in_bytes) || metadata.size_in_bytes <= 0 ||
        metadata.size_in_bytes > 512 * 1024 * 1024 ||
        !(Date.parse(metadata.expires_at) > Date.now())) return unavailable();

    // Short-lived signed URLs are cached internally, never the GitHub credential.
    const cache = globalThis.caches?.default;
    const cacheKey = new Request(`https://decktation.com/__pr-artifact/${metadata.artifact_id}/${metadata.sha256}`);
    const cached = cache && await cache.match(cacheKey);
    if (cached) return new Response(null, { status: 302, headers: { ...NO_STORE, Location: await cached.text() } });
    const apiBudget = await env.PR_API_LIMITER.limit({ key: 'github-artifact-api' });
    if (!apiBudget.success) return unavailable(503);
    const init = {
      headers: { Authorization: `Bearer ${env.GITHUB_ARTIFACT_TOKEN}`, Accept: 'application/vnd.github+json',
        'User-Agent': 'decktation-artifact-download', 'X-GitHub-Api-Version': '2022-11-28' },
      redirect: 'manual', cf: { cacheTtl: 0, cacheEverything: false },
    };
    const response = await fetch(`${API}/${metadata.artifact_id}`, init);
    if (response.status === 404 || response.status === 410) return unavailable(410);
    if (!response.ok) return unavailable(503);
    const artifact = await response.json();
    if (artifact.id !== metadata.artifact_id || artifact.name !== 'decktation.zip' || artifact.expired ||
        artifact.digest !== `sha256:${metadata.sha256}` || artifact.size_in_bytes !== metadata.size_in_bytes ||
        String(artifact.workflow_run?.id) !== run || artifact.workflow_run?.head_sha !== metadata.commit ||
        !(Date.parse(artifact.expires_at) > Date.now())) return unavailable(410);
    const download = await fetch(`${API}/${metadata.artifact_id}/zip`, init);
    if (download.status === 404 || download.status === 410) return unavailable(410);
    if (download.status !== 302) return unavailable(503);
    const target = new URL(download.headers.get('Location'));
    if (target.protocol !== 'https:' || target.username || target.password || target.port ||
        !/^[a-z0-9-]+\.(?:blob\.core\.windows\.net|actions\.githubusercontent\.com)$/.test(target.hostname)) return unavailable(502);
    if (cache) await cache.put(cacheKey, new Response(target.href, { headers: { 'Cache-Control': 'max-age=30' } }));
    // GitHub's signed blob serves the raw ZIP, HEAD and Range requests directly.
    // We never follow the redirect with Authorization or expose the PAT.
    return new Response(null, { status: 302, headers: { ...NO_STORE, Location: target.href } });
  } catch {
    return unavailable(502);
  }
}
