const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const React = require('react');
const {create, act} = require('react-test-renderer');

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const text = node => typeof node === 'string' || typeof node === 'number' ? String(node)
  : Array.isArray(node) ? node.map(text).join('') : node ? text(node.props?.children ?? node.children) : '';
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return {promise, resolve}; };

async function mount(rpc) {
  let now = 100000;
  let id = 0;
  const intervals = new Map();
  const timeouts = new Map();
  const decky = Object.fromEntries(['PanelSection', 'PanelSectionRow', 'ButtonItem', 'Focusable', 'ToggleField', 'DropdownItem'].map(name => [name, name]));
  Object.assign(decky, {definePlugin: fn => fn, getGamepadNavigationTrees: () => [], quickAccessMenuClasses: {},
    gamepadContextMenuClasses: {}, GamepadButton: {}, Router: {}});
  const fakeDate = class extends Date { static now() { return now; } };
  const source = fs.readFileSync(process.env.DECKTATION_PANEL_SOURCE || path.join(__dirname, '../src/index.tsx'), 'utf8');
  const output = ts.transpileModule(source + '\nexport {DecktationPanel};', {
    compilerOptions: {module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.React, esModuleInterop: true, target: ts.ScriptTarget.ES2020},
  }).outputText;
  const context = {exports: {}, console, Date: fakeDate,
    setInterval: (fn, ms) => { intervals.set(++id, {fn, ms}); return id; }, clearInterval: n => intervals.delete(n),
    setTimeout: (fn, ms) => { timeouts.set(++id, {fn, ms}); return id; }, clearTimeout: n => timeouts.delete(n),
    requestAnimationFrame: () => ++id, cancelAnimationFrame: () => {},
    require: name => {
      if (name === 'react') return React;
      if (name === './controllerDebug') {
        const exports = {};
        const clientSource = fs.readFileSync(path.join(__dirname, '../src/controllerDebug.ts'), 'utf8');
        const clientCode = ts.transpileModule(clientSource, {compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020}}).outputText;
        vm.runInNewContext(clientCode, {...context, exports});
        return exports;
      }
      if (name === 'react-icons/fa') return {FaMicrophone: 'FaMicrophone', FaArrowCircleUp: 'FaArrowCircleUp'};
      if (name === 'decky-frontend-lib') return decky;
      if (name === '@decky/api') return {callable: method => async (...args) => rpc[method]
        ? rpc[method](...args) : {success: false}, toaster: {}};
      if (name === './i18n') return {t: key => key, languageName: (_, fallback) => fallback,
        getInterfacePreference: () => 'auto', initializeSteamLanguage: async () => {}, INTERFACE_LANGUAGE_OPTIONS: []};
      if (name === './quickAccessVisibility') return {quickAccessVisibility: () => null};
      if (name === '../package.json') return {version: 'test'};
      return {};
    }};
  vm.runInNewContext(output, context);
  let renderer;
  await act(async () => { renderer = create(React.createElement(context.exports.DecktationPanel, {logic: {enabled: false, recording: false}})); });
  const button = label => renderer.root.findAllByType('ButtonItem').find(node => text(node).includes(label));
  const click = async label => { const node = button(label); assert.ok(node, `missing button: ${label}`); assert.ok(!node.props.disabled); await act(async () => { await node.props.onClick(); }); };
  if (button('Advanced settings')) { await click('Advanced settings'); await click('Diagnostics'); }
  return {button, click, renderer, timeouts,
    async tick(ms) { now += ms; await act(async () => { for (const timer of [...intervals.values()]) if (timer.ms === ms) await timer.fn(); }); },
    async beginTick(ms) { now += ms; let tasks; await act(async () => { tasks = [...intervals.values()].filter(timer => timer.ms === ms).map(timer => timer.fn()); await Promise.resolve(); }); return tasks; },
    async fireTimeout(ms) { await act(async () => { for (const [key, timer] of [...timeouts]) if (timer.ms === ms) { timeouts.delete(key); await timer.fn(); } }); },
    async dispose() { await act(async () => renderer.unmount()); },
  };
}

