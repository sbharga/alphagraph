import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  use: {
    baseURL: "http://127.0.0.1:4173",
    trace: "on-first-retry",
    browserName: "chromium",
    launchOptions: {
      executablePath:
        "/tmp/ms-playwright/chromium-1217/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
    },
  },
  webServer: [
    {
      command:
        "cd .. && export UV_CACHE_DIR=/tmp/uv-cache && uv run --project backend uvicorn alphagraph.app:create_app --factory --host 127.0.0.1 --port 8000",
      port: 8000,
      reuseExistingServer: true,
      timeout: 120000,
    },
    {
      command: "npm run dev -- --host 127.0.0.1 --port 4173",
      port: 4173,
      reuseExistingServer: true,
      timeout: 120000,
    },
  ],
});
