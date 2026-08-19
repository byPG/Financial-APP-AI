import { test, expect } from "@playwright/test";
import { gotoApp, headerStat, positionRow } from "./helpers";

// planning/PLAN.md Section 12: "Buy shares: cash decreases, position
// appears, portfolio updates" and "Sell shares: cash increases, position
// updates or disappears". Deliberately leaves a residual AAPL position (buy
// 2, sell 1) so 04-visualizations.spec.ts has a position to render.
test.describe.serial("trading", () => {
  test("buying shares decreases cash and adds a position", async ({ page }) => {
    await gotoApp(page);

    const cashBefore = await headerStat(page, "Cash").innerText();
    expect(cashBefore).toBe("$10,000.00");

    // AAPL is the first default-watchlist ticker, selected by default.
    await page.locator('input[type="number"]').fill("2");
    await page.getByRole("button", { name: "Buy", exact: true }).click();

    await expect(page.getByText(/^Bought 2 AAPL$/)).toBeVisible();
    await expect
      .poll(async () => headerStat(page, "Cash").innerText())
      .not.toBe("$10,000.00");
    await expect(positionRow(page, "AAPL")).toBeVisible();
  });

  test("selling shares increases cash and updates the position", async ({ page }) => {
    await gotoApp(page);

    const cashBeforeSell = await headerStat(page, "Cash").innerText();

    await page.locator('input[type="number"]').fill("1");
    await page.getByRole("button", { name: "Sell", exact: true }).click();

    await expect(page.getByText(/^Sold 1 AAPL$/)).toBeVisible();
    await expect
      .poll(async () => headerStat(page, "Cash").innerText())
      .not.toBe(cashBeforeSell);

    // Position updates (1 share remains) rather than disappearing.
    const qtyCell = positionRow(page, "AAPL").locator("td").nth(1);
    await expect(qtyCell).toHaveText("1");
  });
});
