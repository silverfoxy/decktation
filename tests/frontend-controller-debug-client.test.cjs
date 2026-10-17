const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const ts = require('typescript');
const file = path.join(__dirname, '../src/controllerDebug.ts');
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return {promise, resolve}; };
const snapshot = (state, revision, extra = {}) => ({success: true, session: 'session-1', revision, state,
  remaining_ms: 30000, event_count: 0, device_count: 0, metadata: {}, report: null, ...extra});
function setup(overrides = {}) {
  assert.ok(fs.existsSync(file), 'controller capture needs a dedicated single-owner client state machine');
  const code = ts.transpileModule(fs.readFileSync(file, 'utf8'), {compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020}}).outputText;
  const timers = new Map(); let id = 0;
  const exports = {};
  vm.runInNewContext(code, {exports, setTimeout: (fn, ms) => {timers.set(++id, {fn, ms}); return id;}, clearTimeout: key => timers.delete(key)});
  const calls = [];
  const rpc = Object.fromEntries(['start', 'get', 'stop', 'resume', 'upload'].map(method => [method, async (...args) => {
    calls.push([method, ...args]);
    if (overrides[method]) return overrides[method](...args);
    return snapshot(method === 'stop' ? 'stopping' : 'starting', calls.length);
  }]));
  const client = new exports.ControllerDebugClient(rpc);
  return {client, calls, timers, async fire(ms) { for (const [key, timer] of [...timers]) if (timer.ms === ms) {timers.delete(key); await timer.fn();} }};
}

const liveInput = () => ({pressed: [{source: 'source_1', button: 'L4'}],
  last_event: {at_ms: 100, source: 'source_1', kind: 'key', code: 704, button: 'L4', pressed: true}});

test('recording accepts only bounded live fields without exposing an in-progress report', async () => {
  const h = setup({start: () => snapshot('recording', 1, {
    live_input: {...liveInput(), private_path: '/not-for-ui'}, report: {events: ['private']},
  })});
  await h.client.start();
  assert.deepEqual(JSON.parse(JSON.stringify(h.client.view.snapshot.live_input)), liveInput());
  assert.equal(h.client.view.snapshot.report, null);
  h.client.dispose();
});

test('malformed live status is discarded rather than rendering untrusted input or blocking capture', async () => {
  const cases = [null, [], {}, {pressed: [], last_event: {}},
    {...liveInput(), pressed: new Array(33).fill({source: 'source_1', button: 'L4'})},
    {...liveInput(), pressed: [{source: '/dev/input/event3', button: 'L4'}]},
    {...liveInput(), pressed: [{source: 'source_17', button: 'L4'}]},
    {...liveInput(), pressed: [{source: 'source_1', button: 'private arbitrary string'}]},
    ...[{at_ms: -1}, {at_ms: 30001}, {at_ms: Infinity}, {source: 'source_0'},
      {kind: 'source'}, {pressed: 1}, {code: 30}, {code: 768}, {code: 704.1},
      {button: 'x'.repeat(65)}, {button: undefined, code: undefined}]
      .map(patch => ({...liveInput(), last_event: {...liveInput().last_event, ...patch}}))];
  for (const live_input of cases) {
    const h = setup({start: () => snapshot('recording', 1, {live_input})});
    await h.client.start();
    assert.equal(h.client.view.snapshot.live_input, null, JSON.stringify(live_input));
    assert.equal(h.client.view.snapshot.state, 'recording');
    assert.equal(h.client.view.error, '');
    h.client.dispose();
  }
});

test('live input clears outside recording and when absent from a newer snapshot', async () => {
  for (const next of [snapshot('recording', 2), snapshot('stopping', 2, {live_input: liveInput()}),
    snapshot('failed', 2, {live_input: liveInput()}),
    snapshot('ready', 2, {report: {phase: 'complete'}, live_input: liveInput()})]) {
    const h = setup({start: () => snapshot('recording', 1, {live_input: liveInput()}), get: () => next});
    await h.client.start();
    assert.ok(h.client.view.snapshot.live_input);
    await h.fire(250);
    assert.equal(h.client.view.snapshot.live_input, null, next.state);
    h.client.dispose();
  }
});

test('a failed poll clears held input so disconnected data is not shown as currently pressed', async () => {
  const h = setup({start: () => snapshot('recording', 1, {live_input: liveInput()}),
    get: () => {throw new Error('Disconnected');}});
  await h.client.start();
  await h.fire(250);
  assert.equal(h.client.view.snapshot.live_input, null);
  assert.equal(h.client.view.error, 'Disconnected');
  h.client.dispose();
});

test('start is idempotent through acknowledgment and its repeated activation cannot issue Stop', async () => {
  const h = setup({get: () => snapshot('recording', 2)});
  await h.client.start();
  assert.equal(h.client.view.snapshot.state, 'starting');
  await h.client.start();
  assert.equal(h.calls.filter(x => x[0] === 'start').length, 1);
  await h.fire(250);
  assert.equal(h.client.view.snapshot.state, 'recording');
  assert.equal(h.client.view.snapshot.remaining_ms, 30000);
  await h.client.start();
  assert.equal(h.calls.filter(x => x[0] === 'stop').length, 0);
  h.client.dispose();
});

