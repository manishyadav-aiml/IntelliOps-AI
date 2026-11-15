import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import process from 'node:process'

const frontendDir = path.dirname(fileURLToPath(import.meta.url))

const backendLauncher = path.join(
  frontendDir,
  'scripts',
  'start-e2e-backend.mjs',
)

export default defineConfig({
  testDir: './e2e',

  timeout: 90_000,

  retries: 0,

  use: {
    baseURL: 'http://localhost:5173',
    trace: 'retain-on-failure',
  },

  webServer: [
    {
      command: `node "${backendLauncher}"`,
      url: 'http://localhost:8000/api/v1/health',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      cwd: frontendDir,
    },
    {
      command: 'npm.cmd run dev -- --host 127.0.0.1 --port 5173',
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      cwd: frontendDir,
    },
  ],
})