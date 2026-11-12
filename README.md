# OrderBlock

A browser-based, responsive, multi-market trading research application for price action, market structure, order blocks, liquidity and multi-timeframe analysis. It is designed for desktop and mobile browsers; it is not a native Android/iOS app.

> **Status:** Initial scaffold. Analysis outputs are research observations, not investment advice or execution instructions. Paper validation comes before any live-trading integration.

## Supported market direction

- **Forex:** currency pairs, pip-aware analysis, spreads and Asian/London/New York session context.
- **Crypto:** exchange-specific spot and perpetual futures markets, with optional funding/open-interest/liquidation context when reliable data is available.
- **Equities and indices:** India-first NSE/BSE coverage, with selected international markets planned later.

Order blocks, BOS/CHoCH, FVGs and liquidity concepts can be used across all three asset classes. The core analysis rules can be shared, but data feeds, trading sessions, price precision, fees and validation must be market-specific. A Forex spot feed is not a centralized exchange-volume feed, and crypto data must retain its exchange/contract identity.

## Product direction

- Market structure: confirmed swing highs/lows, break of structure (BOS), change of character (CHoCH)
- Bullish/bearish order-block candidates, mitigation and invalidation
- Fair Value Gaps (FVG), equal highs/lows and liquidity-sweep candidates
- Multi-timeframe context and explainable confluence
- Market-specific sessions, calendars, costs and instrument metadata
- Chart workspace, watchlists, alerts, journal and backtesting

## Architecture

- **Backend:** Python 3.12+, FastAPI, Pydantic
- **Frontend:** React + TypeScript (Vite), delivered as a browser-based web app
- **Storage (planned):** PostgreSQL/TimescaleDB for market history; Redis for cache and event delivery
- **Charts (planned):** TradingView Lightweight Charts
- **Deployment:** Docker Compose for local development; production hosting to be selected after data-provider and compliance review

## Repository layout

```
backend/       API and deterministic market-structure engine
frontend/      Web application
docs/          Product, architecture and strategy specifications
infra/         Local development and deployment configuration
```

## Development status

The repository currently contains the initial product scaffold, API foundation, structure-analysis logic and responsive web UI shell. Market-data ingestion, exchange/provider adapters, persistent storage, interactive chart overlays, authentication and backtesting are subsequent milestones. Do not treat placeholder or sample data as live market data.

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
- Market-data licensing and redistribution rights must be confirmed for each provider and venue.
- Forex, crypto and equity feeds have different market structures; preserve their source, timestamps and instrument metadata.
- Strategy rules must be tested with spread, fees, funding where applicable, slippage, lookahead-bias controls and out-of-sample periods.
- All generated zones and events should retain their source candles and rule explanations.

## License

Project license to be selected before public distribution.
