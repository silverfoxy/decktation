// Read-only, English UI only. No React internals, raw report, settings or text dumps.
(() => {
  const labels = {start: 'Start 30-second capture', stop: 'Stop and review (touch or mouse)'};
  const visible = e => !!e && e.getClientRects().length > 0 && getComputedStyle(e).visibility !== 'hidden';
  const all = [...document.querySelectorAll('body *')];
  const headings = all.filter(e => visible(e) && e.textContent.trim() === 'Controller input debugger' &&
    ![...e.children].some(c => c.textContent.trim() === 'Controller input debugger'));
  if (headings.length !== 1) return {visible: false, reason: 'need exactly one visible debugger heading'};
  let root = headings[0];
  const controlsIn = e => [...e.querySelectorAll('button,[role="button"]')].filter(visible);
  while (root && root !== document.body && !controlsIn(root).some(e => Object.values(labels).includes(e.textContent.trim()))) root = root.parentElement;
  if (!root || root === document.body) return {visible: false, reason: 'debugger controls not scoped'};
  const status = [...root.querySelectorAll('[role="status"]')].filter(visible).map(e => e.textContent).join(' ');
  const phase = status.includes('Recording controller input') ? 'recording' :
    status.includes('Finalizing controller report') ? 'stopping' :
    status.includes('Controller report ready for review') ? 'ready' :
    /Starting controller capture|Waiting for controller listener/.test(status) ? 'starting' : 'idle';
  const number = regex => { const m = status.match(regex); return m ? Number(m[1]) : null; };
  const rect = e => {const r = e.getBoundingClientRect(); return [r.x,r.y,r.width,r.height].map(Math.round);};
  const controls = {};
  for (const [key,label] of Object.entries(labels)) {
    const found = controlsIn(root).filter(e => !e.disabled && e.textContent.trim() === label);
    if (found.length === 1) {const r=found[0].getBoundingClientRect(); controls[key]=[r.x+r.width/2,r.y+r.height/2];}
  }
  const native_focus = [...document.querySelectorAll('.gpfocus')].filter(visible).slice(0,16).map(e => ({
    label: e === root || e.contains(root) ? 'capture-region' : root.contains(e) ?
      Object.entries(labels).find(([,l]) => e.textContent.trim() === l)?.[0] || 'debugger-control' : 'outside-debugger',
    rect: rect(e)
  }));
  return {visible:true,phase,seconds:number(/(\d+)\s*seconds remaining/),events:number(/Events captured\s*:\s*(\d+)/),
    controls,native_focus,focus_oracle: 'Steam .gpfocus; not document.activeElement',
    active_frontend_identity:'inconclusive',active_backend_identity:'inconclusive'};
})()
