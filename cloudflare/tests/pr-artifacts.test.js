import assert from 'node:assert/strict';
import test from 'node:test';
import worker from '../src/index.js';

function fixture(t, { editMetadata = () => {}, editArtifact = () => {}, listed = true, location = 'https://productionresultssa18.blob.core.windows.net/download?signature=test', apiStatus = 200 } = {}) {
  const path = '/pulls/104/123/2/Decktation.zip';
  const metadata = { channel: 'pull_request', number: 104, run_id: 123, run_attempt: 2,
    artifact_id: 987, commit: 'a'.repeat(40), sha256: 'b'.repeat(64), version: '0.3.22-dev.pr-104.aaaaaaa',
    size_in_bytes: 100, expires_at: '2099-01-01T00:00:00Z', zip_url: `https://decktation.com${path}` };
  editMetadata(metadata);
  const artifact = { id: 987, name: 'decktation.zip', digest: `sha256:${'b'.repeat(64)}`, size_in_bytes: 100,
    expires_at: '2099-01-01T00:00:00Z', expired: false, workflow_run: { id: 123, head_sha: 'a'.repeat(40) } };
  editArtifact(artifact);
  const calls = [];
  t.mock.method(globalThis, 'fetch', async (url, init) => {
    calls.push({ url, init });
    assert.equal(init.redirect, 'manual');
    if (url.startsWith('https://silverfoxy.github.io/')) {
      assert.equal(init.headers, undefined);
      if (url.endsWith('/plugins.json')) return Response.json([{ versions: listed ? [{ artifact: metadata.zip_url, hash: 'b'.repeat(64), name: metadata.version }] : [] }]);
      return Response.json(metadata);
    }
    assert.ok(url.startsWith('https://api.github.com/repos/silverfoxy/decktation/actions/artifacts/987'));
    assert.equal(init.headers.Authorization, 'Bearer secret-test-token');
    if (url.endsWith('/zip')) return new Response(null, { status: 302, headers: { Location: location } });
    return Response.json(artifact, { status: apiStatus });
  });
  const env = { GITHUB_ARTIFACT_TOKEN: 'secret-test-token',
    PR_DOWNLOAD_LIMITER: { limit: async () => ({ success: true }) },
    PR_API_LIMITER: { limit: async () => ({ success: true }) } };
  const request = (method = 'GET', suffix = '') => new Request(`https://decktation.com${path}${suffix}`, { method });
  return { env, request, calls };
}

test('verified raw ZIP redirects GET and HEAD without forwarding token to blob', async t => {
  const f = fixture(t);
  for (const method of ['GET', 'HEAD']) {
    const response = await worker.fetch(f.request(method), f.env);
    assert.equal(response.status, 302);
    assert.ok(response.headers.get('Location').startsWith('https://productionresultssa18.blob.core.windows.net/'));
    assert.equal(response.headers.get('Cache-Control'), 'no-store');
    assert.equal(await response.text(), '');
  }
  assert.equal(f.calls.length, 8);
});

test('unlisted, expired, or tampered builds cannot use GitHub credential', async t => {
  for (const options of [
    { listed: false },
    { editMetadata: m => { m.expires_at = '2000-01-01T00:00:00Z'; } },
    { editMetadata: m => { m.sha256 = 'c'.repeat(64); } },
    { editMetadata: m => { m.run_attempt = 1; } },
  ]) await t.test(JSON.stringify(options), async t => {
    const f = fixture(t, options);
    assert.equal((await worker.fetch(f.request(), f.env)).status, 404);
    assert.equal(f.calls.length, options.listed === false ? 1 : 2);
  });
});

test('GitHub artifact identity, digest and expiry are checked before download', async t => {
  for (const editArtifact of [a => { a.digest = 'wrong'; }, a => { a.workflow_run.id = 999; },
    a => { a.name = 'other.zip'; }, a => { a.expired = true; }, a => { a.workflow_run.head_sha = 'c'.repeat(40); }]) {
    await t.test(String(editArtifact), async t => {
      const f = fixture(t, { editArtifact });
      assert.equal((await worker.fetch(f.request(), f.env)).status, 410);
      assert.equal(f.calls.length, 3);
    });
  }
});

test('invalid routes, methods, missing secrets and rate limits fail before network', async t => {
  const f = fixture(t);
  assert.equal((await worker.fetch(f.request('POST'), f.env)).status, 405);
  assert.equal((await worker.fetch(f.request('GET', '?artifact_id=555'), f.env)).status, 404);
  assert.equal((await worker.fetch(f.request(), {})).status, 503);
  f.env.PR_DOWNLOAD_LIMITER.limit = async () => ({ success: false });
  assert.equal((await worker.fetch(f.request(), f.env)).status, 429);
  assert.equal(f.calls.length, 0);
});

test('API rate limit prevents authenticated calls and unsafe redirect origins are rejected', async t => {
  await t.test('API limit', async t => {
    const f = fixture(t);
    f.env.PR_API_LIMITER.limit = async () => ({ success: false });
    assert.equal((await worker.fetch(f.request(), f.env)).status, 503);
    assert.equal(f.calls.length, 2);
  });
  for (const location of ['https://evil.example/download', 'http://a.blob.core.windows.net/zip',
    'https://a.blob.core.windows.net.evil.example/zip', 'https://user:password@a.blob.core.windows.net/zip']) {
    await t.test(location, async t => {
      const f = fixture(t, { location });
      assert.equal((await worker.fetch(f.request(), f.env)).status, 502);
      assert.equal(f.calls.length, 4);
    });
  }
});

test('signed URL cache avoids repeated API calls while rechecking public authorization', async t => {
  const f = fixture(t);
  const entries = new Map();
  const original = globalThis.caches;
  t.after(() => { if (original === undefined) delete globalThis.caches; else globalThis.caches = original; });
  globalThis.caches = { default: {
    match: async key => entries.get(key.url)?.clone(),
    put: async (key, response) => { entries.set(key.url, response); },
  } };
  assert.equal((await worker.fetch(f.request(), f.env)).status, 302);
  assert.equal((await worker.fetch(f.request(), f.env)).status, 302);
  assert.equal(f.calls.length, 6);
});


test('existing catalog-pinned Pages PR builds keep working during Worker-first rollout', async t => {
  const f = fixture(t, { editMetadata: metadata => {
    for (const name of ['artifact_id', 'expires_at', 'version', 'size_in_bytes']) delete metadata[name];
  } });
  const response = await worker.fetch(f.request(), f.env);
  assert.equal(response.status, 302);
  assert.equal(response.headers.get('Location'), 'https://silverfoxy.github.io/decktation/pulls/104/123/2/Decktation.zip');
  assert.equal(f.calls.length, 2);
});
