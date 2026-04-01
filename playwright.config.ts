import { defineConfig } from '@playwright/test'

// e2e tests auto-start Flask via webServer below — no running service needed.
// Override with E2E_BASE_URL to test against an already-running instance
// (e.g. E2E_BASE_URL=http://localhost:37491 npx playwright test).
const baseURL = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:5199'

export default defineConfig({
  testDir: './e2e',
  timeout: 30000,
  use: {
    baseURL,
    headless: true,
    viewport: { width: 1400, height: 900 },
  },
  reporter: 'list',
  // Auto-start Flask test server unless E2E_BASE_URL is set (external server)
  ...(!process.env.E2E_BASE_URL && {
    webServer: {
      command: 'uv run python -m engine.api --port 5199 --dev',
      url: 'http://127.0.0.1:5199/health',
      reuseExistingServer: false,
      timeout: 15000,
    },
  }),
})
