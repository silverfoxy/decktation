const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../src/index.tsx'), 'utf8');
const client = fs.readFileSync(path.join(__dirname, '../src/controllerDebug.ts'), 'utf8');

test('all lifecycle RPCs use the dedicated session client and upload requires explicit action', () => {
  for (const rpc of ['start_controller_debug', 'get_controller_debug', 'stop_controller_debug', 'upload_controller_debug', 'resume_controller_debug']) {
    assert.ok(source.includes(`"${rpc}"`), rpc);
  }
  assert.ok(source.includes('new ControllerDebugClient'));
  assert.ok(source.includes('onClick={() => controllerClient.upload()}'));
  assert.ok(client.includes('this.rpc.upload(snapshot.session!, true)'));
});

test('frontend never manufactures a capture deadline or completion from a report phase', () => {
  assert.ok(!source.includes('controllerDeadline'));
  assert.ok(!client.includes('Date.now()'));
  assert.ok(source.includes('controllerSnapshot.remaining_ms'));
  assert.ok(source.includes('controllerSnapshot.state === "ready"'));
});

test('preview explains its metadata coverage and submission is not represented as delivery', () => {
  for (const label of ['Events captured', 'Host metadata available', 'Full sanitized report', 'Report submitted. Event ID']) {
    assert.ok(source.includes(label));
  }
  assert.ok(!source.includes('delivery not confirmed'));
  assert.ok(!source.includes('Report queued'));
});
