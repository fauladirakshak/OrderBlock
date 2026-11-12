# OrderBlock — MVP Product Scope

## User problem
Give discretionary traders a clear, explainable view of market structure and liquidity context without opaque, unvalidated buy/sell calls.

## Primary workflow
1. Select a market, instrument and timeframe.
2. Load candles from an explicitly identified data provider.
3. Inspect swing points, BOS/CHoCH, order-block candidates, FVGs and liquidity levels.
4. Compare higher-timeframe context with the execution timeframe.
5. Save an annotated setup to a journal.
6. Replay/backtest the exact rules with fees and slippage included.

## MVP milestones

### M0 — Foundation
- Repository structure, API health endpoint and deterministic structure engine.
- Product and architecture documentation.

### M1 — Data and chart
- Provider abstraction and historical OHLCV ingestion.
- Data provenance, exchange timezone and market-session handling.
- Interactive candlestick chart with overlays.

### M2 — Price-action engine
- Confirmed swing points and BOS/CHoCH.
- Explicit order-block candidate rules and invalidation.
- Three-candle FVG detection.
- Equal-high/low and liquidity-sweep candidates.
- Multi-timeframe context and explanations.

### M3 — Research workflow
- Watchlists, saved layouts and trade journal.
- Historical replay and backtesting.
- Fees, slippage, out-of-sample evaluation and exportable reports.

### M4 — Accounts and release
- Authentication, subscription entitlements and audit logs.
- Monitoring, backups, rate limits and security review.
- Market-data licensing and legal review before commercial launch.

## Non-goals for the first release
- Broker integration or live order execution.
- Guaranteed-return language or personalized investment advice.
- Unlicensed redistribution of exchange or vendor market data.

## Product principles
- Explain every event with the candles and rule that produced it.
- Distinguish confirmed observations from provisional candidates.
- Never silently fill missing candles or relabel exchange timestamps.
- Keep sample data visibly marked as sample data.
