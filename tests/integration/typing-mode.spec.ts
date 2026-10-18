import { test, expect } from './fixtures';

test('Advanced Sending offers persisted keyboard injection without changing submit mode', async ({ page, harness }, testInfo) => {
  await page.setViewportSize({ width: 420, height: 900 });
  await page.goto('/');
  await page.getByRole('button', { name: 'Advanced settings', exact: true }).click();
  const toggle = page.getByRole('checkbox', { name: 'Type text as keystrokes' });
  await expect(toggle).toBeVisible();
  await expect(page.getByText('For games that block paste, like Old School RuneScape. Slower; ASCII only.')).toBeVisible();
  await expect(toggle).not.toBeChecked();
  await toggle.click();
  await expect(toggle).toBeChecked();
  await expect.poll(async () => (await harness.rpc('get_button_config')).config.typeAsKeys).toBe(true);
  expect((await harness.rpc('get_button_config')).config.manualSend).toBe(false);
  await page.reload();
  await page.getByRole('button', { name: 'Advanced settings', exact: true }).click();
  await expect(page.getByRole('checkbox', { name: 'Type text as keystrokes' })).toBeChecked();
  await page.screenshot({ path: testInfo.outputPath('advanced-sending-keyboard-mode.png'), fullPage: true });
});
