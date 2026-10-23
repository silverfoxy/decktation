import { test, expect } from '@playwright/test';

test('an in-flight model download stays visible and blocks test dictation', async ({ page }) => {
  let finishSelection!: () => void;
  const pendingSelection = new Promise<void>(resolve => { finishSelection = resolve; });
  await page.route('**/api/rpc', async route => {
    if (JSON.parse(route.request().postData() || '{}').method !== 'set_model_size') {
      await route.continue();
      return;
    }
    await pendingSelection;
    await route.fulfill({json: {success: true, modelSize: 'medium', reloaded: true}});
  });
  await page.goto('/');
  await page.getByText('Advanced settings', { exact: true }).click();
  await page.getByRole('button', { name: /Model: Base/ }).click();
  await page.getByRole('button', { name: /Medium/ }).click();
  await page.evaluate(() => (window as any).fixture.control('model_download', {stage: 'downloading'}));
  await expect(page.getByRole('status').filter({hasText: 'Downloading transcription model'})).toBeVisible();
  await expect(page.getByRole('button', {name: /Small/})).toBeDisabled();
  await page.getByRole('button', {name: 'Back'}).click();
  await page.getByRole('button', {name: 'Back'}).click();
  await expect(page.getByRole('button', {name: /Test Dictation/})).toBeDisabled();
  await page.evaluate(() => (window as any).fixture.control('model_download', {stage: 'idle'}));
  finishSelection();
  await expect(page.getByText('Downloading transcription model')).toHaveCount(0);
  await expect(page.getByText('Advanced settings', {exact: true})).toBeVisible();
  await page.getByText('Advanced settings', {exact: true}).click();
  await expect(page.getByRole('button', {name: /Model: Medium/})).toBeVisible();
});
