import { test, expect } from './fixtures';
import type { Page } from '@playwright/test';

async function open(page: Page) {
  await page.goto('/');
  await page.getByRole('button', { name: 'Advanced settings', exact: true }).click();
  await page.getByRole('button', { name: 'Diagnostics', exact: true }).click();
}
async function start(page: Page) {
  await open(page);
  await page.getByRole('button', { name: 'Start 30-second capture', exact: true }).click();
  await expect(page.getByText('Recording controller input', { exact: true })).toBeVisible();
}

for (const [command, message] of [
  ['dead_listener', 'Controller listener stopped.'],
  ['pause', 'Controller listener heartbeat lost or restarted.'],
] as const) {
  test(`${command} is a bounded backend failure, not a ready report`, async ({ page, harness }) => {
    await start(page);
    await harness.control(command, { value: true });
    await expect(page.getByRole('alert').filter({ hasText: message })).toBeVisible({ timeout: 4000 });
    const result = await harness.control('inspect');
    expect(result.snapshot.state).toBe('failed');
    expect(result.snapshot.report).toBeNull();
    await expect(page.locator('pre')).toHaveCount(0);
  });
}

test('missing ACK fails within five seconds without producing a successful report', async ({ page, harness }) => {
  await harness.control('pause', { value: true });
  await open(page);
  await page.getByRole('button', { name: 'Start 30-second capture', exact: true }).click();
  await expect(page.getByText('Starting controller capture…', { exact: true })).toBeVisible();
  await expect(page.getByRole('alert').filter({ hasText: 'did not acknowledge capture' })).toBeVisible({ timeout: 6500 });
  expect((await harness.control('inspect')).snapshot.state).toBe('failed');
});

test('RPC timeout is bounded while producer continues and retry reconnects', async ({ page, harness }) => {
  await start(page);
  const session = (await harness.control('inspect')).snapshot.session;
  await harness.control('rpc_delay', { seconds: 6 });
  await expect(page.getByRole('alert').filter({ hasText: 'Controller debugger did not respond.' })).toBeVisible({ timeout: 6500 });
  const running = await harness.control('inspect');
  expect(running.snapshot.session).toBe(session);
  expect(running.snapshot.state).toBe('recording');
  expect(running.snapshot.report).toBeNull();
  await harness.control('rpc_delay', { seconds: 0 });
  await page.getByRole('button', { name: 'Retry controller status', exact: true }).click();
  await expect(page.getByText('Recording controller input', { exact: true })).toBeVisible();
});

for (const kind of ['stale', 'malformed']) {
  test(`${kind} listener IPC snapshot is ignored and cannot replace current session`, async ({ page, harness }) => {
    await start(page);
    // Capture a stable accepted producer snapshot, then stop only the replay
    // producer and corrupt its IPC file; never synthesize a successful RPC.
    const before = await harness.control('inspect');
    await harness.control('corrupt_snapshot', { kind });
    const polls = before.history.filter((v: any) => v.method === 'get_controller_debug').length;
    await expect.poll(async () => (await harness.control('inspect')).history.filter((v: any) => v.method === 'get_controller_debug').length,
      { intervals: [50, 100, 150], timeout: 1200 }).toBeGreaterThan(polls + 1);
    const after = await harness.control('inspect');
    expect(after.snapshot.session).toBe(before.snapshot.session);
    expect(after.snapshot.state).toBe('recording');
    expect(after.snapshot.event_count).toBe(before.snapshot.event_count);
    expect(after.snapshot.report).toBeNull();
    await expect(page.getByRole('alert')).toHaveCount(0);
    await harness.control('pause', { value: false });
    await page.getByRole('button', { name: 'Stop and review (touch or mouse)', exact: true }).click();
    await expect(page.getByText('Controller report ready for review', { exact: true })).toBeVisible();
  });
}

for (const kind of ['recording', 'transcribing']) {
  test(`busy ${kind} rejects capture with no microphone or text output`, async ({ page, harness }) => {
    await harness.control('busy', { kind });
    await open(page);
    await page.getByRole('button', { name: 'Start 30-second capture', exact: true }).click();
    await expect(page.getByRole('alert').filter({ hasText: 'Finish recording, transcription, or the pending draft' })).toBeVisible();
    const result = await harness.control('inspect');
    expect(result.snapshot.state).toBe('idle');
    expect(result.snapshot.session).toBeNull();
    expect(result.counts).toEqual({ microphone: 0, typing: 0, upload: 0 });
  });
}

test('explicit upload uses real backend per-report consent and only local telemetry', async ({ page, harness }) => {
  await start(page);
  const active = await harness.control('inspect');
  expect((await harness.rpc('upload_controller_debug', [active.snapshot.session, true])).success).toBe(false);
  await page.getByRole('button', { name: 'Stop and review (touch or mouse)', exact: true }).click();
  await expect(page.getByText('Controller report ready for review', { exact: true })).toBeVisible();
  const reviewed = JSON.parse(await page.locator('pre').innerText());
  expect((await harness.rpc('upload_controller_debug', [active.snapshot.session, false])).success).toBe(false);
  expect((await harness.control('inspect')).counts.upload).toBe(0);
  await page.getByRole('button', { name: 'Send this report to Sentry', exact: true }).click();
  await expect(page.getByText(/local-fixture-event-1/)).toBeVisible();
  const uploaded = await harness.control('inspect');
  expect(uploaded.uploads).toHaveLength(1);
  expect(uploaded.uploads[0].report).toEqual(reviewed);
  expect((await harness.rpc('upload_controller_debug', [active.snapshot.session, true])).success).toBe(false);
});

test('bridge rejects unauthenticated cross-origin oversized and non-allowlisted requests', async ({ page, request, harness }) => {
  await open(page);
  expect((await request.post('/api/control', { data: { command: 'inspect' } })).status()).toBe(403);
  expect((await harness.post('/api/control', { command: 'inspect' }, { Origin: 'https://untrusted.example' })).status()).toBe(403);
  expect((await harness.post('/api/rpc', { method: '_main', args: [] })).status()).toBe(400);
  expect((await harness.post('/api/rpc', { method: 'start_recording', args: [] })).status()).toBe(400);
  expect((await harness.post('/api/rpc', { method: 'get_controller_debug', args: [] })).status()).toBe(400);
  expect((await harness.post('/api/control', { command: 'write_file', path: '/etc/fixture', text: 'no' })).status()).toBe(400);
  expect((await harness.post('/api/control', { command: 'inspect', overflow: 'x'.repeat(9000) })).status()).toBe(413);
  const inspection = await harness.control('inspect');
  expect(inspection.snapshot.state).toBe('idle');
  expect(inspection.counts).toEqual({ microphone: 0, typing: 0, upload: 0 });
});
