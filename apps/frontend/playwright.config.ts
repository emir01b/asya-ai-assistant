import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "e2e",
  timeout: 90000,
  workers: 1,
  use: {
    baseURL: process.env.VOICE_TEST_BASE_URL || "http://127.0.0.1:5173",
    channel: "msedge",
    headless: true,
    viewport: { width: 1440, height: 1000 },
    screenshot: "only-on-failure",
    ignoreHTTPSErrors: process.env.VOICE_TEST_ALLOW_LOCAL_CERT === "1",
  },
  reporter: [
    ["list"],
    ["json", { outputFile: "../../docs/browser-results.json" }],
  ],
});
