import { test, expect } from "@playwright/test";
import { gotoApp, headerStat } from "./helpers";

// planning/PLAN.md Section 12: "AI chat (mocked): send a message, receive a
// response, trade execution appears inline". Requires LLM_MOCK=true (set by
// test/docker-compose.test.yml) so the "buy" keyword deterministically
// triggers a real trade (planning/PLAN.md Section 9, LLM Mock Mode).
test("mocked chat executes a trade and shows an inline confirmation", async ({ page }) => {
  await gotoApp(page);

  const cashBefore = await headerStat(page, "Cash").innerText();

  await page.getByPlaceholder("Message Financial APP…").fill("please buy AAPL for me");
  await page.getByRole("button", { name: "Send", exact: true }).click();

  await expect(page.getByText("please buy AAPL for me")).toBeVisible();
  await expect(page.getByText(/Mock assistant: buying 1 share of AAPL\./)).toBeVisible();
  await expect(page.getByText(/^✓ buy 1 AAPL$/)).toBeVisible();

  await expect
    .poll(async () => headerStat(page, "Cash").innerText())
    .not.toBe(cashBefore);
});
