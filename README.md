# OrderBlock

A research-first market-structure platform focused on price action, order blocks, liquidity and multi-timeframe analysis.

> **Status:** Initial scaffold. Signals are educational/research outputs, not investment advice or execution instructions. Paper validation comes before any live-trading integration.

## Product direction

- Market structure: swing highs/lows, break of structure (BOS), and change of character (CHoCH)
- Bullish/bearish order-block candidates
- Fair value gaps (FVG) and liquidity-sweep candidates
- Multi-timeframe context and explainable confluence
- Chart workspace, watchlists, alerts, journal and backtesting
- India-first market configuration, with room for international markets

## Architecture

- **Backend:** Python 3.12+, FastAPI, Pydantic
- **Frontend:** React + TypeScript (Vite)
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

This first commit establishes the product boundary and architecture. Market-data ingestion, exchange/provider adapters, persistence, chart UI, authentication, and backtesting are subsequent milestones. Do not treat placeholder or sample data as live market data.

## Local setup

Backend:
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Frontend setup will be documented when the UI scaffold is added.

## Data and safety

- No broker credentials or live order placement in the initial MVP.
- Market-data licensing and redistribution rights must be confirmed for the chosen provider.
- Strategy rules must be tested with fees, slippage, survivorship bias controls and out-of-sample periods.
- All generated zones and events should retain their source candles and rule explanations.

## License

Project license to be selected before public distribution.
