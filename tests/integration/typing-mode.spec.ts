import { test, expect } from './fixtures';

test('Advanced Sending explains the English keyboard requirement for Type', async ({ page, harness }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Advanced settings', exact: true }).click();
  const insertion = page.getByLabel('Text insertion');
  await insertion.selectOption('ydotool');
  await expect.poll(async () => (await harness.rpc('get_button_config')).config.textInsertionMode).toBe('ydotool');
  await expect(page.getByText('Type requires an English (US) keyboard layout and ASCII text. Other text fails without sending.')).toBeVisible();
  expect((await harness.rpc('get_button_config')).config.manualSend).toBe(false);
});
