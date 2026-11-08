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

for (const viewport of [{ width: 1280, height: 800, rows: 10 }, { width: 800, height: 600, rows: 8 }]) {
  test(`profile editor fits compact controls and multiple channels at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await openEditor(page);
    const layout = await page.locator('.decktation-editor').evaluate(root => {
      const list = root.querySelector('.channel-rows')!;
      const bounds = list.getBoundingClientRect();
      const rows = Array.from(list.querySelectorAll('button')).map(button => button.getBoundingClientRect());
      const details = root.querySelector('.details')!;
      return {
        visibleRows: rows.filter(row => row.top >= bounds.top && row.bottom <= bounds.bottom).length,
        tallestRow: Math.max(...rows.map(row => row.height)),
        outerScroll: root.scrollHeight > root.clientHeight,
        outerHorizontalScroll: root.scrollWidth > root.clientWidth,
        listParentScroll: list.parentElement!.scrollHeight > list.parentElement!.clientHeight,
        detailsScroll: details.scrollHeight > details.clientHeight,
      };
    });
    expect(layout.visibleRows).toBeGreaterThanOrEqual(viewport.rows);
    expect(layout.tallestRow).toBeLessThanOrEqual(36);
    expect(layout.outerScroll).toBe(false);
    expect(layout.outerHorizontalScroll).toBe(false);
    expect(layout.listParentScroll).toBe(false);
    expect(layout.detailsScroll).toBe(false);
    await expect(page.getByRole('button', { name: 'Save changes', exact: true })).toBeInViewport();
    for (const name of ['Back', 'Save changes']) {
      const bounds = await page.getByRole('button', { name, exact: true }).boundingBox();
      expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(viewport.height - 48);
    }
    await page.screenshot({ path: `/tmp/decktation-profile-editor-compact-${viewport.width}.png` });
  });
}

test('controller directions follow horizontal rows and channel panes', async ({ page }) => {
  await openEditor(page);
  const direction = (button: number) => page.evaluate(button => (window as any).fixture.gamepad('onGamepadDirection', button), button);
  const channels = page.getByRole('button', { name: /Channels/ });
  const keywords = page.getByRole('button', { name: /Keywords/ });
  await channels.focus();
  await direction(12);
  await expect(keywords).toBeFocused();
  await direction(11);
  await expect(channels).toBeFocused();
  const party = page.getByRole('button', { name: /^party/i });
  await party.click();
  await party.focus();
  await direction(12);
  await expect(page.getByLabel('Chat command')).toBeFocused();
  await direction(11);
  await expect(party).toBeFocused();
  await direction(10);
  await expect(party).not.toBeFocused();
  const trigger = page.getByLabel('New spoken trigger');
  await trigger.fill('group');
  await direction(12);
  await expect(page.getByRole('button', { name: 'Add trigger', exact: true })).toBeFocused();
  await direction(11);
  await expect(trigger).toBeFocused();
});

test('trigger remains visible above an overlay keyboard and in a reduced viewport', async ({ page }) => {
  await page.setViewportSize({ width: 800, height: 600 });
  await openEditor(page);
  const trigger = page.getByLabel('New spoken trigger');
  const original = await trigger.boundingBox();
  await trigger.fill('group');
  await expect.poll(() => trigger.evaluate(input => input.getBoundingClientRect().y)).toBe(original!.y);
  await expect(page.locator('.details')).not.toHaveAttribute('data-editor-editing');
  await page.evaluate(() => {
    const keyboard = document.createElement('div');
    keyboard.className = 'fixture-virtual-keyboard';
    keyboard.style.cssText = 'position:fixed;left:0;right:0;top:320px;bottom:0;background:#222;z-index:9999';
    document.body.append(keyboard);
  });
  await expect.poll(async () => trigger.evaluate(input => input.getBoundingClientRect().bottom)).toBeLessThanOrEqual(280);
  await expect.poll(() => page.locator('.details').evaluate(pane => pane.scrollHeight > pane.clientHeight)).toBe(true);
  await page.evaluate(() => document.querySelector('.fixture-virtual-keyboard')!.remove());
  await expect(page.locator('.details')).not.toHaveAttribute('data-editor-editing');
  await expect.poll(() => trigger.evaluate(input => input.getBoundingClientRect().y)).toBe(original!.y);
  await page.setViewportSize({ width: 800, height: 320 });
  await expect(trigger).toBeInViewport();
  await trigger.press('End');
  await trigger.pressSequentially(' chat');
  await expect(trigger).toHaveValue('group chat');
  await expect(page.getByText('Include a space after the chat command, for example', { exact: false })).toBeAttached();
});


test('Steam overlay visual viewport metrics cannot collapse the editor', async ({ page }) => {
  await page.setViewportSize({ width: 800, height: 600 });
  await page.addInitScript(() => {
    // Steam can expose overlay/zoom viewport metrics instead of the route size.
    const viewport = new EventTarget();
    Object.assign(viewport, { height: 48, offsetTop: 500, scale: 1 });
    Object.defineProperty(window, 'visualViewport', { configurable: true, value: viewport });
  });
  await openEditor(page);
  const bounds = await page.locator('.decktation-editor').boundingBox();
  expect(bounds!.y).toBe(0);
  expect(bounds!.height).toBe(600);
  await expect(page.getByLabel('Chat command')).toBeInViewport();
  await expect(page.getByRole('button', { name: 'Save changes', exact: true })).toBeInViewport();
  await page.evaluate(() => window.visualViewport!.dispatchEvent(new Event('resize')));
  await expect.poll(() => page.locator('.decktation-editor').evaluate(root => root.getBoundingClientRect().height)).toBe(600);
});

test('every prefix can move directly into the text pane without traversing the list', async ({ page }) => {
  await page.setViewportSize({ width: 800, height: 600 });
  await openEditor(page);
  const direction = (button: number) => page.evaluate(button => (window as any).fixture.gamepad('onGamepadDirection', button), button);
  // These focus containers are required by Steam's native traversal, which the
  // browser adapter does not implement.
  await expect(page.locator('.workspace')).toHaveAttribute('flow-children', 'row');
  await expect(page.locator('.channel-rows')).toHaveAttribute('flow-children', 'column');
  await expect(page.locator('.details-body')).toHaveAttribute('flow-children', 'column');
  const rows = page.locator('.channel-row button');
  for (let index = 0; index < await rows.count(); index++) {
    await rows.nth(index).focus();
    await direction(12);
    await expect(page.getByLabel('Chat command')).toBeFocused();
  }
  await page.getByLabel('New spoken trigger').focus();
  await direction(11);
  await expect(page.locator('.channel-row.selected button')).toBeFocused();
  await page.getByLabel('Game profile').focus();
  await direction(10);
  await expect(page.getByLabel('Chat command')).toBeFocused();
});


test('keyboard leaves an unobstructed text field in place', async ({ page }) => {
  await page.setViewportSize({ width: 800, height: 600 });
  await openEditor(page);
  const field = page.getByLabel('Chat command');
  await field.focus();
  const before = await field.boundingBox();
  await page.evaluate(() => {
    const keyboard = document.createElement('div');
    keyboard.className = 'fixture-virtual-keyboard';
    keyboard.style.cssText = 'position:fixed;left:0;right:0;top:320px;bottom:0';
    document.body.append(keyboard);
  });
  await expect(page.locator('.details')).not.toHaveAttribute('data-editor-editing');
  await expect.poll(() => field.evaluate(input => input.getBoundingClientRect().y)).toBe(before!.y);
});


test('physical arrows cross prefix panes and preserve text caret movement', async ({ page }) => {
  await openEditor(page);
  const prefixes = page.locator('.channel-row button');
  for (let index = 0; index < await prefixes.count(); index++) {
    await prefixes.nth(index).focus();
    await page.keyboard.press('ArrowRight');
    await expect(page.getByLabel('Chat command')).toBeFocused();
  }
  const field = page.getByLabel('Chat command');
  await field.fill('/party');
  await page.keyboard.press('ArrowLeft');
  await expect(field).toBeFocused();
  await page.getByRole('button', { name: /^party/i }).click();
  await page.getByRole('button', { name: /Use as default channel/ }).focus();
  await page.keyboard.press('ArrowLeft');
  await expect(page.locator('.channel-row.selected button')).toBeFocused();
});

test('native Steam direction events use virtual focus even when DOM focus differs', async ({ page }) => {
  await openEditor(page);
  await page.getByRole('button', { name: /Channels/ }).focus();
  await page.locator('.channel-row button').last().evaluate(button => {
    button.dispatchEvent(new CustomEvent('vgp_ondirection', { bubbles: true, cancelable: true, detail: { button: 12 } }));
  });
  await expect(page.getByLabel('Chat command')).toBeFocused();
});

test('Steam keyboard visibility reveals covered input even without keyboard DOM', async ({ page }) => {
  await page.setViewportSize({ width: 800, height: 600 });
  await openEditor(page);
  const field = page.getByLabel('New spoken trigger');
  await field.fill('group');
  const before = await field.boundingBox();
  await page.evaluate(() => window.dispatchEvent(new CustomEvent('fixture-keyboard-status', { detail: true })));
  await expect.poll(() => field.evaluate(input => input.getBoundingClientRect().bottom)).toBeLessThanOrEqual(230);
  await expect(page.locator('.details')).toHaveAttribute('data-editor-editing', 'true');
  await page.evaluate(() => window.dispatchEvent(new CustomEvent('fixture-keyboard-status', { detail: false })));
  await expect.poll(() => field.evaluate(input => input.getBoundingClientRect().y)).toBe(before!.y);
});


test('pane navigation works inside a separate Steam window document', async ({ page }) => {
  await openEditor(page);
  const result = await page.evaluate(async () => {
    const { moveEditorFocus } = (window as any).fixture;
    const frame = document.createElement('iframe');
    document.body.append(frame);
    const doc = frame.contentDocument!;
    doc.body.innerHTML = '<div id="editor"><div class="channel-list"><div class="channel-row selected"><button>party</button></div></div><div class="details"><input aria-label="command"></div></div>';
    const root = doc.getElementById('editor')!;
    const channel = doc.querySelector('button')!;
    const command = doc.querySelector('input')!;
    let requested = 0;
    root.addEventListener('vgp_requestfocus', () => requested++);
    channel.focus();
    const right = moveEditorFocus(root, 12, channel) && doc.activeElement === command;
    const left = moveEditorFocus(root, 11, command) && doc.activeElement === channel;
    frame.remove();
    return { right, left, requested };
  });
  expect(result).toEqual({ right: true, left: true, requested: 2 });
});


test('editor opens the active game and can create and save a new profile', async ({ page, harness }) => {
  expect((await harness.rpc('set_active_preset', ['guildwars2'])).success).toBe(true);
  await openEditor(page);
  await expect(page.getByLabel('Game profile')).toHaveValue('guildwars2');
  await page.getByRole('button', { name: 'New profile', exact: true }).click();
  await page.getByLabel('New profile name').fill('My Game');
  await page.getByRole('button', { name: 'Create profile', exact: true }).click();
  await expect(page.getByLabel('Game profile')).toHaveValue('my_game');
  await expect(page.getByLabel('Chat command')).toHaveValue('');
  await page.getByLabel('Chat command').fill('/chat ');
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await expect(page.getByRole('status')).toHaveText('Saved');
  expect((await harness.rpc('get_profile_editor', ['my_game'])).profile.channels.type).toBe('/chat ');
  // Creating/editing does not implicitly change the active game.
  expect((await harness.rpc('get_active_preset')).game).toBe('guildwars2');
  await page.getByRole('button', { name: 'Back', exact: true }).click();
  await page.getByRole('button', { name: /^Mode:/ }).click();
  await page.getByRole('button', { name: 'My Game', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Mode: My Game', exact: true })).toBeVisible();
  await openEditor(page);
  await expect(page.getByLabel('Game profile')).toHaveValue('my_game');
});
