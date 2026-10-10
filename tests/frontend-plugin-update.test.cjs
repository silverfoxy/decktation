const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const source = ts.transpileModule(fs.readFileSync('src/pluginUpdate.ts', 'utf8'), {
  compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020}
}).outputText;
const update = {artifact: 'file:///tmp/decktation-update-abc_123.zip', version: '0.3.19', hash: 'a'.repeat(64)};
function load(window) {
  const exports = {};
  vm.runInNewContext(source, {exports, window});
  return exports.requestPluginUpdate;
}
test('missing global, window and call fail gracefully', async () => {
  for (const window of [undefined, {}, {DeckyBackend: {}}, {DeckyBackend: {call: 2}}]) {
    const result = await load(window)(update);
    assert.equal(result.success, false);
    assert.match(result.error, /installer is not available/);
  }
});
test('exact route and arguments request UPDATE with verified local ZIP', async () => {
  const loader = {async call(...args) {
    assert.equal(this, loader);
    assert.deepEqual(args, ['utilities/install_plugin', update.artifact, 'Decktation', update.version, update.hash, 2]);
  }};
  assert.equal((await load({DeckyBackend: loader})(update)).success, true);
});
test('missing route, rejection and negative responses return a readable error', async () => {
  for (const call of [async () => {throw Error('route not found');}, async () => false, async () => ({success: false})]) {
    const result = await load({DeckyBackend: {call}})(update);
    assert.equal(result.success, false);
    assert.match(result.error, /Update manually/);
    assert.ok(!result.error.includes('route not found'));
  }
});
test('remote or unexpected local paths never reach Decky', async () => {
  for (const artifact of ['https://silverfoxy.github.io/decktation/releases/v0.3.19/Decktation.zip', 'file:///etc/test.zip', 'file:///tmp/decktation-update-../test.zip']) {
    let called = false;
    const result = await load({DeckyBackend: {call: async () => {called = true;}}})({...update, artifact});
    assert.equal(result.success, false);
    assert.equal(called, false);
  }
});
test('successful prompt leaves only the active Decktation panel to prevent stale UI', async () => {
  let closed = 0;
  const deckyState = {publicState: () => ({activePlugin: {name: 'Decktation'}}), closeActivePlugin() { assert.equal(this, deckyState); closed++; }};
  const window = {DeckyPluginLoader: {deckyState}, DeckyBackend: {call: async () => undefined}};
  assert.equal((await load(window)(update)).success, true);
  assert.equal(closed, 1);
  deckyState.publicState = () => ({activePlugin: {name: 'Another plugin'}});
  assert.equal((await load(window)(update)).success, true);
  assert.equal(closed, 1);
  deckyState.publicState = () => ({activePlugin: {name: 'Decktation'}});
  window.DeckyBackend.call = async () => false;
  assert.equal((await load(window)(update)).success, false);
  assert.equal(closed, 1);
});
test('missing or failing navigation never blocks the native update prompt', async () => {
  for (const deckyState of [{}, {publicState() {throw Error('unavailable');}}, {publicState: () => ({activePlugin: {name: 'Decktation'}}), closeActivePlugin() {throw Error('unavailable');}}]) {
    assert.equal((await load({DeckyPluginLoader: {deckyState}, DeckyBackend: {call: async () => undefined}})(update)).success, true);
  }
});
