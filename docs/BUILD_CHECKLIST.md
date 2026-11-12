# OrderBlock build checklist

Last updated: 2026-11-13

Legend: [x] implemented and verified; [~] implemented but awaiting CI/integration verification; [ ] not yet complete.

## Phase 1 — Engine foundation and quality

- [x] Confirmed-swing market structure primitives (BOS / CHoCH).
- [x] Baseline order-block and three-candle FVG candidate detection.
- [x] Configurable ICT-inspired sweep + displacement + structure + FVG candidate engine.
- [x] Ten setup-engine tests covering bullish/bearish candidates, sweep timing, displacement, FVG options, profile validation and API validation.
- [x] Four market-data provider/API tests covering deterministic output, timeframe spacing, API metadata and invalid timeframe handling.
- [x] GitHub Actions backend test and frontend build workflows.
- [x] Backend test job passed on the provider/API implementation commit.
- [x] Frontend production TypeScript/Vite build passed in GitHub Actions.
- [x] Full backend test + frontend build workflow passed on commit 537f3dae000a00828fa0c4e7e018e3a683f69e9d.

## Phase 2 — Trading workspace

- [x] Responsive Lightweight Charts candlestick component with pan, zoom and crosshair.
- [x] Market, instrument and timeframe selectors.
- [x] Backend market-data provider protocol / extension point.
- [x] Deterministic synthetic demo provider with explicit provider and is_synthetic response metadata.
- [x] GET /api/v1/market-data/candles endpoint with market, symbol, timeframe and limit validation.
- [x] Frontend chart fetches candles from the backend API instead of generating them in the browser.
- [x] Loading, API error and provider-status states in the workspace.
- [x] README setup and endpoint documentation.
- [ ] Add provider adapters for licensed historical Forex, crypto and exchange-listed market data.
- [ ] Add venue / contract identifiers and market-specific session, timezone and price-precision metadata to the chart request.
- [x] Add combined backend workspace-analysis endpoint for structure, order-block, FVG and liquidity-sweep annotations.
- [x] Render BOS / CHoCH and liquidity-sweep markers on the chart.
- [x] Render order-block and FVG boundary levels with mitigation / fill status labels.
- [x] Add overlay counts and explanatory status panel.
- [x] Backend overlay endpoint tests passed in GitHub Actions on the overlay integration commit.
- [x] Add a focused regression test proving a sweep is only marked after swing confirmation.
- [x] Full backend test suite, including the focused liquidity-sweep regression test, passed in GitHub Actions on commit cab7bf3527d5c136fd91cbe965d596536adff6f0.
- [x] Frontend chart overlay TypeScript/Vite build passed in GitHub Actions.
- [~] Add independent higher-timeframe structure analysis and bullish / bearish / mixed / neutral alignment endpoint.
- [~] Add multi-timeframe API tests for valid context, timeframe ordering and missing primary series.
- [ ] Integrate multi-timeframe context into the frontend workspace and selected chart.
- [ ] Add shaded rectangular order-block and FVG regions (current chart shows boundary price lines).
- [x] Add chart-side overlay summary and explainable engine notes.
- [x] Add GitHub Pages static preview workflow (synthetic preview candles only; backend overlays require the API).
- [x] Publish the static preview on GitHub Pages; user confirmed successful mobile loading with screenshot.
- [ ] Add historical-data caching and persistence.
- [ ] Add live streaming only after provider selection, licensing review and reconnect handling.

## Validation notes

- The synthetic provider is development data only, anchored to a fixed timestamp for repeatable tests. It is not historical market data, a quote, or a tradeable feed.
- No broker connection or order execution is implemented.
- Multi-timeframe analysis requires separate candle arrays for each timeframe and does not resample or fabricate higher-timeframe candles.
- The latest structure event is a descriptive directional context proxy, not a prediction or trade signal.
- ICT terminology describes an independently implemented research interpretation, not proprietary source-code recovery or a claim of canonical equivalence.
