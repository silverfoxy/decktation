import { createServer } from 'vite';
import { spawn } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import { createWriteStream, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const directory = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(directory, '../..');
const token = randomBytes(32).toString('hex');
mkdirSync(path.join(directory, '.artifacts'), { recursive: true });
const log = createWriteStream(path.join(directory, '.artifacts/backend.log'));
const child = spawn(process.env.DECKTATION_TEST_PYTHON || 'python3', [path.join(directory, 'backend.py')], {
  cwd: root, env: { ...process.env, DECKTATION_TEST_TOKEN: token }, stdio: ['ignore', 'pipe', 'pipe'],
});
child.stdout.pipe(log, { end: false });
child.stderr.pipe(log, { end: false });
let vite;
let closing = false;
async function close(code = 0) {
  if (closing) return;
  closing = true;
  await vite?.close();
  if (child.exitCode === null) {
    child.kill('SIGTERM');
    const timeout = setTimeout(() => child.kill('SIGKILL'), 3500);
    await new Promise(resolve => child.once('exit', resolve));
    clearTimeout(timeout);
  }
  log.end();
  process.exitCode = code;
}
process.on('SIGINT', () => close());
process.on('SIGTERM', () => close());
child.on('error', error => { console.error(error); close(1); });
child.on('exit', code => { if (!closing) { console.error(`Python bridge exited ${code}; see tests/integration/.artifacts/backend.log`); close(1); } });
try {
  await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error('Python bridge startup timed out')), 15000);
    child.stdout.on('data', chunk => {
      if (chunk.toString().includes('BACKEND_READY')) { clearTimeout(timeout); resolve(); }
    });
    child.once('exit', code => { clearTimeout(timeout); reject(new Error(`Python exited ${code}`)); });
  });
  vite = await createServer({
    configFile: false,
    root: path.join(directory, 'browser'),
    resolve: { alias: [
      { find: /^decky-frontend-lib$/, replacement: path.join(directory, 'browser/decky.tsx') },
      { find: /^@decky\/api$/, replacement: path.join(directory, 'browser/sdk.ts') },
    ], dedupe: ['react', 'react-dom'] },
    define: { __TEST_TOKEN__: JSON.stringify(token) },
    plugins: [{ name: 'test-session-token', transformIndexHtml: html => html.replace('TEST_TOKEN_PLACEHOLDER', token) }],
    server: {
      host: '127.0.0.1', port: 5179, strictPort: true,
      fs: { allow: [root] }, cors: false,
      proxy: { '/api': { target: 'http://127.0.0.1:5180' } },
    },
  });
  await vite.listen();
  console.log('Fixture browser: http://127.0.0.1:5179 (NOT Steam/Decky)');
} catch (error) {
  console.error(error);
  await close(1);
}
