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
- Interactive Lightweight Charts candlestick workspace with pan, zoom, crosshair and responsive sizing; current candles remain synthetic demo data.
- Backend market catalogue at `GET /api/v1/markets`.
- Deterministic confirmed swing, BOS and CHoCH engine.
- Explainable baseline order-block and three-candle FVG candidate engine.
- Configurable ICT-inspired confluence candidate engine: liquidity sweep, displacement, structure break and optional FVG.
- Analysis endpoints:
  - `POST /api/v1/analysis/structure`
  - `POST /api/v1/analysis/zones`
  - `POST /api/v1/analysis/setups`
  - `POST /api/v1/analysis/setups`
- Backend unit tests and GitHub Actions quality workflow for backend tests and frontend build.

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
