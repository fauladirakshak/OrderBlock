# OrderBlock

A browser-based, responsive, multi-market trading research application for price action, market structure, order blocks, liquidity and multi-timeframe analysis. It is designed for desktop and mobile browsers; it is not a native Android/iOS app.

> **Status:** Active foundation build. The chart currently uses synthetic sample candles for UI interaction only. Analysis outputs are research observations, not investment advice or execution instructions.

## Supported market direction

- **Forex:** currency pairs, pip-aware analysis, spreads and Asian/London/New York session context.
- **Crypto:** exchange-specific spot and perpetual futures markets, with optional funding/open-interest/liquidation context when reliable data is available.
- **Equities and indices:** India-first NSE/BSE coverage, with selected international markets planned later.

Order blocks, BOS/CHoCH, FVGs and liquidity concepts can be used across all three asset classes. The core analysis rules can be shared, but data feeds, trading sessions, price precision, fees and validation must be market-specific. Forex spot is decentralized and does not have a single consolidated global volume feed. Crypto data must retain its exchange and contract identity.

## Implemented foundation

- Interactive market selector for Forex, Crypto and Stocks.
- Instrument and timeframe selectors.
- Interactive Lightweight Charts candlestick workspace with pan, zoom, crosshair and responsive sizing.
- Backend market-data provider interface with deterministic synthetic mode and unauthenticated Binance public Spot klines. Paid market-data adapters are disabled. Historical CSV import accepts user-supplied Forex, crypto and equity OHLCV datasets with timezone normalization and strict timestamp/OHLC validation.
- Backend instrument catalogue at `GET /api/v1/markets`, including venue ID, contract type, session model, IANA timezone, tick size and price precision.
- Deterministic confirmed swing, BOS and CHoCH engine.
- Explainable baseline order-block and three-candle FVG candidate engine.
- Configurable ICT-inspired confluence candidate engine: liquidity sweep, displacement, structure break and optional FVG.
- Analysis endpoints:
  - `POST /api/v1/analysis/structure`
  - `POST /api/v1/analysis/zones`
  - `POST /api/v1/analysis/setups`
  - `POST /api/v1/backtests/run`
  - `POST /api/v1/backtests/walk-forward`
  - `GET /api/v1/market-data/candles?market=forex&symbol=EUR%2FUSD&timeframe=1H&limit=200`
- Backend unit tests and GitHub Actions quality workflow for backend tests and frontend build.

## Build progress

See [docs/BUILD_CHECKLIST.md](docs/BUILD_CHECKLIST.md) for the tracked Phase 1 and Phase 2 implementation checklist.

## Strategy rules

See [docs/STRATEGY_RULES.md](docs/STRATEGY_RULES.md) for the v0.1 definitions of confirmed pivots, BOS/CHoCH, order-block candidates, mitigation/invalidation and FVGs. A detected order block is a candle-pattern interpretation, not proof of institutional orders.

## Architecture

- **Backend:** Python 3.12+, FastAPI, Pydantic
- **Frontend:** React + TypeScript (Vite), delivered as a browser-based web app
- **Storage (planned):** PostgreSQL/TimescaleDB for market history; Redis for cache and event delivery
- **Charts (current):** Lightweight Charts interactive candlesticks using visibly labelled synthetic sample data; **planned:** licensed historical/live market candles and analysis overlays
- **Deployment:** Docker Compose for local development; production hosting to be selected after data-provider and compliance review

## Repository layout

```
backend/       API and deterministic market-analysis engine
frontend/      Browser web application
docs/          Product scope and versioned strategy definitions
infra/         Local development and deployment configuration
```

## Local setup

Frontend:
```bash
cd frontend
npm install
npm run dev
```

Backend:
```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

## Data and safety

- No broker credentials or live order placement in the initial MVP.
- No live market feed is currently connected; synthetic chart values are not quotes.
- Market-data licensing and redistribution rights must be confirmed for each provider and venue.
- Forex, crypto and equity feeds have different market structures; preserve their source, timestamps and instrument metadata.
- Strategy rules must be tested with spread, fees, funding where applicable, slippage, lookahead-bias controls and out-of-sample periods.
- All generated zones and events should retain their source candles and rule explanations.

## Quality checks

GitHub Actions runs backend tests and the frontend TypeScript/Vite production build on pushes and pull requests to `main`. Check the repository Actions tab for the latest run result.

## License

Project license to be selected before public distribution.


## Automated quality checks

Backend tests:
```bash
cd backend
pip install -e ".[dev]"
pytest -q
```

GitHub Actions runs backend tests and the frontend production build on pushes and pull requests to `main`. The setup-engine tests cover bullish and bearish candidates, sweep confirmation timing, displacement filtering, optional/required FVG behaviour, profile validation and API request/response validation.


### Market-data API and provider configuration

The chart requests candles from `GET /api/v1/market-data/candles`. Supported markets are `forex`, `crypto`, and `stocks`; supported timeframes are `5m`, `15m`, `1H`, `4H`, `1D`, and `1W`. The response includes `provider`, `is_synthetic` and `cache_status` metadata. The current `synthetic-demo` provider is deterministic and uses a fixed timestamp anchor for repeatable UI and test runs; it is not historical market data and must not be used for trading decisions. The provider interface is the extension point for licensed venue-specific data sources.

Set `VITE_API_BASE_URL` in the frontend environment when the API is not running at `http://localhost:8000`.


