# OrderBlock build checklist

Last updated: 2026-11-14

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
- [x] Binance public Spot klines adapter; no private key or subscription required.
- [x] Enforce zero-subscription provider routing; paid-provider selection is explicitly disabled.
- [x] Add validated user-supplied historical CSV importer/API with UTC normalization, timezone handling, OHLC validation and monotonic timestamp checks; backend CI passed.
- [ ] Integrate free Forex historical datasets (Dukascopy/HistData) after format and usage-terms validation.
- [x] Add offline NSE CM-UDiFF Common Bhavcopy Final ZIP importer/API for selected symbol and series, daily OHLCV conversion and Asia/Kolkata date normalization; CI passed. EOD only; usage terms still require review.
- [x] Add offline HistData Generic ASCII M1 ZIP importer/API, fixed EST (UTC-5, no DST) to UTC conversion, bid OHLCV parsing and strict timestamp/OHLC validation; CI passed. Free download source; redistribution terms not assumed.
- [x] Add venue IDs, contract types, session model, IANA timezone, tick size and price precision to instrument catalogue, candle request and chart formatting.
- [x] Add combined backend workspace-analysis endpoint for structure, order-block, FVG and liquidity-sweep annotations.
- [x] Render BOS / CHoCH and liquidity-sweep markers on the chart.
- [x] Render order-block and FVG boundary levels with mitigation / fill status labels.
- [x] Add overlay counts and explanatory status panel.
- [x] Backend overlay endpoint tests passed in GitHub Actions on the overlay integration commit.
- [x] Add a focused regression test proving a sweep is only marked after swing confirmation.
- [x] Full backend test suite, including the focused liquidity-sweep regression test, passed in GitHub Actions on commit cab7bf3527d5c136fd91cbe965d596536adff6f0.
- [x] Frontend chart overlay TypeScript/Vite build passed in GitHub Actions.
- [x] Add independent higher-timeframe structure analysis and bullish / bearish / mixed / neutral alignment endpoint.
- [x] Add multi-timeframe API tests for valid context, timeframe ordering and missing primary series (CI verified).
- [x] Integrate multi-timeframe context into the frontend workspace and selected chart; CI verified on commit e7ebfea404c275b7e42a0709c2e40fd1168985a1.
- [x] Add shaded rectangular order-block and FVG regions using a responsive canvas overlay; frontend production build passed on commit 2456991f8acd814b5a34083618e332145a0700b7.
- [x] Add selectable zone inspector with status, price range and engine rule explanation; frontend production build passed on commit 2456991f8acd814b5a34083618e332145a0700b7.
- [x] Add chart-side overlay summary and explainable engine notes.
- [x] Add GitHub Pages static preview workflow (synthetic preview candles only; backend overlays require the API).
- [x] Publish the static preview on GitHub Pages; user confirmed successful mobile loading with screenshot.
- [~] Add opt-in SQLite historical-candle cache with provider/instrument-scoped keys, configurable TTL, expiry cleanup and loader-level cache-hit integration test; awaiting CI verification. Caching stays disabled by default until data-storage rights are confirmed.\n- [ ] Validate cache retention settings against each provider/exchange agreement before enabling in production.
- [ ] Add live streaming only after provider selection, licensing review and reconnect handling.

## Phase 3 — Historical research backtester (v0.1 complete)

- [x] Add deterministic OHLC backtesting engine using the configurable setup-candidate engine; backend CI passed.
- [x] Add prefix-only signal evaluation and next-bar-open entry to avoid signal lookahead.
- [x] Add one-position-at-a-time simulation, OB-edge stop with signal-candle fallback, configurable R-multiple target and risk-based sizing.
- [x] Add configurable commission, spread and slippage; return trade-level costs and net PnL.
- [x] Add conservative stop-first handling when stop and target are both touched in one OHLC candle, plus conservative gap-through-stop handling.
- [x] Add end-of-data position closure, equity curve, win rate, profit factor, expectancy, average R and maximum drawdown.
- [x] Add API endpoint POST /api/v1/backtests/run and regression tests for next-bar entry, intrabar ambiguity, gap handling, costs, end-of-data closure, timezone-aware timestamp validation and API response; backend CI passed.
- [x] Add responsive frontend Strategy lab with user CSV import, risk/cost configuration, result metrics, trade table and downloadable CSV report; frontend CI passed.
## Phase 4 — Validation and market-specific realism (v0.1 complete; CI passed)

- [x] Add rolling chronological walk-forward folds with isolated out-of-sample entry windows.
- [x] Add per-fold training metrics, out-of-sample metrics, simple buy-and-hold benchmark and excess-return comparison.
- [x] Add Strategy Lab controls for training/test/step windows and fold-by-fold benchmark results.
- [x] Add configurable contract multiplier to position sizing, PnL and commission notional.
- [x] Add prorated crypto funding, Forex swap and short-stock borrow estimates, plus a simplified positive-realized-PnL tax estimate.
- [x] Add regression tests for chronological folds, benchmark output, profile-derived training minimums, evaluation-boundary lookahead protection, contract multipliers, crypto funding, Forex swap, short-stock borrow and tax deductions; backend CI passed.
- [ ] Validate exact venue funding timestamps, broker swap/rollover schedules, stock borrow availability, exchange lot/contract multipliers, and jurisdiction-specific taxes/fees against authoritative sources before using as production assumptions.
- [ ] Add parameter optimization and walk-forward re-optimization only after an overfitting-resistant protocol is specified.

## Validation notes

- The synthetic provider is development data only, anchored to a fixed timestamp for repeatable tests. It is not historical market data, a quote, or a tradeable feed.
- No broker connection or order execution is implemented.
- Multi-timeframe analysis requires separate candle arrays for each timeframe and does not resample or fabricate higher-timeframe candles.
- The latest structure event is a descriptive directional context proxy, not a prediction or trade signal.
- ICT terminology describes an independently implemented research interpretation, not proprietary source-code recovery or a claim of canonical equivalence.


## Provider rollout prerequisites

- [x] Server-side provider selection via ORDERBLOCK_DATA_PROVIDER; auto routes Binance Spot only and fails clearly for markets without a configured free source.
- [x] Paid-provider selection is disabled by the zero-subscription requirement.
- [x] Binance public Spot adapter uses the market-data-only endpoint and rejects non-Binance Spot contracts.
- [x] Normalize provider timestamps to UTC and preserve venue/session metadata in the candle response.
- [x] Provider configuration/upstream errors return HTTP 503; no silent synthetic fallback.
- [ ] Verify source terms and supported symbols for each free Forex/NSE dataset before ingestion or redistribution.
- [ ] Deploy API with no paid market-data secrets; keep any optional broker credentials out of client code.


- Phase 4 CI verification: GitHub Actions run `43510369599` passed both backend tests and frontend production build on commit `74aab2d3e114356e109baa06c472e7b123c3fee1`.


- NSE and HistData importers: GitHub Actions run `43510775203` passed backend tests and frontend production build on commit `7dc4ab075456430655bc81dcd749277bbf43dcdc`.