const state = (value, revision, extra = {}) => ({success: true, session: 'one', revision, state: value,
  remaining_ms: value === 'recording' ? 30000 : 0, event_count: 0, device_count: 0,
  metadata: {os_id: 'steamos'}, report: null, ...extra});
const idle = {success: true, session: null, revision: 0, state: 'idle', remaining_ms: 0,
  event_count: 0, device_count: 0, metadata: {}, report: null};

test('per-report Send is above the log preview and submission displays its event ID without claiming delivery', async () => {
  const uploads = [];
  const ready = state('ready', 4, {event_count: 8, device_count: 2, report: {phase: 'complete', events: []}});
  const h = await mount({resume_controller_debug: async () => ready,
    upload_controller_debug: async (...args) => {uploads.push(args); return {...ready, revision: 5, event_id: 'a'.repeat(32)};}});
  try {
    assert.equal(uploads.length, 0, 'review never implies consent');
    const copy = text(h.renderer.toJSON());
    assert.ok(copy.indexOf('Send this report to Sentry') < copy.indexOf('Full sanitized report'), 'send must precede preview');
    assert.match(copy, /Events captured: 8.*Controller interfaces: 2/);
    assert.ok(!copy.includes('delivery not confirmed'));
    await h.click('Send this report to Sentry');
    assert.deepEqual(uploads, [['one', true]], 'explicit consent belongs to this frozen report');
    const sent = text(h.renderer.toJSON());
    assert.match(sent, /Report submitted\. Event ID: a{32}/);
    assert.ok(!/queued|delivery not confirmed|delivered/i.test(sent));
    assert.equal(h.button('Send this report to Sentry'), undefined, 'no duplicate send');
  } finally {await h.dispose();}
});

test('debugger instructions stay compact while retaining explicit report privacy and consent', async () => {
  const h = await mount({resume_controller_debug: async () => idle,
    start_controller_debug: async () => state('recording', 1)});
  try {
    const section = h.renderer.root.findAllByType('PanelSection').find(node => node.props.title === 'Controller input debugger');
    const copy = text(section);
    assert.match(copy, /Record up to 30 seconds of controller input\./);
    assert.match(copy, /Press each paddle, then A\. Do not type\./);
    assert.match(copy, /Includes host\/build details, controller interfaces and button transitions\./);
    assert.match(copy, /Excludes typing, audio, transcripts, serials and input paths\./);
    assert.match(copy, /Nothing is sent automatically\. Send shares only this report with Sentry\./);
    assert.ok(copy.split(/\s+/).length < 100, copy);
    assert.ok(!copy.includes('250 ms'));
    assert.ok(!copy.includes('delivery not confirmed'));
    await h.click('Start 30-second capture');
    const active = text(h.renderer.toJSON());
    assert.match(active, /Controller navigation is paused\. Steam\/Quick Access may open menus\./);
    assert.match(active, /Ends after 30 seconds; touch or mouse can stop early\./);
    assert.ok(active.split(/\s+/).length < 85, active);
  } finally {await h.dispose();}
});