test('countdown comes from the backend and Stop remains stopping until a final report is acknowledged', async () => {
  let result = snapshot('recording', 2, {remaining_ms: 23000});
  const h = setup({get: () => result});
  await h.client.start();
  await h.fire(250);
  assert.equal(h.client.view.snapshot.remaining_ms, 23000);
  await h.client.stop();
  assert.equal(h.client.view.snapshot.state, 'stopping');
  assert.equal(h.client.view.snapshot.report, null);
  result = snapshot('ready', 4, {remaining_ms: 0, report: {phase: 'stopped', metadata: {os_id: 'steamos'}, devices: [], events: []}});
  await h.fire(250);
  assert.equal(h.client.view.snapshot.report.metadata.os_id, 'steamos');
  assert.equal(h.client.view.snapshot.state, 'ready');
  h.client.dispose();
});

test('a pre-stop poll and obsolete revisions cannot regress the session', async () => {
  const slow = deferred();
  const h = setup({get: () => slow.promise, stop: () => snapshot('stopping', 3)});
  await h.client.start();
  const polling = h.fire(250);
  await h.client.stop();
  slow.resolve(snapshot('recording', 2));
  await polling;
  assert.equal(h.client.view.snapshot.state, 'stopping');
  h.client.dispose();
});

test('resume is not a synthetic new capture and late resume cannot replace Start', async () => {
  const slow = deferred();
  const h = setup({resume: () => slow.promise});
  const resuming = h.client.connect();
  await h.client.start();
  slow.resolve(snapshot('ready', 50, {session: 'previous', report: {phase: 'complete'}}));
  await resuming;
  assert.equal(h.client.view.snapshot.session, 'session-1');
  assert.equal(h.client.view.snapshot.state, 'starting');
  h.client.dispose();
});

test('polls are sequential, terminal results stop polling, and unmount never sends Stop', async () => {
  const slow = deferred();
  const h = setup({get: () => slow.promise});
  await h.client.start();
  const polling = h.fire(250);
  assert.equal([...h.timers.values()].filter(x => x.ms === 250).length, 0);
  slow.resolve(snapshot('ready', 2, {remaining_ms: 0, report: {phase: 'complete'}}));
  await polling;
  assert.equal([...h.timers.values()].filter(x => x.ms === 250).length, 0);
  h.client.dispose();
  assert.equal(h.calls.some(x => x[0] === 'stop'), false);
});

test('timeouts expose a retryable transport error rather than inventing a terminal report', async () => {
  const h = setup({stop: () => new Promise(() => {})});
  await h.client.start();
  const stopping = h.client.stop();
  await h.fire(5000);
  await stopping;
  assert.match(h.client.view.error, /respond/);
  assert.equal(h.client.view.pending, null);
  assert.equal(h.client.view.snapshot.report, null);
  h.client.dispose();
});

test('malformed terminal report or a different session is not accepted', async () => {
  const h = setup({get: () => snapshot('ready', 2, {session: 'previous', report: {phase: 'complete'}})});
  await h.client.start();
  await h.fire(250);
  assert.equal(h.client.view.snapshot.state, 'starting');
  assert.equal(h.client.view.snapshot.report, null);
  assert.ok(h.client.view.error);
  h.client.dispose();
});

test('TypeScript client consumes real Python owner/listener IPC, not a hand-written RPC fixture', {timeout: 10000}, async () => {
  const {spawn} = require('node:child_process');
  const {createInterface} = require('node:readline');
  const child = spawn(process.env.DECKTATION_TEST_PYTHON || 'python3', [path.join(__dirname, 'controller_debug_bridge.py')], {stdio: ['pipe', 'pipe', 'pipe']});
  const pending = [];
  let failure = '';
  child.stderr.on('data', data => { failure += data; });
  const lines = createInterface({input: child.stdout});
  lines.on('line', line => { const waiter = pending.shift(); if (waiter) waiter.resolve(JSON.parse(line)); });
  child.on('error', error => { for (const waiter of pending.splice(0)) waiter.reject(error); });
  child.on('exit', code => { for (const waiter of pending.splice(0)) waiter.reject(new Error(`bridge exited ${code}: ${failure}`)); });
  const call = (method, ...args) => new Promise((resolve, reject) => {
    pending.push({resolve, reject});
    child.stdin.write(JSON.stringify({method, args}) + '\n');
  });
  const h = setup(Object.fromEntries(['start', 'get', 'stop', 'resume'].map(method => [method, (...args) => call(method, ...args)])));
  try {
    await h.client.connect();
    assert.equal(h.client.view.snapshot.state, 'idle');
    await h.client.start();
    assert.equal(h.client.view.snapshot.state, 'starting');
    await call('advance', 4); // slow ACK still grants a full thirty seconds
    await h.fire(250);
    assert.equal(h.client.view.snapshot.state, 'recording');
    assert.equal(h.client.view.snapshot.remaining_ms, 30000);
    await call('advance', 1);
    await call('input');
    await h.fire(250);
    assert.equal(h.client.view.snapshot.remaining_ms, 29000);
    assert.equal(h.client.view.snapshot.event_count, 1);
    await h.client.stop();
    assert.equal(h.client.view.snapshot.state, 'stopping');
    assert.equal(h.client.view.snapshot.report, null);
    await call('advance', 0.1);
    await h.fire(250);
    assert.equal(h.client.view.snapshot.state, 'ready');
    assert.equal(h.client.view.snapshot.report.events[0].code, 0x130);
    assert.equal(h.client.view.snapshot.report.metadata.os_id, 'fixture-os');
    assert.ok(!JSON.stringify(h.client.view.snapshot.report).includes('replayed-controller'));
  } finally { h.client.dispose(); child.stdin.end(); lines.close(); child.kill(); }
});
