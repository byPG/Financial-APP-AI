# PLAN.md Review

Review pass over `planning/PLAN.md` (2026-08-18). Items are grouped by category; numbering is per-category, not global priority.

**Status (2026-08-18): all 26 items below have been resolved and applied to `planning/PLAN.md`.** Each item is marked ✅ with a one-line pointer to the resolution. Four items were genuine open product decisions and were confirmed with the project owner before applying (marked with 🗳️):

- Trade scope: trades are restricted to tickers already on the watchlist (Section 14, Ticker Scope)
- Watchlist removal: blocked (409) while a position is still open (Section 14, Ticker Scope)
- Position lifecycle at zero quantity: the row is deleted; realized P&L deferred out of v1 scope (Section 14, Trading Rules)
- LLM mock mode: canned responses selected via keyword matching on the user's message (Section 9, LLM Mock Mode)

---

## Inconsistencies & likely bugs

1. **`planning/` vs `docs/` as the agent contract location.** Section 1 says "Agents interact through files in `planning/`," but Section 4's Key Boundaries say "The Architect agent produces `ARCHITECTURE.md`" in `docs/`. Pick one location for the cross-agent contract, or state explicitly that `planning/` is for product spec docs (this file) while `docs/` is for the technical contract.
   ✅ Resolved — Section 1 now states the split explicitly: `planning/` for product/process docs, `docs/` for the technical contract.

2. **`docs/` is referenced but not in the directory tree.** Section 4's directory-structure diagram lists `frontend/`, `backend/`, `planning/`, `scripts/`, `test/`, `db/`, plus root files — but no `docs/`. The very next subsection ("Key Boundaries") then describes `docs/ARCHITECTURE.md` as the definitive contract every agent reads first. Add `docs/` to the tree so it isn't missed by an agent skimming the diagram.
   ✅ Resolved — `docs/ARCHITECTURE.md` added to the Section 4 tree.

3. **Script naming mismatch.** Section 4's tree lists `scripts/start_windows.ps1` / `scripts/stop_windows.ps1`; Section 11 calls the same scripts `scripts/start_pc.ps1` / `scripts/stop_pc.ps1`. Pick one name — this repo already has Windows as the dev environment, so it's worth getting right before the DevOps agent writes them.
   ✅ Resolved — Section 11 now uses `start_windows.ps1` / `stop_windows.ps1`, matching the tree.

4. **Docker persistence mechanism mismatch.** Section 4 describes `db/` as a repo directory bind-mounted into the container (implying `-v $(pwd)/db:/app/db`, with `finally.db` gitignored at that path). Section 11's example command instead uses a named volume (`-v finally-data:/app/db`). These put the SQLite file in two different places from the student's perspective (a file they can see in the repo vs. an opaque Docker-managed volume) — pick one and make the start scripts and directory-structure doc agree.
   ✅ Resolved — Section 11 switched to the bind mount (`-v "$(pwd)/db:/app/db"`), matching Section 4.

5. **"FIFO or average cost" contradicts the schema.** Section 14 leaves cost-basis method open ("FIFO or average cost — Architect decides"), but the `positions` table (Section 7) has a single `avg_cost` column with no per-lot tracking — it can only support average-cost accounting. Drop "FIFO or" from Section 14; the schema already decided this.
   ✅ Resolved — Section 14 now states average-cost accounting only, with the reason (single `avg_cost` column).

---

## Gaps / missing detail

6. **No chat history endpoint.** Section 9 says the backend "loads recent conversation history from the `chat_messages` table" on every turn, but Section 8's API table only lists `POST /api/chat`. Without a `GET /api/chat` (or similar), the frontend can't repopulate the chat panel on page load/refresh — the conversation appears empty until the next message is sent.
   ✅ Resolved — added `GET /api/chat` to Section 8; Section 10's chat panel now references it.

