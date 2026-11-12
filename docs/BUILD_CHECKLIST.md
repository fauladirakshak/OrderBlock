 # OrderBlock build checklist

Last updated: 2026-11-13

Legend: [x] implemented; [ ] not yet complete; [~] implemented but awaiting verification.

## Phase 1 — Engine foundation and quality

- [x] Confirmed-swing market structure primitives (BOS / CHoCH).
- [x] Baseline order-block and three-candle FVG candidate detection.
- [x] Configurable ICT-inspired sweep + displacement + structure + FVG candidate engine.
- [x] Ten setup-engine tests covering bullish/bearish candidates, sweep timing, displacement, FVG options, profile validation and API validation.
- [x] Four market-data provider/API tests covering deterministic output, timeframe spacing, API metadata and invalid timeframe handling.
- [x] GitHub Actions backend test and frontend build workflows.
- [x] Backend test job passed on the provider/API implementation commit.
- [~] Frontend production build: an earlier run exposed a TypeScript syntax issue; corrected in the latest commit and awaiting the new CI result.

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
- [ ] Connect structure, BOS / CHoCH, order-block, FVG and liquidity-sweep overlays.
- [ ] Add multi-timeframe workspace and higher-timeframe context.
- [ ] Add chart-side analysis panel and explainable setup annotations.
- [ ] Add historical-data caching and persistence.
- [ ] Add live streaming only after provider selection, licensing review and reconnect handling.

## Validation notes

- The synthetic provider is development data only, anchored to a fixed timestamp for repeatable tests. It is not historical market data, a quote, or a tradeable feed.
- No broker connection or order execution is implemented.
- ICT terminology describes an independently implemented research interpretation, not proprietary source-code recovery or a claim of canonical equivalence.
