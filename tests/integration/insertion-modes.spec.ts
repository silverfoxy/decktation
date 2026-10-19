import { test, expect } from './fixtures';

test('Advanced Sending keeps Paste default and persists Type', async ({ page, harness }, testInfo) => {
  await page.setViewportSize({ width: 420, height: 900 });
  await page.goto('/');
  await page.getByRole('button', { name: 'Advanced settings', exact: true }).click();
  const method = page.getByLabel('Text insertion');
  await expect(method).toHaveValue('paste');
  await expect(method.locator('option')).toHaveText(['Paste (default)', 'Type (only English keyboard)']);
  await method.selectOption('ydotool');
  await expect.poll(async () => (await harness.rpc('get_button_config')).config.textInsertionMode).toBe('ydotool');
  await page.reload();
  await page.getByRole('button', { name: 'Advanced settings', exact: true }).click();
  await expect(page.getByLabel('Text insertion')).toHaveValue('ydotool');
  await page.screenshot({ path: testInfo.outputPath('text-insertion.png'), fullPage: true });
  await page.getByLabel('Text insertion').selectOption('paste');
  await expect.poll(async () => (await harness.rpc('get_button_config')).config.textInsertionMode).toBe('paste');
});
