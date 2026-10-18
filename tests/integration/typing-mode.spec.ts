import { test, expect } from './fixtures';

test('Advanced Sending still offers the ydotool typing option', async ({ page, harness }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Advanced settings', exact: true }).click();
  const insertion = page.getByLabel('Text insertion');
  await insertion.selectOption('ydotool');
  await expect.poll(async () => (await harness.rpc('get_button_config')).config.textInsertionMode).toBe('ydotool');
  await expect(page.getByText('ydotool typing: US keyboard layout and ASCII only. Other text fails without sending.')).toBeVisible();
  expect((await harness.rpc('get_button_config')).config.manualSend).toBe(false);
});
