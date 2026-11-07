import { GamepadButton } from "decky-frontend-lib";

const controls = 'button, input, select, textarea, [role="button"]';
function available(root: Element): HTMLElement[] {
    return Array.from(root.querySelectorAll<HTMLElement>(controls)).filter(element =>
        !element.matches(':disabled, [aria-disabled="true"]') && element.getClientRects().length > 0);
}
function focus(element?: HTMLElement) {
    if (!element) return false;
    element.focus({ preventScroll: true });
    element.scrollIntoView({ block: 'nearest', inline: 'nearest' });
    return true;
}

// Steam's default column traversal does not follow these full-screen rows.
export function moveEditorFocus(root: HTMLElement, direction: number): boolean {
    const active = document.activeElement as HTMLElement | null;
    if (!active || !root.contains(active)) return false;
    const horizontal = direction === GamepadButton.DIR_LEFT || direction === GamepadButton.DIR_RIGHT;
    const vertical = direction === GamepadButton.DIR_UP || direction === GamepadButton.DIR_DOWN;
    if (!horizontal && !vertical) return false;
    const forward = direction === GamepadButton.DIR_RIGHT || direction === GamepadButton.DIR_DOWN ? 1 : -1;
    const scope = root.querySelector<HTMLElement>('[role="alertdialog"]') || root;
    const from = active.getBoundingClientRect();
    const centerX = from.left + from.width / 2, centerY = from.top + from.height / 2;
    const row = active.closest<HTMLElement>('[data-nav-row]');
    if (horizontal && row && scope.contains(row)) {
        const peers = available(row).filter(element => element !== active).map(element => ({ element, rect: element.getBoundingClientRect() }))
            .filter(({ rect }) => rect.bottom > from.top && rect.top < from.bottom && (rect.left + rect.width / 2 - centerX) * forward > 2)
            .sort((a, b) => Math.abs(a.rect.left + a.rect.width / 2 - centerX) - Math.abs(b.rect.left + b.rect.width / 2 - centerX));
        if (peers.length) return focus(peers[0].element);
    }
    const pane = active.closest('.channel-list, .details, .keywords');
    if (scope === root && horizontal) {
        if (direction === GamepadButton.DIR_RIGHT && pane?.matches('.channel-list'))
            return focus(available(root.querySelector('.details')!)[0]);
        if (direction === GamepadButton.DIR_LEFT && pane?.matches('.details'))
            return focus(root.querySelector<HTMLElement>('.channel-row.selected button, .channel-row.selected [role="button"]') || undefined);
    }
    const candidates = available(scope).filter(element => element !== active && !element.contains(active) &&
        (!vertical || !pane || pane.contains(element) || !!element.closest('.editor-header, .editor-footer')))
        .map(element => {
            const rect = element.getBoundingClientRect();
            const dx = rect.left + rect.width / 2 - centerX, dy = rect.top + rect.height / 2 - centerY;
            const advance = (horizontal ? dx : dy) * forward;
            const cross = Math.abs(horizontal ? dy : dx);
            return { element, advance, score: advance + cross * 3 };
        }).filter(candidate => candidate.advance > 2).sort((a, b) => a.score - b.score);
    return focus(candidates[0]?.element);
}
