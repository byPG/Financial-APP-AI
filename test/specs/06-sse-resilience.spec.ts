import { test, expect } from "@playwright/test";

// planning/PLAN.md Section 12: "SSE resilience: disconnect and verify
// reconnection". `context.setOffline()` does not reliably sever an
// already-open SSE connection on localhost in Chromium (offline emulation
// only blocks new connection attempts), so this instead blocks the stream
// endpoint itself before the page ever connects, confirms the app never
// shows "Live" while blocked (and doesn't crash/hang), then unblocks it and
// confirms native EventSource retry (planning/PLAN.md Section 6) brings the
// connection up on its own with no page reload.
test("shows a non-live status while the stream is unavailable, then recovers automatically", async ({
  page,
}) => {
  await page.route("**/api/stream/prices", (route) => route.abort());
  await page.goto("/");

  await expect(page.getByText("Live", { exact: true })).toHaveCount(0);
  // Give it a moment to prove it *stays* down rather than racing a check.
  await page.waitForTimeout(2000);
  await expect(page.getByText("Live", { exact: true })).toHaveCount(0);

  await page.unroute("**/api/stream/prices");

  await expect(page.getByText("Live", { exact: true })).toBeVisible({ timeout: 20000 });
});
