import { defineConfig } from '@playwright/test';
import { assertLocalTestOrigin } from './tools/test-origin.mjs';

// Validate during configuration, before starting any server or browser.
const baseURL = assertLocalTestOrigin(process.env.TEST_BASE_URL);

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: true,
  timeout: 15_000,
  reporter: 'list',
  use: {
    baseURL,
    browserName: 'chromium',
    headless: true,
    storageState: { cookies: [], origins: [] },
    serviceWorkers: 'block',
  },
  webServer: {
    // Explicit settings ensure inherited production environment is not consumed.
    command: `.venv/bin/python -c "from tools.serve_preview import create_preview_app; import uvicorn; uvicorn.run(create_preview_app('${baseURL}'), host='127.0.0.1', port=8765)"`,
    url: `${baseURL}/health/live`,
    reuseExistingServer: false,
    timeout: 15_000,
    gracefulShutdown: { signal: 'SIGTERM', timeout: 5_000 },
  },
});
