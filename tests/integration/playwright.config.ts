import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '.', testMatch: '**/*.spec.ts', fullyParallel: false, workers: 1,
  retries: 0, timeout: 45000, expect: { timeout: 8000 },
  outputDir: '../../test-results',
  reporter: [['list'], ['html', { outputFolder: '../../playwright-report', open: 'never' }]],
  use: {
    baseURL: 'http://127.0.0.1:5179', viewport: { width: 900, height: 1000 },
    trace: 'retain-on-failure', screenshot: 'only-on-failure',
    launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH },
  },
  webServer: {
    command: 'node tests/integration/server.mjs', url: 'http://127.0.0.1:5179',
    cwd: process.cwd(), timeout: 30000, reuseExistingServer: !process.env.CI,
    gracefulShutdown: { signal: 'SIGTERM', timeout: 5000 },
  },
});