7. **No per-ticker price history storage/endpoint.** Section 2 requires 30-minute sparklines and Section 10 requires a price-over-time chart for the selected ticker, but Section 6's price cache only holds the latest price, previous price, and timestamp — no rolling history. Neither the schema (Section 7) nor the API table (Section 8) says where historical per-ticker prices come from. Needs either an in-memory ring buffer per ticker plus a `GET /api/prices/{ticker}/history` endpoint, or a lightweight `price_history` table — see simplification #16 below for a concrete sampling rate.
   ✅ Resolved — Section 6 adds an in-memory downsampled ring buffer (no new DB table) plus `GET /api/prices/{ticker}/history` in Section 8.

8. **Trades require a price, but the price cache is scoped to the watchlist.** Section 6 says the cache is populated for "the union of all watched tickers" (explicit for Massive; implied for the simulator by Section 15 — "so users can add tickers via the watchlist and still see simulated data"). Section 8/14 never state whether `POST /api/portfolio/trade` is restricted to watchlist tickers. If a user (or the LLM) tries to buy a ticker that was never added to the watchlist, there is no cached price to fill at. Either (a) require the ticker be on the watchlist before it can be traded and return a clear validation error otherwise, or (b) auto-add any traded ticker to the watchlist / have the simulator serve prices for any valid symbol on demand. This needs an explicit rule.
   🗳️ Resolved (product decision, confirmed with owner) — option (a): a ticker must be on the watchlist before it can be traded (Section 14, Ticker Scope; `POST /api/portfolio/trade` returns 400 otherwise). Chosen for simplicity — avoids "price any symbol on demand" logic.

9. **Positions can outlive their watchlist entry.** `DELETE /api/watchlist/{ticker}` removes a ticker from the watchlist, but a position in that ticker isn't mentioned as blocking removal. If the price cache/poller only tracks watched tickers (per #8), removing a ticker the user still holds shares in would freeze that position's price, silently corrupting unrealized P&L and total portfolio value. Either keep polling/simulating prices for any ticker with an open position regardless of watchlist membership, or block watchlist removal while a position is open (and say so).
   🗳️ Resolved (product decision, confirmed with owner) — removal is blocked (409) while a position is open (Section 14, Ticker Scope; `DELETE /api/watchlist/{ticker}` in Section 8). Chosen for simplicity — keeps "price cache covers every held ticker" as a strict invariant, no extra out-of-watchlist tracking needed.

10. **Ticker validity is undefined.** `POST /api/watchlist` and trade execution both need to reject bogus symbols, but nothing defines what makes a ticker "valid" — a format check (e.g., 1–5 uppercase letters), a fixed allow-list, or something else. Since there's no real market-data lookup in simulator mode, this needs an explicit rule so `Add ticker: "ZZZZZ123"` has defined behavior.
    ✅ Resolved — Section 14 (Ticker Scope) defines `^[A-Z]{1,5}$` as the sole validity rule; `POST /api/watchlist` in Section 8 returns 400 otherwise.

11. **Chat "streaming" is in tension with structured output.** Section 9 has the LLM return one structured JSON object (`message`, `trades`, `watchlist_changes`); Sections 2/10 describe the response as streamed "token-by-token." A client generally can't act on partial JSON. Clarify whether "streaming" means (a) the backend waits for the full structured response, then streams just `message` back afterward (a typewriter effect), or (b) something more involved like incremental JSON parsing. See simplification #15 — (a) is far simpler and is almost certainly the intent.
    ✅ Resolved — option (a) adopted; Section 9's new "Transport & Streaming" subsection spells it out, Section 10's chat panel updated to match.

12. **`POST /api/chat` response transport is unspecified.** Section 8 doesn't say whether the "streamed" response is SSE, chunked HTTP, or a single JSON payload animated client-side. The app already has an SSE pattern for prices; state explicitly which transport chat uses so the Architect's contract is unambiguous.
    ✅ Resolved — Section 9's "Transport & Streaming" subsection states it's a single JSON request/response, no SSE/chunking; Section 8's Chat table updated to match.

