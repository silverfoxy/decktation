import { test, expect } from './fixtures';

async function openEditor(page: any) {
  await page.goto('/');
  await page.getByRole('button', { name: /^Mode:/ }).click();
  await page.getByRole('button', { name: 'Edit game profile', exact: true }).click();
  await expect(page).toHaveURL(/\/decktation\/profiles$/);
  await expect(page.getByLabel('Search channels')).toBeVisible();
}

test('fullscreen profile editor saves vocabulary and spoken channel triggers', async ({ page, harness }) => {
  await openEditor(page);
  await page.getByRole('button', { name: /party/i }).click();
  await page.getByLabel('New spoken trigger').fill('group');
  await page.getByRole('button', { name: 'Add trigger', exact: true }).click();
  await page.getByLabel('Chat command').fill('/p');
  await page.getByRole('button', { name: 'Keywords', exact: false }).click();
  await page.getByLabel('New keyword').fill('Azeroth');
  await page.getByRole('button', { name: 'Add keyword', exact: true }).click();
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await expect(page.getByRole('status')).toHaveText('Saved');
  const saved = await harness.rpc('get_profile_editor', ['wow']);
  expect(saved.profile.hotwords).toEqual(['Azeroth']);
  expect(saved.profile.channel_triggers.group).toBe('party');
  expect(saved.profile.channels.party).toBe('/p ');
  await page.getByRole('button', { name: /Channels/ }).click();
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.screenshot({ path: '/tmp/decktation-profile-editor-fullscreen.png' });
});

test('profile editor searches, adds channels and protects unsaved changes', async ({ page, harness }) => {
  await openEditor(page);
  await page.getByLabel('Search channels').fill('/raid');
  await expect(page.getByRole('button', { name: /^party/i })).toHaveCount(0);
  await page.getByLabel('Search channels').fill('');
  await page.getByRole('button', { name: 'Add channel', exact: true }).click();
  await page.getByLabel('New channel name').fill('friends');
  await page.getByRole('button', { name: 'Add channel', exact: true }).click();
  await page.getByLabel('Chat command').fill('/join');
  await page.getByRole('button', { name: 'Back', exact: true }).click();
  await expect(page.getByRole('alertdialog')).toBeVisible();
  await page.getByRole('button', { name: 'Keep editing', exact: true }).click();
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await expect(page.getByRole('status')).toHaveText('Saved');
  const saved = await harness.rpc('get_profile_editor', ['wow']);
  expect(saved.profile.channels.friends).toBe('/join ');
  await page.getByLabel('Chat command').fill('/other');
  await page.getByLabel('Game profile').selectOption('guildwars2');
  await page.getByRole('button', { name: 'Discard changes', exact: true }).click();
  await expect(page.getByLabel('Game profile')).toHaveValue('guildwars2');
  await page.getByLabel('Search channels').fill('squad');
  await expect(page.getByRole('button', { name: /^squad/i })).toBeVisible();
  expect((await harness.rpc('get_profile_editor', ['wow'])).profile.channels.friends).toBe('/join ');
});

test('profile editor rejects conflicting triggers and controller Back keeps unsaved work', async ({ page }) => {
  await openEditor(page);
  await page.getByRole('button', { name: /party/i }).click();
  await page.getByLabel('New spoken trigger').fill('group');
  await page.getByRole('button', { name: 'Add trigger', exact: true }).click();
  await page.getByRole('button', { name: /^raid/i }).click();
  await page.getByLabel('New spoken trigger').fill('group');
  await page.getByRole('button', { name: 'Add trigger', exact: true }).click();
  await expect(page.getByRole('alert')).toHaveText('Each spoken trigger must belong to one channel.');
  await page.getByLabel('New spoken trigger').fill('');
  await page.getByRole('button', { name: 'Back', exact: true }).focus();
  await page.evaluate(() => (window as any).fixture.gamepad('onCancel', 2));
  await expect(page.getByRole('alertdialog')).toBeVisible();
  await page.getByRole('button', { name: 'Keep editing', exact: true }).click();
  await page.getByRole('button', { name: /party/i }).click();
  await expect(page.getByRole('button', { name: 'Remove trigger: group ×', exact: true })).toBeVisible();
});
