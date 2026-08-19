import { defineConfig, devices } from "@playwright/test";

// planning/PLAN.md Section 12: E2E scenarios exercise a single shared app
// instance/database in a realistic user flow (buy before sell, etc.), so
// specs run serially, in file order, against one worker rather than
// Playwright's default parallel/isolated model.
export default defineConfig({
  testDir: "./specs",
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: "list",
  use: {
    baseURL: process.env.BASE_URL || "http://localhost:8000",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