13. **No realized P&L.** Section 14 defines unrealized P&L per position and total portfolio value, but nothing surfaces realized P&L (gains/losses banked from completed sells) anywhere in the API or UI spec, even though the append-only `trades` table has everything needed to compute it. Worth deciding if this is in scope for v1 or explicitly deferred.
    ✅ Resolved — explicitly deferred out of v1 scope (Section 14, Trading Rules), noted as derivable later from the `trades` table if needed. Keeps the schema/API surface simple for now.

14. **LLM mock mode's determinism strategy is unspecified.** Section 12's E2E scenario "AI chat (mocked): send a message, receive a streamed response, trade execution appears inline" requires the mock to actually produce a trade for at least one test message. Section 9 only says mock mode is "deterministic" — it doesn't say how mock responses are selected (fixed canned response regardless of input? keyword/regex matching on the user's message?). Without this, the Backend Engineer has to invent a mocking strategy the E2E test then has to reverse-engineer.
    🗳️ Resolved (product decision, confirmed with owner) — simple keyword matching on the user's message (e.g. "buy" → canned trade response), documented in Section 9's LLM Mock Mode subsection. Chosen because it's the minimum needed to make the E2E trade scenario deterministic without a real parser.

---

## Process / sub-agent ordering

15. **Phase 2's "Docker builds successfully" gate looks unreachable at that point.** The Execution Order (Section 13) puts the DevOps Engineer in Phase 2, gated on "Docker builds successfully" — but the multi-stage Dockerfile needs `frontend/` (Frontend Engineer, Phase 4) and a working `backend/` uv project (Backend Engineer, Phase 3) to actually build and run. At Phase 2, neither exists yet. Either relax the Phase 2 DevOps gate to something achievable then (e.g., "Dockerfile authored, syntactically valid, scripts idempotent") and move the real "image builds and runs" validation to Phase 5 where it's already planned, or explicitly scaffold minimal placeholder `frontend/` and `backend/` projects before Phase 2 so there's something to build.
    ✅ Resolved — Phase 2's DevOps gate relaxed to "Dockerfile authored and syntactically valid, scripts idempotent"; the real build/run check stays at Phase 5 (Section 13, Execution Order).

16. **Who scaffolds the shared `backend/` project before the Market Data Engineer starts?** The Market Data Engineer (Phase 2) and Backend Engineer (Phase 3) share `backend/` but own different subdirectories, and Section 13 says the Architect "does NOT write application code." If nobody creates `backend/pyproject.toml` and the base project skeleton before Phase 2, the Market Data Engineer has to invent the shared project setup that the Backend Engineer (arriving a phase later) is nominally responsible for — a likely source of rework or boundary friction. Worth having the Architect (or a lightweight scaffolding step) own the empty-but-configured `backend/` and `frontend/` project skeletons as part of its contract deliverable.
    ✅ Resolved — the Architect's responsibilities (Section 13) now explicitly include scaffolding empty-but-configured `backend/pyproject.toml` and `frontend/package.json` skeletons.

---

## Best practices worth calling out explicitly

17. **SQLite concurrency.** The plan has at least three writers hitting the same SQLite file concurrently: trade execution (API request), the periodic portfolio-snapshot background task (~every 30s per Section 14), and chat message persistence — plus the market-data background task if it's ever changed to write through instead of staying in-memory. SQLite's default journal mode serializes writes and can raise "database is locked" under contention. Worth stating explicitly that the backend should enable WAL mode (`PRAGMA journal_mode=WAL`) and keep transactions short, so the Backend Engineer doesn't discover this the hard way during Playwright load.
    ✅ Resolved — new "Concurrency" subsection in Section 7 states the WAL-mode requirement explicitly.

