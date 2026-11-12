# OrderBlock — MVP Product Scope

## Product vision
Build a multi-market, browser-based trading research platform for explainable price-action analysis across Forex, cryptocurrency and equities/indices. The same core market-structure concepts can be applied across markets, while instrument metadata, sessions, costs and data adapters remain market-specific.

## Supported markets

### Forex
- Major and selected minor currency pairs first (for example EUR/USD, GBP/USD and USD/JPY).
- Pip-aware price precision, bid/ask spread and swap/rollover metadata where supplied.
- Configurable Asian, London and New York sessions, including daylight-saving changes.
- Session highs/lows, previous-day/week levels and liquidity analysis.
- Spot FX data is fragmented across liquidity providers; identify the actual feed/provider and do not imply a single consolidated global volume feed.

### Cryptocurrency
- Spot and perpetual futures as distinct instrument types.
- Exchange-specific symbols and candles; never silently merge prices or volumes from different venues.
- 24/7 calendar, exchange timezone and maintenance/outage metadata.
- Optional funding rate, open interest, liquidation and basis overlays when a licensed/reliable provider supplies them.
- Funding, leverage and liquidation data must be labelled with venue, contract and timestamp.

### Equities and indices
- India-first NSE/BSE coverage, followed by selected international exchanges.
- Exchange calendars, holidays, sessions, auctions, price bands and corporate-action adjustments.
- Distinguish cash equities, index values and exchange-traded derivatives.
- Confirm market-data licensing and redistribution permissions before launch.

## Shared strategy engine
The following concepts are market-agnostic at the rule level, but must be calibrated and validated for each market and timeframe:
- Confirmed swing highs/lows and market structure.
- Break of Structure (BOS) and Change of Character (CHoCH).
- Bullish/bearish order-block candidates, mitigation and invalidation.
- Fair Value Gaps (FVG) and consequent encroachment.
- Equal highs/lows, liquidity pools and sweep candidates.
- Premium/discount ranges, dealing ranges and previous session/day/week levels.
- Multi-timeframe context and confluence scoring with visible component explanations.

Every strategy rule must have a version, explicit parameters, source candles and a reproducible explanation. Avoid implying that an order block is a verified institutional order: it is a price-action interpretation inferred from candles.

## Primary workflow
1. Select market category, venue/provider, instrument and timeframe.
2. Load candles with source, timestamp, timezone and data-quality status.
3. Inspect structure, order-block candidates, FVGs and liquidity context.
4. Compare higher-timeframe context with the execution timeframe.
5. Save an annotated setup to a journal or watchlist.
6. Replay/backtest the exact versioned rules with realistic spread, fees, funding, slippage and market-specific assumptions.

## MVP milestones

### M0 — Foundation
- Repository structure, API health endpoint and deterministic structure engine.
- Product and architecture documentation.

### M1 — Multi-market data and chart
- Market/instrument model with asset class, venue, symbol, tick size, price precision and timezone.
- Provider adapter interface; historical OHLCV ingestion and data provenance.
- Forex session calendar and pip/spread metadata.
- Crypto exchange-specific spot/perpetual instruments and 24/7 calendar.
- Equity exchange calendars and session handling.
- Interactive candlestick chart with overlays; demo data visibly labelled as sample.

### M2 — Price-action engine
- Confirmed swing points and BOS/CHoCH.
- Explicit order-block candidate rules, mitigation and invalidation.
- Three-candle FVG detection.
- Equal-high/low and liquidity-sweep candidates.
- Multi-timeframe context and explanations.
- Per-market/timeframe parameter profiles; shared rules with market-specific validation.

### M3 — Research workflow
- Watchlists, saved layouts and trade journal.
- Historical replay and backtesting.
- Forex spread/pip and rollover cost modelling.
- Crypto maker/taker fees, funding and contract specifications where applicable.
- Equity brokerage, taxes/charges and slippage configuration where applicable.
- Out-of-sample evaluation, robustness checks and exportable reports.

### M4 — Accounts and release
- Authentication, subscription entitlements and audit logs.
- Monitoring, backups, rate limits and security review.
- Market-data licensing and legal review before commercial launch.

## Non-goals for the first release
- Broker integration or live order execution.
- Guaranteed-return language or personalized investment advice.
- Unlicensed redistribution of exchange, broker or vendor market data.
- Treating Forex tick volume as centralized exchange volume.
- Combining crypto venue data into a synthetic candle without explicit methodology and labelling.

## Product principles
- Explain every event with the candles and rule version that produced it.
- Distinguish confirmed observations from provisional candidates.
- Never silently fill missing candles or relabel exchange timestamps.
- Keep sample data visibly marked as sample data.
- Avoid lookahead bias: pivots and zones become available only when their confirmation rules permit.
- Backtests must model costs and disclose assumptions; historical performance does not guarantee future results.
