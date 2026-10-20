import { test, expect } from './fixtures';
import type { Page } from '@playwright/test';

const label = 'Stop and review (touch or mouse)';
async function open(page: Page) {
  await page.goto('/');
  await page.getByRole('button', { name: 'Advanced settings', exact: true }).click();
  await page.getByRole('button', { name: 'Diagnostics', exact: true }).click();
  await page.getByRole('button', { name: 'Start 30-second capture', exact: true }).scrollIntoViewIfNeeded();
  expect(await page.evaluate(() => window.scrollY)).toBeGreaterThan(0);
  await page.getByRole('button', { name: 'Start 30-second capture', exact: true }).click();
  await expect(page.getByText('Starting controller capture…', { exact: true })).toBeVisible();
  const initial = await boxes(page);
  await expect(page.getByText('Recording controller input', { exact: true })).toBeVisible();
  return initial;
}
async function boxes(page: Page) {
  return Promise.all([
    page.getByRole('status').first(),
    page.getByText(/Events captured:.*Controller interfaces:/),
    page.getByRole('button', { name: label, exact: true }),
  ].map(node => node.boundingBox()));
}
async function fullyVisible(page: Page, node: ReturnType<Page['getByRole']>) {
  const box = await node.boundingBox();
  expect(box).not.toBeNull();
  expect(box!.y).toBeGreaterThanOrEqual(0);
  expect(box!.y + box!.height).toBeLessThanOrEqual(page.viewportSize()!.height);
  expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.x + box!.width).toBeLessThanOrEqual(page.viewportSize()!.width);
}

for (const size of [{width: 320, height: 600}, {width: 360, height: 640}]) {
  test(`live capture rows do not move across simultaneous long inputs ${size.width}`, async ({ page, harness }, testInfo) => {
    await page.setViewportSize(size);
    const initial = await open(page);
    expect(await boxes(page)).toEqual(initial);
    const live = page.getByRole('status').filter({ has: page.getByText('Held buttons', { exact: true }) });
    await expect(live).toContainText('No buttons held');
    const held = ['L4', 'Left Trackpad', 'Right Trackpad', 'D-pad Right', 'D-pad Left'];
    for (const [i, button] of held.entries()) {
      await harness.control('input', { source: 'hidraw', button, pressed: true });
      await expect(live).toContainText(`${button} · Source: source_3`);
      if (i === 0) expect(await boxes(page)).toEqual(initial);
    }
    await page.screenshot({path: testInfo.outputPath(`${process.env.LAYOUT_STAGE || 'after'}-held-${size.width}.png`)});
    expect(await boxes(page)).toEqual(initial);
    await fullyVisible(page, page.getByRole('button', { name: label, exact: true }));
    for (const button of held) await harness.control('input', { source: 'hidraw', button, pressed: false });
    await expect(live).toContainText('No buttons held');
    await expect(live).not.toContainText('source_3');
    expect(await boxes(page)).toEqual(initial);
    await harness.control('advance', {seconds: 11});
    await expect(page.getByText(/1\d seconds remaining/)).toBeVisible();
    expect(await boxes(page)).toEqual(initial);
    await page.getByRole('button', {name: label, exact: true}).click();
    await expect(page.getByText('Finalizing controller report…', {exact: true})).toBeVisible();
    expect(await boxes(page)).toEqual(initial);
    await expect(live).not.toContainText('source_3');
  });
  for (const finish of ['stop', 'automatic']) {
    test(`ready Send stays fully visible after ${finish} and preview scroll ${size.width}`, async ({ page, harness }, testInfo) => {
      await page.setViewportSize(size);
      await open(page);
      // Grow the real producer report, not a hand-written RPC response.
      for (let i = 0; i < 12; i++) {
        await harness.control('input', {source: 'hidraw', button: 'Right Trackpad', pressed: i % 2 === 0});
      }
      if (finish === 'stop') await page.getByRole('button', {name: label, exact: true}).click();
      else {
        // Model a slow replay deterministically. A fixed 30-second jump from here
        // would skip the producer's two-second finalization window.
        await harness.control('advance', {seconds: 3});
        const {snapshot} = await harness.control('inspect');
        expect(snapshot.state).toBe('recording');
        await harness.control('advance', {seconds: snapshot.remaining_ms / 1000 + 0.05});
      }
      await expect(page.locator('pre')).toBeVisible();
      if (finish === 'automatic') {
        const {snapshot} = await harness.control('inspect');
        expect(snapshot.state).toBe('ready');
        expect(snapshot.report.phase).toBe('complete');
      }
      await page.screenshot({path: testInfo.outputPath(`${process.env.LAYOUT_STAGE || 'after'}-ready-${finish}-${size.width}.png`)});
      const send = page.getByRole('button', {name: 'Send this report to Sentry', exact: true});
      await fullyVisible(page, send);
      await expect(page.getByRole('heading', {name: 'Input and service', exact: true})).toHaveCount(0);
      await expect(page.getByText('Held buttons', {exact: true})).toHaveCount(0);
      const back = page.getByRole('button', {name: 'Back', exact: true});
      await fullyVisible(page, back);
      const before = await Promise.all([send.boundingBox(), back.boundingBox()]);
      const preview = page.locator('pre');
      expect(await preview.evaluate(node => node.scrollHeight > node.clientHeight)).toBe(true);
      await preview.evaluate(node => {node.scrollTop = node.scrollHeight;});
      expect(await preview.evaluate(node => node.scrollTop)).toBeGreaterThan(0);
      expect(await Promise.all([send.boundingBox(), back.boundingBox()])).toEqual(before);
      expect((await harness.control('inspect')).counts.upload).toBe(0);
      await back.focus();
      const cancel = await page.evaluate(() => (window as any).fixture.gamepad('onCancel', 2));
      expect(cancel.consumed).toBe(false);
      await expect(page.getByRole('heading', {name: 'Input and service', exact: true})).toBeVisible();
      await expect(page.getByRole('button', {name: 'Start 30-second capture', exact: true})).toBeVisible();
      // Polling the same ready session must not reopen the dedicated report.
      await page.waitForTimeout(600);
      await expect(page.locator('pre')).toHaveCount(0);
      await page.getByRole('button', {name: 'Start 30-second capture', exact: true}).click();
      await expect(page.getByText('Recording controller input', {exact: true})).toBeVisible();
      await expect(page.getByText('No buttons held', {exact: true})).toBeVisible();
      await page.getByRole('button', {name: label, exact: true}).click();
      await expect(send).toBeVisible();
      await page.getByRole('button', {name: 'Back', exact: true}).click();
      await expect(page.getByRole('heading', {name: 'Input and service', exact: true})).toBeVisible();
    });
  }
}
