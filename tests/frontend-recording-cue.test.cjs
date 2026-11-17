const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const source = fs.readFileSync(path.join(__dirname, '../src/index.tsx'), 'utf8');

test('recording cue only offers overlay or none, including old toast configs', () => {
  assert.match(source, /rgOptions=\{\[\{data:"overlay",label:t\("Overlay"\)\},\{data:"none",label:t\("None"\)\}\]\}/);
  assert.match(source, /config\.recordingIndicator === "none" \|\| \(config\.recordingIndicator == null && config\.showNotifications === false\) \? "none" : "overlay"/);
  assert.match(source, /recordingIndicator: string = "overlay"/);
  assert.match(source, /useState<string>\("overlay"\)/);
  assert.doesNotMatch(source, /recordingIndicator: string = "toast"/);
  assert.doesNotMatch(source, /useState<string>\("toast"\)/);
  assert.doesNotMatch(source, /logic\.recordingIndicator === "toast"/);
});