import { GamepadButton, getGamepadNavigationTrees } from "decky-frontend-lib";

const controls = 'button, input, select, textarea, [role="button"]';
function available(root: Element): HTMLElement[] {
    return Array.from(root.querySelectorAll<HTMLElement>(controls)).filter(element =>
        !element.matches(':disabled, [aria-disabled="true"]') && element.getClientRects().length > 0);
}
function focus(element?: HTMLElement) {
    if (!element) return false;
    // Ask Steam to transfer virtual focus, including when the editor is mounted
    // in its separate SP window. DOM focus alone does not move the focus ring.
    const CustomEvent = element.ownerDocument.defaultView?.CustomEvent;
    if (CustomEvent) element.dispatchEvent(new CustomEvent("vgp_requestfocus", { bubbles: true, cancelable: true, detail: { button: GamepadButton.INVALID } }));
    // Steam tracks virtual controller focus separately from DOM focus.
    let nativeNode: any;
    const visit = (node: any) => {
        if (!node?.Element?.contains(element)) return;
        nativeNode = node;
        for (const child of node.GetChildren?.()[0] || []) visit(child);
    };
    try {
        for (const tree of getGamepadNavigationTrees() || []) visit(tree.Root);
        nativeNode?.BTakeFocus?.(0);
    } catch { /* DOM-only environments do not have a Steam navigation tree. */ }
    element.focus({ preventScroll: true });
    element.scrollIntoView({ block: 'nearest', inline: 'nearest' });
    return true;
}

// Steam's default column traversal does not follow these full-screen rows.
export function moveEditorFocus(root: HTMLElement, direction: number, source?: EventTarget | null): boolean {
    const ElementClass = root.ownerDocument.defaultView?.HTMLElement;
    const active = (ElementClass && source instanceof ElementClass && root.contains(source)
        ? source : root.ownerDocument.activeElement) as HTMLElement | null;
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


export function moveEditorKeyFocus(root: HTMLElement, event: KeyboardEvent): boolean {
    const directions: Record<string, number> = { ArrowLeft: GamepadButton.DIR_LEFT, ArrowRight: GamepadButton.DIR_RIGHT, ArrowUp: GamepadButton.DIR_UP, ArrowDown: GamepadButton.DIR_DOWN };
    if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || !(event.key in directions)) return false;
    const target = event.target as HTMLElement;
    // Keep caret movement while editing text. Escape/Tab or the controller can
    // leave the field; physical arrows navigate when a button has focus.
    if (target.matches('input, textarea, select, [contenteditable="true"]')) return false;
    return moveEditorFocus(root, directions[event.key], target);
}
