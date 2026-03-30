// @ts-check
const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  timeout: 60000,
  retries: 0,
  use: {
    baseURL: 'file://' + __dirname + '/index.html',
    headless: true,
    viewport: { width: 1440, height: 900 },
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
  ],
});
