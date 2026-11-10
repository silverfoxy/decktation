const { test } = require('node:test');
const assert = require('node:assert/strict');
const { deployPages } = require('../scripts/deploy-pages.cjs');

function fixture(states = ['deployment_in_progress', 'succeed']) {
  const calls = [], outputs = [];
  return {
    calls, outputs,
    args: {
      snapshot: 'b'.repeat(40), artifactId: '42',
      context: { repo: { owner: 'owner', repo: 'repo' }, runId: 123, sha: 'a'.repeat(40) },
      core: { getIDToken: async () => 'test-oidc', setOutput: (...value) => outputs.push(value) },
      wait: async () => {}, polls: 3,
      github: {
        rest: { actions: { listWorkflowRunArtifacts: async () => { throw new Error('Artifact discovery must not be used, including on reruns'); } } },
        request: async (route, options) => {
          calls.push({ route, options });
          if (route.startsWith('GET')) return { data: { status: states.shift() || 'deployment_in_progress' } };
          return { data: { id: 'b'.repeat(40), page_url: 'https://example.github.io/' } };
        },
      },
    },
  };
}

test('Pages uses the generated snapshot SHA and polls its deployment, not master', async () => {
  const { args, calls, outputs } = fixture();
  await deployPages(args);
  assert.equal(calls[0].options.pages_build_version, args.snapshot);
  assert.notEqual(calls[0].options.pages_build_version, args.context.sha);
  assert.equal(calls[0].options.artifact_id, 42);
  assert.equal(calls[0].options.oidc_token, 'test-oidc');
  assert.ok(calls.slice(1).every(call => call.options.deploymentId === args.snapshot));
  assert.deepEqual(outputs, [['page_url', 'https://example.github.io/']]);
});

test('Pages fails when the new snapshot fails rather than reporting prior success', async () => {
  const { args, outputs } = fixture(['deployment_failed']);
  await assert.rejects(deployPages(args), /deployment_failed/);
  assert.deepEqual(outputs, []);
});

test('Pages cancels a timed out snapshot', async () => {
  const { args, calls } = fixture([]);
  await assert.rejects(deployPages(args), /timed out/);
  assert.ok(calls.at(-1).route.endsWith('/cancel'));
});

test('Pages refuses missing artifact IDs or invalid snapshot commits', async () => {
  const { args, calls } = fixture();
  await assert.rejects(deployPages({ ...args, snapshot: 'not a commit' }), /Invalid/);
  await assert.rejects(deployPages({ ...args, artifactId: undefined }), /artifact ID/);
  assert.deepEqual(calls, []);
});


test('Pages rejects artifact IDs that cannot be represented exactly by the API', async () => {
  const { args, calls } = fixture();
  await assert.rejects(deployPages({ ...args, artifactId: '9007199254740993' }), /artifact ID/);
  assert.deepEqual(calls, []);
});
