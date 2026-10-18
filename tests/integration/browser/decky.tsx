import React, { forwardRef } from 'react';

// UI adapter only: production panel and ControllerDebugClient remain untouched.
export const definePlugin = (factory: () => any) => factory;
export const Router = { NavigateToExternalWeb: () => { throw new Error('External navigation prohibited'); } };
export const quickAccessMenuClasses = { Title: 'fixture-title', QuickAccessMenu: 'fixture-qam', Menu: 'fixture-menu' };
export const gamepadContextMenuClasses = {};
export const getGamepadNavigationTrees = () => [];
export const GamepadButton = { OK: 1, CANCEL: 2, DIR_UP: 9, DIR_DOWN: 10 };
export const PanelSection = ({ title, children }: any) => <section><h2>{title}</h2>{children}</section>;
export const PanelSectionRow = ({ children }: any) => <div>{children}</div>;
export const ButtonItem = ({ children, onClick, disabled }: any) => <button disabled={disabled} onClick={onClick}>{children}</button>;
export const ToggleField = ({ label, description, checked, disabled, onChange }: any) => <div><label><input type="checkbox" checked={checked} disabled={disabled} onChange={e => onChange(e.target.checked)} />{label}</label>{description && <div className="toggle-description">{description}</div>}</div>;
export const DropdownItem = ({ label, rgOptions, selectedOption, onChange }: any) => <label>{label}<select value={selectedOption} onChange={e => onChange(rgOptions.find((option: any) => String(option.data) === e.target.value))}>{rgOptions.map((option: any) => <option key={option.data} value={option.data}>{option.label}</option>)}</select></label>;
export const Menu = PanelSection;
export const MenuItem = ButtonItem;
export const showContextMenu = () => {};
const names = ['onButtonDown', 'onButtonUp', 'onOKButton', 'onCancelButton', 'onGamepadDirection', 'onActivate', 'onCancel'];
export const Focusable = forwardRef<HTMLDivElement, any>((props, ref) => {
  const dom = Object.fromEntries(Object.entries(props).filter(([key]) => !names.includes(key)));
  return <div {...dom} ref={(node: any) => {
    if (typeof ref === 'function') ref(node); else if (ref) ref.current = node;
    if (node) node.__fixtureGamepadHandlers = Object.fromEntries(names.map(name => [name, props[name]]));
  }} />;
});

// Dispatch through the same callback props Decky supplies, with real cancelable
// bubbling CustomEvents. This proves React wiring, NOT native navigation.
export function gamepad(kind: string, button: number) {
  const event = new CustomEvent(kind, { bubbles: true, cancelable: true, detail: { button } });
  let node: any = document.activeElement;
  while (node) {
    node.__fixtureGamepadHandlers?.[kind]?.(event);
    if (event.cancelBubble) break;
    node = node.parentElement;
  }
  return { consumed: event.defaultPrevented, activeTag: document.activeElement?.tagName };
}
