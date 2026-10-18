import { readFile } from 'node:fs/promises';
import { test, expect } from './fixtures';

test('device DOM probe observes every capture phase including explicit upload', async ({ page, harness }) => {
  // Exercise the exact script shipped with the device runner, not a fabricated
  // CDP result. The browser adapter does not provide Steam's native .gpfocus.
  const expression = await readFile('scripts/deck/js/diagnostics.js', 'utf8');
  const probe = () => page.evaluate(expression);
  await harness.control('ack_delay', { seconds: 2 });
  await page.goto('/');
  await page.getByRole('button', { name: 'Advanced settings', exact: true }).click();
  await page.getByRole('button', { name: 'Diagnostics', exact: true }).click();
  const idle = await probe();
  expect(idle.visible).toBe(true);
  expect(idle.phase).toBe('idle');
  expect(idle.controls.start).toHaveLength(2);
  expect(idle.native_focus).toEqual([]);
  expect(idle.active_frontend_identity).toBe('inconclusive');

  await page.getByRole('button', { name: 'Start 30-second capture', exact: true }).click();
  await expect.poll(async () => (await probe()).phase).toBe('starting');
  await expect.poll(async () => (await probe()).phase).toBe('recording');
  const recording = await probe();
  expect(recording.seconds).toBeGreaterThan(0);
  expect(recording.seconds).toBeLessThanOrEqual(30);
  expect(recording.controls.stop).toHaveLength(2);
  await expect.poll(async () => (await probe()).events).toBeGreaterThan(0);

  await page.getByRole('button', { name: 'Stop and review (touch or mouse)', exact: true }).click();
  await expect.poll(async () => (await probe()).phase).toBe('stopping');
  await expect.poll(async () => (await probe()).phase).toBe('ready');
  const ready = await probe();
  expect(ready.controls.start).toBeUndefined();
  expect(ready.controls.send).toHaveLength(2);
  expect(ready.controls.back).toHaveLength(2);
  await page.getByRole('button', {name: 'Send this report to Sentry', exact: true}).click();
  await expect(page.getByText(/Report submitted\. Event ID/)).toBeVisible();
  await expect.poll(async () => (await probe()).phase).toBe('ready');
  expect((await probe()).controls.send).toBeUndefined();
  expect((await probe()).controls.back).toHaveLength(2);
  await page.getByRole('button', {name: 'Back', exact: true}).click();
  await expect.poll(async () => (await probe()).phase).toBe('ready');
  expect((await probe()).controls.start).toHaveLength(2);
  await expect(page.locator('pre')).toHaveCount(0);
});
