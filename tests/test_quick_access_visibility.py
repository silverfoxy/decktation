"""Exercise the frontend's DOM visibility logic with representative Steam states."""
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).parents[1]


def test_actual_menu_visibility_ignores_hidden_sidebars_and_missing_navigation_tree():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is required for frontend DOM tests')
    available = subprocess.run([node, '-e', "require.resolve('typescript')"], cwd=ROOT, capture_output=True)
    if available.returncode:
        pytest.skip('Install frontend dependencies to run this test')
    script = r'''
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const code = ts.transpileModule(fs.readFileSync('src/quickAccessVisibility.ts', 'utf8'), {
  compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020},
}).outputText;
const context = {exports: {}};
vm.runInNewContext(code, context);
const read = context.exports.quickAccessVisibility;
function doc(options = {}) {
  const node = {
    isConnected: true, parentElement: null,
    getBoundingClientRect: () => options.rect || {width: 400, height: 800, left: 880, right: 1280, top: 0, bottom: 800},
  };
  const view = {innerWidth: 1280, innerHeight: 800,
    getComputedStyle: () => ({display: options.display || 'block', visibility: 'visible', opacity: options.opacity ?? '1'})};
  return {hidden: options.hidden || false, defaultView: view,
    getElementsByClassName: name => name === 'qam' && !options.missing ? [node] : []};
}
assert.equal(read([doc()], ['qam']), true);
assert.equal(read([doc({hidden: true})], ['qam']), false);
assert.equal(read([doc({display: 'none'})], ['qam']), false);
assert.equal(read([doc({opacity: '0'})], ['qam']), false);
assert.equal(read([doc({rect: {width: 400, height: 800, left: 1280, right: 1680, top: 0, bottom: 800}})], ['qam']), false);
assert.equal(read([doc({missing: true})], ['qam']), null);
assert.equal(read([doc({missing: true}), doc({hidden: true})], ['qam']), false);
// No navigation tree is necessary if the mounted panel's document has QAM markup.
assert.equal(read([doc()], ['qam']), true);
'''
    result = subprocess.run([node, '-e', script], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
