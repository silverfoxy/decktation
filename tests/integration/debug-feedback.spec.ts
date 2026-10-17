import { test, expect } from './fixtures';
import type { Page } from '@playwright/test';
import type { Harness } from './fixtures';

// Keep behavior assertions independent of minor English copy changes.
async function openDebugger(page: Page) {
  await page.goto('/');
  await page.getByRole('button', { name: 'Advanced settings', exact: true }).click();
  await page.getByRole('button', { name: 'Diagnostics', exact: true }).click();
}
function debuggerPanel(page: Page) {
  return page.locator('section').filter({ has: page.getByRole('heading', { name: /controller.*debug/i }) });
}
async function start(page: Page) {
  await openDebugger(page);
  await debuggerPanel(page).getByRole('button', { name: /start.*capture|^start$|record.*input/i }).click();
  await expect(page.getByText('Recording controller input', { exact: true })).toBeVisible();
}

test('compact capture keeps instructions stats and Stop readable in a narrow panel', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await start(page);
  const panel = debuggerPanel(page);
  // A bounded copy budget catches the old wall of prose without freezing wording.
  expect((await panel.innerText()).length).toBeLessThan(400);
  await expect(panel.getByText(/Events(?: captured)?:\s*\d+.*(?:interfaces|sources):\s*\d+/i)).toBeVisible();
  const stop = panel.getByRole('button', { name: /stop/i });
  await expect(stop).toBeInViewport();
  expect(await panel.evaluate(node => node.scrollWidth <= node.clientWidth)).toBe(true);
});

async function ready(page: Page) {
  await debuggerPanel(page).getByRole('button', { name: /stop/i }).click();
  await expect(page.locator('pre')).toBeVisible();
}

test('report submission control precedes the full report preview in document and visual order', async ({ page }) => {
  await start(page);
  await ready(page);
  const send = debuggerPanel(page).getByRole('button', { name: /send.*report|submit.*report/i });
  await expect(send).toBeEnabled();
  expect(await send.evaluate(button => {
    const preview = document.querySelector('pre')!;
    return Boolean(button.compareDocumentPosition(preview) & Node.DOCUMENT_POSITION_FOLLOWING);
  })).toBe(true);
  const sendBox = await send.boundingBox();
  const previewBox = await page.locator('pre').boundingBox();
  expect(sendBox!.y + sendBox!.height).toBeLessThanOrEqual(previewBox!.y);
});

test('explicit upload confirms Report submitted and preserves the exact reviewed report', async ({ page, harness }) => {
  await start(page);
  await ready(page);
  const reviewed = JSON.parse(await page.locator('pre').innerText());
  expect((await harness.control('inspect')).counts.upload).toBe(0);
  await debuggerPanel(page).getByRole('button', { name: /send.*report|submit.*report/i }).click();
  const feedback = page.getByRole('status').filter({ hasText: 'local-fixture-event-1' });
  await expect(feedback).toBeVisible();
  await expect(feedback).toContainText('Report submitted');
  await expect(feedback).not.toContainText(/queued|delivery not confirmed/i);
  const submitted = await harness.control('inspect');
  expect(submitted.uploads).toHaveLength(1);
  expect(submitted.uploads[0].report).toEqual(reviewed);
  expect((await snapshot(harness)).report).toEqual(reviewed);
});

test('reviewed producer report includes bounded capture outcome and enriched host metadata', async ({ page, harness }) => {
  await start(page);
  await harness.control('input', { source: 'controller', button: 'L4', pressed: true });
  await ready(page);
  const report = JSON.parse(await page.locator('pre').innerText());
  // Outcome field names are the shared contract; leave enum/object details to
  // report-schema tests so the browser lane tests useful review evidence.
  expect(report.duration_ms).toEqual(expect.any(Number));
  expect(report.duration_ms).toBeGreaterThanOrEqual(0);
  expect(report.duration_ms).toBeLessThanOrEqual(30000);
  expect(report.stop_reason).toEqual(expect.any(String));
  expect(report.stop_reason.length).toBeGreaterThan(0);
  expect(report).toHaveProperty('initial_state');
  expect(report).toHaveProperty('truncation');
  expect(report.metadata).toMatchObject({
    decktation_version: expect.any(String), os_id: expect.any(String),
    kernel_release: expect.any(String), architecture: expect.any(String),
  });
  expect(report.devices).toEqual(expect.arrayContaining([
    expect.objectContaining({ source: 'source_1', status: 'accepted', vendor_id: 10462, product_id: 4613 }),
    expect.objectContaining({ source: 'source_2', status: 'rejected' }),
  ]));
  expect(report.events).toEqual(expect.arrayContaining([
    expect.objectContaining({ source: 'source_1', code: 704, button: 'L4', pressed: true }),
  ]));
  expect((await snapshot(harness)).report).toEqual(report);
  expect(JSON.stringify(report)).not.toMatch(/private-path|serial_number|\/dev\/input/);
});