test('recording shows held buttons with their source without duplicate timestamp prose or the in-progress report', async () => {
  let result = state('recording', 2, {event_count: 7, device_count: 3, report: {secret: 'unfinished report'},
    live_input: {pressed: [{source: 'source_2', button: 'L4'}, {source: 'source_3', button: 'A'}],
      last_event: {source: 'source_2', kind: 'hid', button: 'L4', pressed: true, at_ms: 200}}});
  const h = await mount({resume_controller_debug: async () => idle,
    start_controller_debug: async () => state('starting', 1), get_controller_debug: async () => result});
  try {
    await h.click('Start 30-second capture');
    await h.fireTimeout(250);
    const rendered = text(h.renderer.toJSON());
    assert.match(rendered, /Held buttons/);
    assert.match(rendered, /L4.*Source: source_2/);
    assert.match(rendered, /A.*Source: source_3/);
    assert.ok(!rendered.includes('Last transition:'), 'timestamps must not reflow the live card');
    assert.match(rendered, /Events captured: 7.*Controller interfaces: 3/);
    assert.ok(!rendered.includes('unfinished report'));
    result = state('recording', 3, {live_input: {pressed: [],
      last_event: {source: 'source_2', kind: 'key', code: 704, pressed: false, at_ms: 250}}});
    await h.fireTimeout(250);
    assert.match(text(h.renderer.toJSON()), /No buttons held/);
    assert.ok(!text(h.renderer.toJSON()).includes('source_2'), 'released input must clear its stale source');
    assert.ok(!text(h.renderer.toJSON()).includes('source_3'));
    result = state('recording', 4);
    await h.fireTimeout(250);
    assert.match(text(h.renderer.toJSON()), /Live input unavailable/);
    assert.ok(!text(h.renderer.toJSON()).includes('Last transition:'));
  } finally {await h.dispose();}
});

// These tests exercise the mounted screen with real client state, not string-presence checks.
test('capture uses an isolated focus trap and swallows controller navigation without stopping', async () => {
  let stops = 0;
  const h = await mount({resume_controller_debug: async () => idle,
    start_controller_debug: async () => state('starting', 1),
    get_controller_debug: async () => state('recording', 2),
    stop_controller_debug: async () => {stops++; return state('stopping', 3);},
  });
  try {
    await h.click('Start 30-second capture');
    assert.match(text(h.renderer.toJSON()), /Starting controller capture/);
    const focus = h.renderer.root.findByType('Focusable');
    for (const handler of ['onButtonDown', 'onButtonUp', 'onOKButton', 'onCancelButton', 'onGamepadDirection', 'onActivate', 'onCancel']) {
      let prevented = false; let stopped = false;
      assert.equal(typeof focus.props[handler], 'function', handler);
      focus.props[handler]({preventDefault() {prevented = true;}, stopPropagation() {stopped = true;}});
      assert.ok(prevented && stopped, handler);
    }
    assert.equal(h.renderer.root.findAllByType('ButtonItem').length, 0, 'no gamepad-activatable controls during capture');
    await h.fireTimeout(250);
    assert.match(text(h.renderer.toJSON()), /30 seconds remaining/);
    const recordingFocus = h.renderer.root.findByType('Focusable');
    recordingFocus.props.onOKButton({preventDefault() {}, stopPropagation() {}});
    recordingFocus.props.onCancelButton({preventDefault() {}, stopPropagation() {}});
    assert.equal(stops, 0, 'the original Start release, A, and B cannot invoke Stop');
    const touchStop = h.renderer.root.findByType('button');
    assert.equal(touchStop.props.tabIndex, -1);
  } finally { await h.dispose(); }
});

test('touch Stop waits for the final snapshot then restores report review and normal navigation', async () => {
  let result = state('recording', 2, {remaining_ms: 27000});
  const h = await mount({resume_controller_debug: async () => idle,
    start_controller_debug: async () => state('starting', 1),
    get_controller_debug: async () => result,
    stop_controller_debug: async () => state('stopping', 3),
  });
  try {
    await h.click('Start 30-second capture');
    await h.fireTimeout(250);
    assert.match(text(h.renderer.toJSON()), /27 seconds remaining/);
    await act(async () => { await h.renderer.root.findByType('button').props.onClick(); });
    assert.match(text(h.renderer.toJSON()), /Finalizing controller report/);
    assert.ok(h.renderer.root.findByType('button').props.disabled);
    result = state('ready', 4, {report: {phase: 'stopped', metadata: {os_id: 'steamos'}, devices: [], events: []}});
    await h.fireTimeout(250);
    assert.ok(h.button('Send this report to Sentry'));
    assert.match(text(h.renderer.toJSON()), /steamos/);
    assert.equal(h.renderer.root.findByType('Focusable').props.onButtonDown, undefined);
  } finally { await h.dispose(); }
});

