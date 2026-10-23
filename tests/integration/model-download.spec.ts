import { test, expect } from '@playwright/test';

test('Cancel requests download interruption and restores the previous model choice', async ({ page }, testInfo) => {
  let finishSelection!: () => void;
  const pendingSelection = new Promise<void>(resolve => { finishSelection = resolve; });
  let cancellationRequested = false;
  await page.route('**/api/rpc', async route => {
    const method = JSON.parse(route.request().postData() || '{}').method;
    if (method === 'set_model_size') {
      await pendingSelection;
      await route.fulfill({json: {success: false, cancelled: true, modelSize: 'base', error: 'Model download cancelled.'}});
    } else if (method === 'cancel_model_download') {
      cancellationRequested = true;
      finishSelection();
      await route.fulfill({json: {success: true, cancelling: true}});
    } else await route.continue();
  });
  await page.goto('/');
  await page.getByText('Advanced settings', {exact: true}).click();
  await page.getByRole('button', {name: /Model: Base/}).click();
  await page.getByRole('button', {name: /Medium/}).click();
  await page.evaluate(() => (window as any).fixture.control('model_download', {stage: 'downloading'}));
  await expect(page.getByRole('button', {name: 'Cancel download'})).toBeVisible();
  await page.screenshot({path: testInfo.outputPath('cancel-download-ui.png')});
  await page.getByRole('button', {name: 'Cancel download'}).click();
  await page.evaluate(() => (window as any).fixture.control('model_download', {stage: 'idle'}));
  await expect(page.getByRole('button', {name: /Small/})).toBeEnabled();
  await expect(page.getByRole('button', {name: /Base/})).toContainText('✓');
  expect(cancellationRequested).toBe(true);
});

test('Cancel on a restored enabled startup load clears the cancelling state', async ({ page }) => {
  let finishLoad!: () => void;
  const pendingLoad = new Promise<void>(resolve => { finishLoad = resolve; });
  let finishCancel!: () => void;
  const pendingCancel = new Promise<void>(resolve => { finishCancel = resolve; });
  let reportCancel!: () => void;
  const cancelSeen = new Promise<void>(resolve => { reportCancel = resolve; });
  await page.route('**/api/rpc', async route => {
    const method = JSON.parse(route.request().postData() || '{}').method;
    if (method === 'get_button_config') {
      await route.fulfill({json: {success: true, config: {enabled: true, modelSize: 'medium'}}});
    } else if (method === 'load_model') {
      await pendingLoad;
      await route.fulfill({json: {success: false, cancelled: true, error: 'Model download cancelled.'}});
    } else if (method === 'cancel_model_download') {
      reportCancel();
      await pendingCancel;
      await route.fulfill({json: {success: true, cancelling: true}});
    } else await route.continue();
  });
  await page.goto('/');
  await page.evaluate(() => (window as any).fixture.control('model_download', {stage: 'downloading'}));
  await page.getByRole('button', {name: 'Cancel download'}).click();
  await cancelSeen;
  await expect(page.getByRole('button', {name: 'Cancelling model download...'})).toBeVisible();
  finishCancel();
  finishLoad();
  await page.evaluate(() => (window as any).fixture.control('model_download', {stage: 'idle'}));
  await expect(page.getByRole('button', {name: 'Cancelling model download...'})).toHaveCount(0);
  // A later download must present an active Cancel control, not a stuck old request.
  await page.evaluate(() => (window as any).fixture.control('model_download', {stage: 'downloading'}));
  await expect(page.getByRole('button', {name: 'Cancel download'})).toBeEnabled();
  await page.evaluate(() => (window as any).fixture.control('model_download', {stage: 'idle'}));
});

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
