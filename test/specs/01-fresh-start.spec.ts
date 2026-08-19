import { test, expect } from "@playwright/test";
import { DEFAULT_TICKERS, gotoApp, headerStat, watchlistRow } from "./helpers";

// planning/PLAN.md Section 12: "Fresh start: default watchlist appears,
// $10k balance shown, prices are streaming". Must run first, against a
// clean database (test/docker-compose.test.yml gives every test run an
// ephemeral db/ with no prior state).
test.describe.serial("fresh start", () => {
  test("shows the default watchlist, $10,000 cash, and a live connection", async ({ page }) => {
    await gotoApp(page);

    await expect(headerStat(page, "Cash")).toHaveText("$10,000.00");
    await expect(headerStat(page, "Portfolio Value")).toHaveText("$10,000.00");
    await expect(headerStat(page, "Unrealized P&L")).toHaveText("$0.00");

    for (const ticker of DEFAULT_TICKERS) {
      await expect(watchlistRow(page, ticker)).toBeVisible();
    }

    await expect(page.getByText("No open positions.")).toBeVisible();
  });

  test("prices stream and update within a few seconds", async ({ page }) => {
    await gotoApp(page);

    const priceCell = watchlistRow(page, "AAPL").locator("td").nth(1);
    const initialPrice = await priceCell.innerText();

    // The simulator ticks ~every 500ms (planning/PLAN.md Section 6); give
    // it a generous window to guarantee at least one visible change.
    await expect
      .poll(async () => priceCell.innerText(), { timeout: 10000, intervals: [500] })
      .not.toBe(initialPrice);
  });
});
