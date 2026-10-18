import { test, expect } from './fixtures';

test('Advanced Sending keeps Paste default and persists each experimental insertion backend', async ({ page, harness }, testInfo) => {
  await page.setViewportSize({ width: 420, height: 900 });
  await page.goto('/');
  await page.getByRole('button', { name: 'Advanced settings', exact: true }).click();
  const method = page.getByLabel('Text insertion');
  await expect(method).toHaveValue('paste');
  await expect(page.getByText('Experimental: compare typing backends on your Steam Deck before sending in a game.')).toBeVisible();
  await method.selectOption('ydotool');
  await expect.poll(async () => (await harness.rpc('get_button_config')).config.textInsertionMode).toBe('ydotool');
  await method.selectOption('gamescope');
  await expect.poll(async () => (await harness.rpc('get_button_config')).config.textInsertionMode).toBe('gamescope');
  await expect(page.getByText('Gamescope typing never presses Enter. Check the draft and send it yourself. Maximum 40 characters including any channel prefix.')).toBeVisible();
  await expect(page.getByRole('checkbox', { name: 'Press Enter yourself' })).toBeChecked();
  await expect(page.getByRole('checkbox', { name: 'Press Enter yourself' })).toBeDisabled();
  expect((await harness.rpc('get_button_config')).config.manualSend).toBe(false);
  await page.reload();
  await page.getByRole('button', { name: 'Advanced settings', exact: true }).click();
  await expect(page.getByLabel('Text insertion')).toHaveValue('gamescope');
  await page.screenshot({ path: testInfo.outputPath('experimental-text-insertion.png'), fullPage: true });
  await page.getByLabel('Text insertion').selectOption('paste');
  await expect.poll(async () => (await harness.rpc('get_button_config')).config.textInsertionMode).toBe('paste');
});
