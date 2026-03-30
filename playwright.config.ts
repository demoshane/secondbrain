import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 30000,
  use: {
    baseURL: 'http://localhost:37491',
    headless: true,
    viewport: { width: 1400, height: 900 },
  },
  reporter: 'list',
})
