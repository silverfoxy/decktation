import { test as base, expect, APIRequestContext } from '@playwright/test';
import { readFile } from 'node:fs/promises';

export type Harness = {
  control: (command: string, extra?: Record<string, unknown>) => Promise<any>;
  rpc: (method: string, args?: unknown[]) => Promise<any>;
  post: (path: string, data: unknown, headers?: Record<string, string>) => ReturnType<APIRequestContext['post']>;
};
export const test = base.extend<{ harness: Harness }>({
  harness: [async ({ request, page }, use, testInfo) => {
    const html = await (await request.get('/')).text();
    const token = html.match(/name="test-token" content="([a-f0-9]+)"/)?.[1];
    expect(token).toBeTruthy();
    const headers = { 'Content-Type': 'application/json', 'X-Decktation-Test-Token': token! };
    const post: Harness['post'] = (path, data, extra = {}) => request.post(path, { data, headers: { ...headers, ...extra } });
    const control = async (command: string, extra = {}) => {
      const response = await post('/api/control', { command, ...extra });
      expect(response.status()).toBe(200);
      return response.json();
    };
    const rpc = async (method: string, args: unknown[] = []) => {
      const response = await post('/api/rpc', { method, args });
      expect(response.status()).toBe(200);
      return response.json();
    };
    const consoleLog: string[] = [];
    const pageErrors: string[] = [];
    page.on('console', msg => consoleLog.push(`${msg.type()}: ${msg.text()}`));
    page.on('pageerror', error => pageErrors.push(error.stack || error.message));
    await control('reset');
    try {
      await use({ control, rpc, post });
      const inspection = await control('inspect');
      expect(inspection.actor_error).toBeNull();
      expect(inspection.counts.microphone).toBe(0);
      expect(inspection.counts.typing).toBe(0);
      expect(inspection.counts.upload).toBe(testInfo.title.includes('explicit upload') ? 1 : 0);
      expect(pageErrors).toEqual([]);
    } finally {
      if (testInfo.status !== testInfo.expectedStatus) {
        await testInfo.attach('browser-console', { body: consoleLog.join('\n') + '\n' + pageErrors.join('\n'), contentType: 'text/plain' });
        await testInfo.attach('backend-log', { body: await readFile('tests/integration/.artifacts/backend.log'), contentType: 'text/plain' });
        await testInfo.attach('backend-inspection', { body: JSON.stringify(await control('inspect'), null, 2), contentType: 'application/json' });
      }
    }
  }, { auto: true }],
});
export { expect };
