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


### Market-specific cost assumptions (research estimates)

The backtest request and Strategy Lab expose a contract multiplier plus optional crypto funding (basis points per eight hours), Forex swap (basis points per day), short-stock borrow (basis points per day) and a simplified tax estimate on positive realized PnL. Contract multipliers are included in risk sizing, gross PnL and commission notional. Holding costs are prorated by elapsed holding time; stock borrow is charged only to short positions. The selected market category controls which holding-cost field is applied.

These are user-entered estimates, not automatically sourced exchange/broker schedules. Funding timestamps, triple-swap days, long/short swap direction, financing credits, exchange-specific lot sizes, taxes, GST/stamp duty, corporate actions and exact contract specifications still require instrument- and jurisdiction-specific validation. Set unverified assumptions to zero rather than treating defaults as official rates.


### NSE cash-market EOD import

The Strategy Lab accepts an official NSE **CM-UDiFF Common Bhavcopy Final** ZIP for the Stocks market. Choose the requested symbol and upload the downloaded ZIP; the importer reads the UDiFF CSV inside it, filters by symbol and series (default `EQ`), maps open/high/low/close and traded volume, and emits daily candles labelled by trading date in Asia/Kolkata. The API endpoint is `POST /api/v1/market-data/import/nse-udiff`.

