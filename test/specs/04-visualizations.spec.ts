import { test, expect, type APIRequestContext } from "@playwright/test";
import { gotoApp } from "./helpers";

function panel(page: import("@playwright/test").Page, heading: string) {
  return page.locator("section", { has: page.getByRole("heading", { name: heading, exact: true }) });
}

async function waitForSnapshots(request: APIRequestContext, minCount: number, timeoutMs: number) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const res = await request.get("/api/portfolio/history");
    const body = await res.json();
    if (body.snapshots.length >= minCount) return;
    await new Promise((r) => setTimeout(r, 2000));
  }
  throw new Error(`portfolio_snapshots never reached ${minCount} within ${timeoutMs}ms`);
}

// planning/PLAN.md Section 12: "Portfolio visualization: heatmap renders
// with correct colors, P&L chart has data points". Relies on the AAPL
// position left over by 03-trading.spec.ts. Portfolio snapshots are
// recorded by a ~30s background timer independent of trade events
// (planning/PLAN.md Section 14), so this polls the API directly for at
// least 2 snapshots to exist server-side before loading the page, rather
// than holding the page open and waiting on its own 30s client-side
// refetch on top of that.
test("heatmap renders the open position and the P&L chart has data", async ({ page, request }) => {
  test.setTimeout(90000);
  await waitForSnapshots(request, 2, 75000);

  await gotoApp(page);

  const heatmap = panel(page, "Portfolio Heatmap");
  await expect(heatmap.getByText("No open positions to visualize.")).toHaveCount(0);

  const aaplCell = heatmap.locator("rect");
  await expect(aaplCell.first()).toBeVisible();
  const fill = await aaplCell.first().getAttribute("fill");
  // colorForPnl always returns an hsl(...) string, green (hue 142) for
  // gains or red (hue 0) for losses -- either is a valid "has a real
  // P&L-driven color" signal.
  expect(fill).toMatch(/^hsl\((142|0), /);

  const pnlPanel = panel(page, "P&L");
  await expect(pnlPanel.getByText("Building history…")).toHaveCount(0);
  const pnlLine = pnlPanel.locator("svg path.recharts-line-curve");
  await expect(pnlLine).toBeVisible();
});
