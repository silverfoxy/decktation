import { test, expect } from './fixtures';

test('pending Start has immediate dedicated feedback before the RPC response arrives', async ({ page, harness }) => {
  await harness.control('start_response_delay', { seconds: 1.5 });
  await diagnostics(page);
  await page.getByRole('button', { name: 'Start 30-second capture', exact: true }).click();
  await expect(page.getByText('Starting controller capture…', { exact: true })).toBeVisible({ timeout: 800 });
  await expect(page.getByRole('button', { name: 'Stop and review (touch or mouse)', exact: true })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Advanced settings', exact: true })).toHaveCount(0);
  await expect(page.getByText('Recording controller input', { exact: true })).toBeVisible();
});

test('production panel navigates to diagnostics and captures a real IPC report', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Advanced settings', exact: true }).click();
  await page.getByRole('button', { name: 'Diagnostics', exact: true }).click();
  await page.getByRole('button', { name: 'Start 30-second capture', exact: true }).click();
  await expect(page.getByText('Starting controller capture…', { exact: true })).toBeVisible();
  await expect(page.getByText('Recording controller input', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Stop and review (touch or mouse)', exact: true }).click();
  await expect(page.getByText('Finalizing controller report…', { exact: true })).toBeVisible();
  await expect(page.getByText('Controller report ready for review', { exact: true })).toBeVisible();
  const report = JSON.parse(await page.locator('pre').innerText());
  expect(report.phase).toBe('stopped');
  expect(report.events.length).toBeGreaterThan(0);
  expect(report.metadata.decktation_version).toBeTruthy();
  expect(report.devices).toEqual(expect.arrayContaining([
    expect.objectContaining({ status: 'accepted', vendor_id: 10462, keys: [704, 304] }),
    expect.objectContaining({ status: 'rejected' }),
  ]));
  expect(report.events).toEqual(expect.arrayContaining([
    expect.objectContaining({ code: 704, button: 'L4', pressed: true }),
    expect.objectContaining({ code: 704, button: 'L4', pressed: false }),
  ]));
  expect(JSON.stringify(report)).not.toContain('private-path');
});

async function diagnostics(page: any) {
  await page.goto('/');
  await page.getByRole('button', { name: 'Advanced settings', exact: true }).click();
  await page.getByRole('button', { name: 'Diagnostics', exact: true }).click();
}
async function recording(page: any) {
  await page.getByRole('button', { name: 'Start 30-second capture', exact: true }).click();
  await expect(page.getByText('Recording controller input', { exact: true })).toBeVisible();
}

test('delayed listener ACK starts a full real-time 30-second window', async ({ page, harness }) => {
  await harness.control('ack_delay', { seconds: 3.5 });
  await diagnostics(page);
  const requested = Date.now();
  await page.getByRole('button', { name: 'Start 30-second capture', exact: true }).click();
  await expect(page.getByText('Starting controller capture…', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Advanced settings', exact: true })).toHaveCount(0);
  // Do not advance a fake clock in this test: producer, backend and Chromium
  // independently use their actual clocks throughout ACK and automatic finish.
  await expect(page.getByText('Recording controller input', { exact: true })).toBeVisible();
  expect(Date.now() - requested).toBeGreaterThan(3000);
  const acknowledged = Date.now();
  await expect(page.getByText('30 seconds remaining', { exact: true })).toBeVisible();
  await expect(page.getByText('29 seconds remaining', { exact: true })).toBeVisible();
  await expect(page.getByText('Controller report ready for review', { exact: true })).toBeVisible({ timeout: 34000 });
  expect(Date.now() - acknowledged).toBeGreaterThan(29000);
  expect(JSON.parse(await page.locator('pre').innerText()).phase).toBe('complete');
});

test('duplicate Start and activating A release cannot Stop; mock A B arrows are consumed', async ({ page, harness }) => {
  await diagnostics(page);
  await page.getByRole('button', { name: 'Start 30-second capture', exact: true }).dblclick();
  await expect(page.getByText('Recording controller input', { exact: true })).toBeVisible();
  const active = await harness.control('inspect');
  const repeated = await harness.rpc('start_controller_debug');
  expect(repeated.session).toBe(active.snapshot.session);
  for (const [kind, button] of [['onButtonDown', 1], ['onButtonUp', 1], ['onOKButton', 1],
      ['onCancelButton', 2], ['onGamepadDirection', 9], ['onGamepadDirection', 10],
      ['onActivate', 1], ['onCancel', 2]] as const) {
    const result = await page.evaluate(([kind, button]) => (window as any).fixture.gamepad(kind, button), [kind, button]);
    expect(result.consumed).toBe(true);
  }
  const after = await harness.control('inspect');
  expect(after.snapshot.state).toBe('recording');
  expect(after.history.filter((call: any) => call.method === 'stop_controller_debug')).toHaveLength(0);
  await expect(page.getByRole('button', { name: 'Stop and review (touch or mouse)', exact: true })).toBeVisible();
});

test('background producer completes while panel is unmounted and remount resumes exact report', async ({ page, harness }) => {
  await diagnostics(page);
  await recording(page);
  const session = (await harness.control('inspect')).snapshot.session;
  await page.evaluate(() => (window as any).fixture.unmount());
  await expect(page.getByRole('heading')).toHaveCount(0);
  const before = (await harness.control('inspect')).history.filter((v: any) => v.method === 'get_controller_debug').length;
  await harness.control('advance', { seconds: 30 });
  await expect.poll(async () => (await harness.control('inspect')).snapshot.state).toBe('ready');
  const final = await harness.control('inspect');
  expect(final.history.filter((v: any) => v.method === 'get_controller_debug')).toHaveLength(before);
  await page.evaluate(() => (window as any).fixture.mount());
  await expect(page.getByText('Controller report ready for review', { exact: true })).toBeVisible();
  expect((await harness.control('inspect')).snapshot.session).toBe(session);
  expect(JSON.parse(await page.locator('pre').innerText())).toEqual(final.snapshot.report);
});