This is daily end-of-day data only; it does not create intraday bars. NSE discontinued its older CM Bhavcopy CSV in favour of the CM-UDiFF Common Bhavcopy Final from 8 July 2024. Download reports from the [official NSE All Reports page](https://www.nseindia.com/all-reports). The importer works on a file the user has downloaded; it does not automate website access or bypass controls. Check NSE's current terms and your permitted use before storing, redistributing or commercializing the data.


### HistData Forex M1 import

The Strategy Lab accepts a user-downloaded HistData Generic ASCII M1 ZIP for Forex. It reads the six-column, headerless, semicolon-separated format, validates OHLC and timestamps, and converts the source's fixed EST (UTC-5, no daylight-saving adjustment) timestamps to UTC. The output is labelled `1m`; the source bars are bid OHLC and the published volume field may be zero. The API endpoint is `POST /api/v1/market-data/import/histdata-forex`.

HistData describes these historical files as free downloads and documents the file format/timezone. Start from the [HistData free Forex download page](https://www.histdata.com/download-free-forex-historical-data/) and choose Generic ASCII M1 for the selected pair. It also states that the data is supplied without warranty or certification. This is a user-uploaded offline import, not an automated scraper. Check the source's current download terms and do not assume redistribution or commercial reuse rights.


### Dukascopy BI5 Forex archive import

Strategy Lab supports user-supplied Dukascopy classic hourly `.bi5` archives through `POST /api/v1/market-data/import/dukascopy-bi5`. The ZIP must preserve the hourly datafeed folder structure `SYMBOL/YYYY/MM0/DD/HHh_ticks.bi5` (month is zero-indexed). The importer decodes 20-byte big-endian tick records, validates timestamps and ask/bid values, and aggregates bid ticks to 1m, 5m, 15m, 1H, 4H or 1D OHLCV bars. The instrument price divisor is required and must be independently verified; it is never guessed. Ask prices are checked but the Candle model retains bid-side OHLC and combined reported tick volume only; configure spread costs separately in the backtester.

The importer is offline: it does not scrape or automatically download Dukascopy data. Dukascopy's published terms limit downloads to personal, non-commercial use unless a written agreement says otherwise, and restrict redistribution/database use. Do not use this source in a commercial deployment, distribute the resulting dataset, or make it available to other users without obtaining the required written permissions. Review the current [Dukascopy terms](https://www.dukascopy.com/europe/english/legal-pages/terms-of-use/) before use. The binary layout is based on the documented [Dukascopy historical data export format](https://wiki.dukascopy.com/en/development/data-export).


### Timezone-aware market-session context

The workspace calls `POST /api/v1/analysis/sessions` for the selected instrument. Forex uses broad Asia (Tokyo), London and New York regional windows with IANA timezone/DST handling and overlapping session summaries. NSE-listed instruments use the configured regular session (09:15–15:30 Asia/Kolkata). Crypto is grouped into UTC calendar-day buckets. Each available bucket reports OHLC range, range percentage, volume and candle count.

These are descriptive session windows, not canonical ICT killzones, trade signals or a complete exchange calendar. NSE holidays, special sessions and early closes are not inferred; session highs/lows are only as complete as the candles supplied.


### Liquidity reference levels

The workspace also calls `POST /api/v1/analysis/liquidity-references` to calculate previous available day/week highs and lows plus equal-high/equal-low clusters from confirmed swing pivots. The instrument's IANA timezone and tick size are supplied from the catalogue. Equal-swing tolerance is expressed in ticks; sweeps require a wick beyond the level and a close back inside after the level's confirmation index. Previous-period levels become eligible only after the source period's final supplied candle.

This is a descriptive reference map, not proof of resting orders or a trade signal. The current implementation selects the previous available candle period in the supplied data; incomplete datasets, missing holidays, corporate actions and partial sessions can distort levels. It does not yet include an official holiday calendar or futures-specific rollover/continuous-contract adjustments.


### Premium / discount dealing range

`POST /api/v1/analysis/dealing-range` selects the latest confirmed swing high and swing low that were eligible before the final candle, calculates the 50% equilibrium, and classifies the latest close as premium, discount, equilibrium, above-range or below-range. The configurable equilibrium band is centered on 50%. The chart displays range high, equilibrium and range low, and the workspace reports the current position within the range.

This is geometric context only. It does not predict reversal, define a trade entry, or claim canonical ICT dealing-range equivalence. The range can be unavailable until both confirmed swing sides exist; incomplete history can change the selected swing pair.


### Higher-timeframe dealing-range context

The workspace calls `POST /api/v1/analysis/higher-timeframe-ranges` to calculate separate premium/discount dealing ranges from independently fetched higher-timeframe candles (for example, 1H and 4H context on a 15m chart). The endpoint validates unique timeframe ordering, timezone-aware strictly increasing timestamps, and rejects context candles timestamped after the primary chart's latest candle. It reuses the confirmed-swing eligibility rules from the single-timeframe range engine.

The service does not resample or fabricate higher-timeframe candles. Callers must provide genuinely completed higher-timeframe candles; the API cannot independently prove that an upstream candle is closed. Results are geometric research context, not forecasts or trade signals.


### User-configurable session windows

The existing `POST /api/v1/analysis/sessions` endpoint accepts an optional `custom_windows` array. Each entry defines a unique name, IANA timezone, start and end clock time (for example, `{"name":"London Open Study","timezone":"Europe/London","start":"08:00","end":"10:00"}`). Custom windows are added alongside the market's broad default sessions, with DST handled by the selected IANA timezone. A maximum of eight custom windows is accepted per request.

These are user-defined study windows only. They are not labelled as canonical ICT killzones, and the backend does not prescribe or validate a proprietary killzone schedule.


The workspace exposes a one-window editor in the Session Context panel. Enter a name, IANA timezone and local start/end times, then apply the window to the currently loaded candle history. The controls are session-only and are not persisted between reloads yet.


Available higher-timeframe ranges are also drawn on the active chart as labelled high, 50% equilibrium and low price lines. The line labels retain their source timeframe; the workspace limits chart rendering to the first four available higher-timeframe contexts to avoid excessive clutter.


### Higher-timeframe order blocks and fair value gaps

The workspace calls `POST /api/v1/analysis/higher-timeframe-zones` to calculate order-block and three-candle FVG candidates independently on each supplied higher timeframe. Results are shown grouped by source timeframe, including each zone's price boundaries and mitigation/invalidation/fill status.

The endpoint requires separate higher-timeframe candle arrays, enforces timeframe ordering and chronological timezone-aware timestamps, and rejects future-dated context. It does not resample lower-timeframe candles. Zone status is evaluated only within its own source timeframe; these patterns are descriptive rule-based observations, not proof of institutional orders or trade signals.


### Setup sequence refinement

The setup candidate engine now constrains its optional order-block candle to the interval strictly after the qualifying liquidity sweep and before the displacement/structure-break candle. If no opposing candle exists in that sequence, the candidate carries no order-block zone and the backtester uses its documented signal-candle stop fallback. This avoids assigning a pre-sweep opposing candle as the post-sweep order-block component.


The chart also renders a deliberately limited selection of recent higher-timeframe OB/FVG boundaries as labelled horizontal price lines. The detailed panel retains the grouped source-timeframe list; the chart caps this overlay at eight zones to limit visual clutter.


The higher-timeframe zone panel includes independent chart visibility toggles for OBs and FVGs and timeframe filters for 1H, 4H, 1D and 1W. These filters affect chart price lines only; the underlying analysis and detailed zone list remain available.


Custom session names are checked against the market's built-in session names as well as against other custom names. This prevents a user-defined timezone/window from silently shadowing a built-in session label and producing ambiguous timezone attribution in the session summaries.


The original multi-timeframe structure endpoint also validates timezone-aware strictly increasing candle timestamps per series and rejects any higher-timeframe series whose latest candle extends beyond the primary chart's latest timestamp. This guards direct API callers as well as the frontend against future-context leakage.


The Binance Spot adapter now drops klines whose exchange-provided close timestamp has not yet passed. This keeps the market-data API's Binance candle series closed-bar-only for research analysis. The filter is covered by a regression test that supplies one completed and one still-forming kline.


Walk-forward evaluation requires `step_bars >= test_window_bars`. This prevents overlapping out-of-sample folds from double-counting the same market bars in the compounded aggregate return. Fold-level returns and benchmarks remain reported separately.