### Static preview

A GitHub Pages workflow builds a static UI preview using clearly labelled deterministic synthetic candles when the backend is not connected. Enable GitHub Pages in repository Settings → Pages → Build and deployment → Source: GitHub Actions to publish it. The static preview demonstrates the workspace layout and chart interactions only; backend-computed BOS/CHoCH, order-block, FVG and liquidity-sweep overlays require the FastAPI service. Never treat preview candles as market quotes.


### Historical provider configuration

The API selects its provider with server-side environment variables; never place provider credentials in frontend code.

- Default: `ORDERBLOCK_DATA_PROVIDER=synthetic` — deterministic demo candles only.
- Automatic routing: `ORDERBLOCK_DATA_PROVIDER=auto` — Binance Spot for supported Binance Spot instruments. Other markets return an explicit unavailable-source error until a free-source adapter is integrated.
- Binance Spot: `ORDERBLOCK_DATA_PROVIDER=binance`. Uses Binance's public market-data endpoint for Binance Spot contracts only; no trading or private account key is used. It is not a Binance perpetual/futures feed.

A provider configuration or upstream error returns HTTP 503; the API never silently substitutes synthetic candles when a real provider is selected. Each instrument request includes `venue_id` and `contract_type`. The response also returns venue, session, timezone, precision and tick-size metadata. The frontend reads the instrument catalogue and applies price precision to the chart.

Paid market-data subscriptions are not part of the project plan. Binance public market-data endpoints require no private account key, but their terms still govern use. Forex and NSE data will be sourced through free historical datasets, official downloadable reports where permitted, and user-imported CSV files. Public availability does not automatically grant unrestricted redistribution rights.


### Historical candle cache

An opt-in SQLite cache is available for historical provider candles. It is disabled by default and never stores synthetic demo candles. Enable it only after the applicable provider and exchange terms permit local storage and the configured retention period:

```bash
ORDERBLOCK_CACHE_ENABLED=true
ORDERBLOCK_CACHE_DB=./data/orderblock-market-cache.sqlite3
ORDERBLOCK_CACHE_TTL_SECONDS=300
```

Cache keys are scoped by provider, venue, contract type, symbol, timeframe and requested candle count. API responses identify cache status as `disabled`, `hit`, `miss` or `demo`. This cache is a short-lived performance layer, not a canonical historical archive. Long-term storage, backfills, corporate-action adjustments and licensed retention policies remain separate work.


### Free historical CSV import

The API accepts user-supplied OHLCV CSV data at `POST /api/v1/market-data/import/csv`. Required columns: `timestamp` (or `datetime`, `date`, `time`), `open`, `high`, `low`, `close`; `volume` is optional. Supply an IANA timezone for timestamps without an offset. Imported rows are normalized to UTC and rejected if timestamps are duplicated/out of order or OHLC values are invalid. This endpoint does not fetch or claim ownership of third-party data.

Example JSON fields: `symbol`, `market`, `timeframe`, `timezone`, `csv_text`.


### Phase 3 — Historical backtesting

The research backtester is available at `POST /api/v1/backtests/run` and in the frontend **Strategy lab** workspace. The UI imports user-supplied OHLCV CSV files, normalizes timestamps through the import API, configures starting equity, risk per trade, target R multiple and commission/spread/slippage assumptions, then displays metrics and trade records with CSV export. The API accepts a candle array and returns an equity curve, win rate, profit factor, expectancy, average R and maximum drawdown.

Execution assumptions:
- Setups are recalculated using only the candle prefix available at each signal close.
- A signal on candle *i* can enter no earlier than candle *i+1* open.
- One position is allowed at a time; position size is based on the configured percentage of current equity and entry-to-stop distance.
- If stop and target are both touched in one OHLC candle, the stop is assumed first because candle data cannot reveal intrabar ordering.
- Open positions are closed at the final candle close. Commission, spread and slippage are configurable; funding, swaps, borrow, taxes and venue-specific contract multipliers are not modeled.
- Input is capped at 5,000 candles for this correctness-first v0.1 prefix-replay implementation.

The API identifies candles as caller-supplied and does not independently verify their provenance or usage rights. The frontend Strategy lab starts from CSV import rather than the synthetic preview series. This is a historical research simulator only. It does not place orders, promise performance or claim to reproduce proprietary/canonical ICT code. Out-of-sample testing, market-specific costs and data-quality review remain necessary.


### Phase 4 — Walk-forward and out-of-sample validation

The rolling evaluator is available at `POST /api/v1/backtests/walk-forward` and from the Strategy Lab. Configure a chronological training window, test window and step size. Each fold reports the training-period metrics, out-of-sample metrics, a simple buy-and-hold benchmark return and strategy excess return. Aggregate out-of-sample returns are compounded across folds that each start with fresh configured equity.

The test replay retains only candles up to that fold's test end and blocks new entries before the test boundary. Earlier candles remain available for swing/liquidity context. The setup profile is held fixed; this is an evaluation harness, not automated parameter optimization. Overlapping test windows are possible when step size is smaller than test-window size and should be interpreted accordingly.

The buy-and-hold benchmark is close-to-open price return only; it excludes dividends, funding, borrow, taxes and trading costs. A fair strategy comparison requires realistic market-specific costs and validated source data. No result is a guarantee of future performance.
