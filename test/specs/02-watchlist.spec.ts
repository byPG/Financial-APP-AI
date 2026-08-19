import { test, expect } from "@playwright/test";
import { gotoApp, watchlistRow } from "./helpers";

// planning/PLAN.md Section 12: "Add and remove a ticker from the watchlist".
test("adds and removes a ticker from the watchlist", async ({ page }) => {
  await gotoApp(page);

  await expect(watchlistRow(page, "PYPL")).toHaveCount(0);

  await page.getByPlaceholder("Add ticker").fill("PYPL");
  await page.getByRole("button", { name: "Add", exact: true }).click();

  await expect(watchlistRow(page, "PYPL")).toBeVisible();

  await page.getByTitle("Remove PYPL").click();

  await expect(watchlistRow(page, "PYPL")).toHaveCount(0);
});
