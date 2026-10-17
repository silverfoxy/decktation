import React from 'react';
import { createRoot } from 'react-dom/client';
import pluginFactory from '../../../src/index';
import { gamepad } from './decky';
import { token, rpc } from './sdk';

// This is the production definePlugin callback, not a copied/exported panel.
const plugin = (pluginFactory as unknown as () => {
  content: any; onDismount: () => void;
})();
const root = createRoot(document.getElementById('root')!);
function mount() { root.render(plugin.content); }
mount();
(window as any).fixture = {
  gamepad, rpc,
  unmount: () => root.render(null),
  mount,
  control: async (command: string, extra = {}) => {
    const response = await fetch('/api/control', { method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Decktation-Test-Token': token },
      body: JSON.stringify({ command, ...extra }),
    });
    if (!response.ok) throw new Error(`Fixture control: HTTP ${response.status}`);
    return response.json();
  },
};
window.addEventListener('beforeunload', () => plugin.onDismount());