test('a thirty-second terminal snapshot ends capture without a button press', async () => {
  const h = await mount({resume_controller_debug: async () => idle,
    start_controller_debug: async () => state('recording', 1),
    get_controller_debug: async () => state('ready', 2, {report: {phase: 'complete', metadata: {}, devices: [], events: []}}),
  });
  try {
    await h.click('Start 30-second capture');
    await h.fireTimeout(250);
    assert.ok(h.button('Send this report to Sentry'));
  } finally { await h.dispose(); }
});

test('listener failure releases the focus trap with an error and allows a new capture', async () => {
  const h = await mount({resume_controller_debug: async () => idle,
    start_controller_debug: async () => state('starting', 1),
    get_controller_debug: async () => state('failed', 2, {error: 'Controller listener unavailable.'}),
  });
  try {
    await h.click('Start 30-second capture');
    await h.fireTimeout(250);
    assert.match(text(h.renderer.toJSON()), /Controller listener unavailable/);
    assert.ok(h.button('Start 30-second capture'));
    assert.ok(!h.button('Send this report to Sentry'));
  } finally { await h.dispose(); }
});

test('reopening restores actual active state and unmount does not cancel the capture', async () => {
  let stops = 0;
  // Resume is active before navigation, so mount's navigation path must tolerate the dedicated screen.
  const h = await mount({resume_controller_debug: async () => state('recording', 5, {remaining_ms: 17000}),
    stop_controller_debug: async () => {stops++; return state('stopping', 6);},
  });
  try { assert.match(text(h.renderer.toJSON()), /17 seconds remaining/); }
  finally { await h.dispose(); }
  assert.equal(stops, 0);
});

test('ready Back dismisses only that session, leaves normal navigation usable and can reopen its report', async () => {
  const ready = state('ready', 4, {report: {phase: 'complete', events: []}});
  const h = await mount({resume_controller_debug: async () => ready});
  try {
    assert.ok(h.button('Send this report to Sentry'));
    assert.equal(h.button('Start 30-second capture'), undefined, 'completion is not buried in Diagnostics');
    const focus = h.renderer.root.findByType('Focusable');
    assert.equal(focus.props.onButtonDown, undefined);
    assert.equal(focus.props.onOKButton, undefined);
    await act(async () => focus.props.onCancel({stopPropagation() {}}));
    assert.ok(h.button('Start 30-second capture'));
    assert.equal(h.renderer.root.findAllByType('pre').length, 0);
    await h.click('Controller report ready for review');
    assert.ok(h.button('Send this report to Sentry'));
    await h.click('Back');
    assert.ok(h.button('Start 30-second capture'));
    await h.click('Back');
    assert.ok(h.button('Diagnostics'), 'normal Back still leaves Diagnostics');
  } finally {await h.dispose();}
});

test('capture reserves the same status and live regions during startup recording and finalization', async () => {
  let result = state('recording', 2, {live_input: {pressed: [{source: 'source_1', button: 'Right Trackpad'}], last_event: null}});
  const h = await mount({resume_controller_debug: async () => idle,
    start_controller_debug: async () => state('starting', 1), get_controller_debug: async () => result,
    stop_controller_debug: async () => state('stopping', 3)});
  try {
    await h.click('Start 30-second capture');
    const regions = () => h.renderer.root.findAll(node => node.props.role === 'status').map(node => ({height: node.props.style?.height, overflowY: node.props.style?.overflowY}));
    const initial = regions();
    await h.fireTimeout(250);
    assert.deepEqual(regions(), initial);
    await act(async () => h.renderer.root.findByType('button').props.onClick());
    assert.deepEqual(regions(), initial);
    assert.ok(!text(h.renderer.toJSON()).includes('source_1'));
    assert.match(text(h.renderer.toJSON()), /Live input unavailable/);
  } finally {await h.dispose();}
});
