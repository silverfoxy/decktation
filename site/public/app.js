const menu = document.querySelector('.mobile-menu');
const navigation = document.getElementById('navigation');
function closeMenu() {
  menu.setAttribute('aria-expanded', 'false');
  navigation.classList.remove('is-open');
}
menu.addEventListener('click', () => {
  const open = menu.getAttribute('aria-expanded') !== 'true';
  menu.setAttribute('aria-expanded', String(open));
  navigation.classList.toggle('is-open', open);
});
navigation.addEventListener('click', (event) => {
  if (event.target.closest('a')) closeMenu();
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && menu.getAttribute('aria-expanded') === 'true') {
    closeMenu();
    menu.focus();
  }
});
const languageSelect = document.getElementById('language-select');
const localeOptions = [...languageSelect.options];
const currentLocale = document.documentElement.lang;
function localeUrl(locale) {
  const option = localeOptions.find(option => option.value === locale);
  const url = new URL(option.dataset.url, window.location.href);
  url.search = window.location.search;
  url.hash = window.location.hash;
  return url;
}
languageSelect.addEventListener('change', () => {
  try { localStorage.setItem('decktation-lang', languageSelect.value); } catch {}
  window.location.assign(localeUrl(languageSelect.value));
});
// Detect on the default entry route; explicit localized links keep their locale.
if (currentLocale === 'en') {
  let saved;
  try { saved = localStorage.getItem('decktation-lang'); } catch {}
  const supported = localeOptions.map(option => option.value);
  const browserLocale = (navigator.language || 'en').toLowerCase().split(/[-_]/)[0];
  const preferred = supported.includes(saved) ? saved : (supported.includes(browserLocale) ? browserLocale : 'en');
  if (preferred !== currentLocale) window.location.replace(localeUrl(preferred));
}
const copyButton = document.getElementById('copy');
const status = document.getElementById('copy-status');
copyButton.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(document.getElementById('installUrl').textContent.trim());
    status.textContent = document.body.dataset.copySuccess;
    const original = copyButton.textContent;
    copyButton.textContent = status.textContent;
    copyButton.disabled = true;
    setTimeout(() => { copyButton.textContent = original; copyButton.disabled = false; }, 1600);
  } catch {
    const url = document.getElementById('installUrl');
    const range = document.createRange();
    range.selectNodeContents(url);
    const selection = window.getSelection();
    selection.removeAllRanges(); selection.addRange(range);
    url.focus();
    status.textContent = document.body.dataset.copyError;
  }
});

// Lightweight staged demo; pauses off-screen, in background tabs, and on request.
document.querySelectorAll('.animated-demo').forEach(demo => {
const typed = demo.querySelector('.demo-typed');
const message = typed?.textContent;
const toggle = demo.querySelector('.demo-toggle');
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const stages = demo.classList.contains('wow-gameplay')
  ? [2800, 1900, 180, 3400]
  : [2800, 650, 180, 3000];
const phases = ['listening', 'transcribing', 'typing', 'done'];
let stage = 0;
let elapsed = 0;
let lastTime = 0;
let frame = 0;
let visible = false;
let paused = false;
function renderDemo() {
  const phase = reducedMotion.matches ? 'done' : phases[stage];
  demo.dataset.phase = phase;
  if (typed) typed.textContent = phase === 'done' || phase === 'typing' ? message : '';
}
function tickDemo(time) {
  elapsed += lastTime ? Math.min(time - lastTime, 100) : 0;
  lastTime = time;
  if (elapsed >= stages[stage]) { stage = (stage + 1) % stages.length; elapsed = 0; }
  renderDemo();
  frame = requestAnimationFrame(tickDemo);
}
function syncDemo() {
  cancelAnimationFrame(frame);
  lastTime = 0;
  const running = visible && !paused && !document.hidden && !reducedMotion.matches;
  demo.classList.toggle('is-paused', !running);
  renderDemo();
  if (running) frame = requestAnimationFrame(tickDemo);
}
toggle?.addEventListener('click', () => {
  paused = !paused;
  toggle.setAttribute('aria-pressed', String(paused));
  toggle.querySelector('i').className = 'fa-solid ' + (paused ? 'fa-play' : 'fa-pause');
  syncDemo();
});
new IntersectionObserver(entries => {
  visible = entries[0].isIntersecting;
  syncDemo();
}, { threshold: 0.15 }).observe(demo);
reducedMotion.addEventListener('change', syncDemo);
document.addEventListener('visibilitychange', syncDemo);
renderDemo();

});

// Installation paths are selected explicitly; never infer whether Decky is installed.
const installSection = document.getElementById('install');
const installChoices = document.getElementById('install-choices');
const installChange = document.getElementById('install-change');
function showInstallPath(path) {
  installChoices.hidden = !!path;
  installChange.hidden = !path;
  installSection.querySelectorAll('.install-path').forEach(panel => {
    panel.hidden = panel.id !== `install-${path}`;
  });
  const heading = path ? document.querySelector(`#install-${path} h3`) : document.getElementById('install-question');
  heading.focus({ preventScroll: true });
  heading.scrollIntoView({ behavior: 'instant', block: 'start' });
}
installSection.querySelectorAll('[data-install-path]').forEach(button => {
  button.addEventListener('click', () => showInstallPath(button.dataset.installPath));
});
installChange.addEventListener('click', () => showInstallPath(''));
document.getElementById('decky-finished').addEventListener('click', () => showInstallPath('existing'));
const transfer = document.getElementById('install-transfer');
const deviceDownload = document.getElementById('install-device-download');
document.getElementById('confirm-steamos').addEventListener('click', () => {
  transfer.hidden = true;
  deviceDownload.hidden = false;
  deviceDownload.querySelector('a').focus({ preventScroll: true });
});
document.getElementById('other-device').addEventListener('click', () => {
  transfer.hidden = false;
  deviceDownload.hidden = true;
  document.getElementById('confirm-steamos').focus({ preventScroll: true });
});

const systemTheme = matchMedia('(prefers-color-scheme: dark)');
let themeChoice = 'auto';
try { themeChoice = localStorage.getItem('decktation-theme') || 'auto'; } catch {}
if (!['auto', 'light', 'dark'].includes(themeChoice)) themeChoice = 'auto';
const themeToggle = document.getElementById('theme-toggle');
const themeModes = ['auto', 'light', 'dark'];
function applyTheme() {
  document.documentElement.dataset.theme = themeChoice === 'auto' ? (systemTheme.matches ? 'dark' : 'light') : themeChoice;
  themeToggle.dataset.mode = themeChoice;
  const current = document.getElementById(`theme-${themeChoice}`).textContent;
  const next = document.getElementById(`theme-${themeModes[(themeModes.indexOf(themeChoice) + 1) % 3]}`).textContent;
  const label = `${document.getElementById('theme-label').textContent}: ${current} → ${next}`;
  document.getElementById('theme-description').textContent = label;
  themeToggle.title = label;
}
themeToggle.addEventListener('click', () => {
  themeChoice = themeModes[(themeModes.indexOf(themeChoice) + 1) % 3];
  try { localStorage.setItem('decktation-theme', themeChoice); } catch {}
  applyTheme();
});
systemTheme.addEventListener('change', applyTheme);
applyTheme();
