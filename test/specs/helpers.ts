import { expect, type Page } from "@playwright/test";

export const DEFAULT_TICKERS = [
  "AAPL",
  "GOOGL",
  "MSFT",
  "AMZN",
  "TSLA",
  "NVDA",
  "META",
  "JPM",
  "V",
  "NFLX",
];

/** Header stat block value (Portfolio Value / Cash / Unrealized P&L),
 * matching the label -> value div pair in components/Header.tsx. */
export function headerStat(page: Page, label: string) {
  return page
    .locator("header div.text-right", { hasText: label })
    .locator("div")
    .last();
}

/** The panel (WatchlistPanel/PositionsTable/etc.) whose header reads
 * exactly this label, e.g. "Watchlist" or "Positions". */
function panel(page: Page, heading: string) {
  return page.locator("section", { has: page.getByRole("heading", { name: heading, exact: true }) });
}

/** A table row within `panel` whose first cell is exactly this ticker
 * (avoids substring collisions, e.g. "V" matching "NVDA"). The `has`
 * locator must be rooted at `page` (not at panelLocator) -- Playwright
 * evaluates it relative to each candidate row regardless of how it was
 * built, so prefixing it with the panel's own selector makes it
 * unsatisfiable (a <tr> can never contain a nested <section>). */
function rowIn(page: Page, panelLocator: ReturnType<typeof panel>, ticker: string) {
  return panelLocator.locator("tbody tr", {
    has: page.locator("td", { hasText: new RegExp(`^${ticker}$`) }),
  });
}

export function watchlistRow(page: Page, ticker: string) {
  return rowIn(page, panel(page, "Watchlist"), ticker);
}

export function positionRow(page: Page, ticker: string) {
  return rowIn(page, panel(page, "Positions"), ticker);
}

export async function waitForLiveConnection(page: Page) {
  await expect(page.getByText("Live", { exact: true })).toBeVisible({ timeout: 15000 });
}

export async function gotoApp(page: Page) {
  await page.goto("/");
  await waitForLiveConnection(page);
}
