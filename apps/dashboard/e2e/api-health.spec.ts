import { test, expect } from "@playwright/test";

const API = process.env.PLAYWRIGHT_API_URL || "http://localhost:8000";

test.describe("API health", () => {
  test("gateway health endpoint", async ({ request }) => {
    test.skip(!process.env.PLAYWRIGHT_API_URL, "Set PLAYWRIGHT_API_URL for full stack E2E");
    const resp = await request.get(`${API}/health`);
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body.status).toBe("ok");
  });
});
