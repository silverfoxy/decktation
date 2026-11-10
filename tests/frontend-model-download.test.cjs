const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
const source = fs.readFileSync('src/index.tsx', 'utf8');
const component = source.slice(source.indexOf('type ModelDownload ='), source.indexOf('const setOverlayLabel'));
const exportsObject = {};
vm.runInNewContext(ts.transpileModule(component + '\nexport {ModelDownloadProgress};', {
  compilerOptions: {module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.React},
}).outputText, {exports: exportsObject, React, t: (key, values = {}) => key.replace(/\{(\w+)\}/g, (_, name) => values[name])});
const render = progress => renderToStaticMarkup(React.createElement(exportsObject.ModelDownloadProgress, {progress}));

test('known download size renders a real percentage and byte count', () => {
  const html = render({received: 5 * 1048576, total: 10 * 1048576, seconds_since_data: 0});
  assert.match(html, /50% · 5.0 \/ 10.0 MiB/);
  assert.match(html, /<progress[^>]*max="10485760"[^>]*value="5242880"/);
  assert.match(html, /Receiving download data/);
});
test('unknown size remains indeterminate while reporting downloaded bytes', () => {
  const html = render({received: 1048576, total: null, seconds_since_data: 0});
  assert.match(html, /1.0 MiB/);
  assert.doesNotMatch(html, /<progress[^>]*value=/);
  assert.doesNotMatch(html, /[0-9]% ·/);
});
test('stalled transfers and initial connection have distinct statuses', () => {
  assert.match(render({received: 100, total: 1000, seconds_since_data: 15}), /No download data received for 15 seconds/);
  assert.match(render(null), /Waiting for download data/);
});
