import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  use: { baseURL: 'http://127.0.0.1:4173', trace: 'retain-on-failure' },
  webServer: {
    command: 'npm run build && npm run preview -- --host 127.0.0.1',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: !process.env.CI
  },
  projects: [
    {
      name: 'chromium-desktop-vn',
      use: { ...devices['Desktop Chrome'], timezoneId: 'Asia/Ho_Chi_Minh' }
    },
    {
      name: 'chromium-mobile-vn',
      use: { ...devices['Pixel 7'], timezoneId: 'Asia/Ho_Chi_Minh' }
    },
    {
      name: 'chromium-desktop-utc',
      use: { ...devices['Desktop Chrome'], timezoneId: 'UTC' }
    }
  ]
})