test('bounded replay controls exercise real key and HID producer events and frozen terminal evidence', async ({ page, harness }) => {
  await start(page);
  const active = await snapshot(harness);
  expect(active.report).toBeNull();
  for (const extra of [
    { source: '/dev/input/event0', button: 'L4', pressed: true },
    { source: 'controller', button: 'KEY_A', pressed: true },
    { source: 'controller', button: 'L4', pressed: 'true' },
  ]) {
    expect((await harness.post('/api/control', { command: 'input', ...extra })).status()).toBe(400);
  }
  for (const source of ['controller', 'hidraw']) {
    for (const pressed of [true, false]) {
      await harness.control('input', { source, button: 'L4', pressed });
    }
  }
  await ready(page);
  const frozen = JSON.parse(await page.locator('pre').innerText());
  expect(frozen.events.slice(-4)).toEqual([
    expect.objectContaining({ source: 'source_1', kind: 'key', code: 704, button: 'L4', pressed: true }),
    expect.objectContaining({ source: 'source_1', kind: 'key', code: 704, button: 'L4', pressed: false }),
    expect.objectContaining({ source: 'source_3', kind: 'hid', button: 'L4', pressed: true }),
    expect.objectContaining({ source: 'source_3', kind: 'hid', button: 'L4', pressed: false }),
  ]);
  await harness.control('input', { source: 'controller', button: 'L4', pressed: true });
  await harness.control('input', { source: 'hidraw', button: 'L4', pressed: true });
  expect((await snapshot(harness)).report).toEqual(frozen);
  expect(JSON.parse(await page.locator('pre').innerText())).toEqual(frozen);
});

async function snapshot(harness: Harness) {
  const inspected = await harness.control('inspect');
  expect(inspected.actor_error).toBeNull();
  return harness.rpc('get_controller_debug', [inspected.snapshot.session]);
}

for (const source of ['controller', 'hidraw']) {
  test(`live ${source} press and release cross actual producer IPC into visible button source and stats`, async ({ page, harness }) => {
    await start(page);
    const before = await snapshot(harness);
    await harness.control('input', { source, button: 'L4', pressed: true });
    await expect.poll(async () => (await snapshot(harness)).live_input?.pressed).toEqual([
      { source: source === 'controller' ? 'source_1' : 'source_3', button: 'L4' },
    ]);
    const held = await snapshot(harness);
    expect(held.report).toBeNull();
    expect(held.event_count).toBeGreaterThan(before.event_count);
    expect(held.live_input.last_event).toMatchObject({
      source: source === 'controller' ? 'source_1' : 'source_3',
      kind: source === 'controller' ? 'key' : 'hid', button: 'L4', pressed: true,
    });
    expect(held.live_input.last_event.at_ms).toBeGreaterThanOrEqual(0);
    expect(held.live_input.last_event.at_ms).toBeLessThanOrEqual(30000);
    const panel = debuggerPanel(page);
    const alias = source === 'controller' ? 'source_1' : 'source_3';
    // Match the held-button row, not a stale last-event label elsewhere.
    const live = panel.getByRole('status').filter({ has: page.getByText('Held buttons', { exact: true }) });
    await expect(live.getByText(`L4 · Source: ${alias}`, { exact: true })).toBeVisible();
    await expect(panel.getByText(`Events captured: ${held.event_count} · Controller interfaces: ${held.device_count}`, { exact: true })).toBeVisible();
    await expect(page.locator('pre')).toHaveCount(0);
    await harness.control('input', { source, button: 'L4', pressed: false });
    await expect.poll(async () => (await snapshot(harness)).live_input?.pressed).toEqual([]);
    await expect.poll(async () => (await snapshot(harness)).live_input?.last_event?.pressed).toBe(false);
    await expect(live.getByText('No buttons held', { exact: true })).toBeVisible();
    // Stop while held: terminal status must not retain live recording state.
    await harness.control('input', { source, button: 'L4', pressed: true });
    await expect.poll(async () => (await snapshot(harness)).live_input?.pressed?.length).toBe(1);
    await panel.getByRole('button', { name: /stop/i }).click();
    await expect(page.locator('pre')).toBeVisible();
    const ready = await snapshot(harness);
    expect(ready.live_input?.pressed ?? []).toEqual([]);
    expect(ready.live_input?.last_event ?? null).toBeNull();
    const frozen = JSON.parse(await page.locator('pre').innerText());
    expect(frozen).toEqual(ready.report);
    await harness.control('input', { source, button: 'L4', pressed: true });
    expect((await snapshot(harness)).report).toEqual(frozen);
    expect(JSON.parse(await page.locator('pre').innerText())).toEqual(frozen);
    expect(JSON.stringify(frozen)).not.toContain('private-path');
  });
}