18. **Parameterized queries / input validation reminder.** Not currently addressed anywhere. Given ticker symbols and quantities flow in from both direct API calls and LLM-generated trades, it's worth a one-line note that all SQL is parameterized (no string-built queries) and that ticker/quantity/side are validated server-side even when they originate from the "trusted" LLM structured output — the LLM response is still untrusted input from the backend's perspective.
    ✅ Resolved — Section 9's structured-output schema notes now state the LLM's output is treated as untrusted input and validated server-side like any other request.

19. **Success criteria omit unit tests.** Section 17's success checklist covers Docker startup, UI behavior, and the Playwright E2E suite, but never mentions the pytest/RTL unit test suites that Section 12 spends two full subsections defining. Suggest adding "Backend and frontend unit test suites pass" as its own success criterion so it isn't implicitly optional.
    ✅ Resolved — added as item 7 in Section 17's Success Criteria.

20. **Initial main-chart state is unspecified.** Section 2/10 describe the main chart as populated "when a ticker is clicked" but don't say what (if anything) it shows before the user's first click on a fresh session — worth deciding (e.g., default to the first watchlist ticker) so the Frontend Engineer isn't guessing.
    ✅ Resolved — Section 10 now states the main chart defaults to the first watchlist ticker on initial load.

---

## Simplification opportunities

21. **Resolve #11/#12 with a one-shot-then-typewriter design.** Backend calls the LLM once, waits for the complete structured response, executes any trades/watchlist changes, persists the chat message with its `actions`, then returns the finished `message` text in a single response. The frontend applies a client-side typewriter animation for the "streaming" feel. This avoids writing an incremental JSON parser entirely while still delivering the UX described in Section 2/10.
    ✅ Resolved — adopted verbatim; see Section 9, Transport & Streaming.

22. **Downsample price history instead of storing every tick (addresses #7).** A sparkline doesn't need 500ms-tick resolution — 30 minutes at that cadence is 3,600 points/ticker, expensive to hold and serialize for every watched ticker. Sample roughly one point every 10–15 seconds per ticker instead (~120–180 points for a 30-minute window), whether that lands in an in-memory ring buffer or a `price_history` table.
    ✅ Resolved — adopted verbatim (in-memory ring buffer, ~10-15s sampling); see Section 6, Price History.

23. **Tie `chat_messages.actions` explicitly to the structured-output schema.** Section 7's `actions` column and Section 9's `trades`/`watchlist_changes` arrays are clearly meant to be the same shape, but the doc never says so directly. State that `actions` stores exactly `{trades, watchlist_changes}` from the LLM response (or `null` if neither), so the Backend Engineer doesn't have to invent a shape for it.
    ✅ Resolved — Section 9, How It Works step 7 now states this explicitly.

---

## Minor questions

24. Section 6's Massive API cadence ("Free tier (5 calls/min): poll every 15 seconds") is worth double-checking against Polygon.io/Massive's current free-tier rate limits before implementation — third-party limits change over time and this is easy to get stale.
    ✅ Resolved — Section 6 now flags this figure with a note to confirm current rate limits at implementation time.

25. Section 14 leaves a second "Architect decides" item open: whether a position row is deleted or kept at quantity 0 when fully sold. Fine to leave open, but flag it alongside #5 above so both cost-basis and position-lifecycle decisions get made in the same pass.
    🗳️ Resolved (product decision, confirmed with owner) — the row is deleted at quantity 0 (Section 14, Trading Rules). See also item 13 above (realized P&L deferred).

26. Section 8's `POST /api/watchlist` and `DELETE /api/watchlist/{ticker}` don't specify behavior for duplicate-add (ticker already on the watchlist — the schema has a UNIQUE constraint, so this needs a defined status code, e.g., 200/idempotent vs. 409) or remove-not-found (404 vs. no-op 200). Small, but worth pinning down so frontend error handling isn't guesswork.
    ✅ Resolved — Section 8's Watchlist table now specifies: duplicate-add is idempotent (200), remove-not-found is 404, remove-with-open-position is 409 (see item 9 above).
