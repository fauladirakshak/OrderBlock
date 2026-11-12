# ICT-inspired strategy research rules

**Status:** research specification in progress. The currently implemented detector is a basic price-action baseline, not a complete ICT strategy or a claim to reproduce a proprietary indicator.

## Research stance

OrderBlock uses publicly described ICT concepts as a methodology reference. It does not claim to recover private source code, undisclosed algorithms, or the exact internal rules of any paid indicator. The product will implement independently written, deterministic rules and retain the evidence behind every event.

ICT terminology is not always used identically across lessons, time periods, traders, and public scripts. Where definitions vary, OrderBlock will expose named rule profiles and parameters rather than presenting one interpretation as canonical.

## Analysis sequence

A candidate setup should be represented as a linked sequence, not a collection of unrelated chart labels:

1. **Context:** market, instrument, timeframe, session, higher-timeframe dealing range and directional context.
2. **Draw on liquidity:** relevant external or internal liquidity reference (prior day/week highs/lows, session extremes, confirmed swing points, relative equal highs/lows).
3. **Liquidity event:** a sweep/raid through a previously confirmed level, with configurable wick-penetration and close-back criteria.
4. **Displacement:** directional expansion measured against recent candle ranges/ATR and/or body size; optionally require an FVG.
5. **Structure confirmation:** close-based MSS or BOS through a confirmed, eligible swing. Wick-only breaks are recorded separately.
6. **PD array:** candidate order block, fair value gap, breaker, mitigation block, or other supported array, linked to the displacement and structure event.
7. **Retracement:** price returns to a selected zone; record first touch, partial mitigation, consequent encroachment (50%), and full fill separately.
8. **Trade hypothesis:** entry model, structural invalidation, target liquidity, risk/reward and market costs. This is a research simulation, not an order.
9. **Outcome:** forward price path with timestamps and costs, including unresolved/expired setups.

A liquidity sweep alone is not an entry signal. An order-block candle alone is not a validated setup.

## Versioned implementation baseline

### Market structure (baseline v0.2)

- A swing high/low is a strict local extreme over pivot candles on both sides.
- A pivot at index p is confirmed at p + pivot.
- It is eligible for a break only on a later candle (current_index > confirmation_index); the confirmation candle cannot simultaneously break that pivot.
- BOS/CHoCH are currently close-based breaks of the latest eligible unbroken swing, with the first observed break labelled BOS and a break against the current direction labelled CHoCH.
- This is a deliberately simple structural baseline. A later ICT profile must distinguish MSS from continuation BOS and identify the protected swing relevant to the prevailing dealing leg.

### Order-block candidates (legacy v0.1 baseline; not yet full ICT qualification)

- For each confirmed close-based BOS/CHoCH, search backward for the nearest opposing candle before the break candle.
- Bullish candidate: nearest down-close candle; bearish candidate: nearest up-close candle.
- Current zone boundaries use the full candle wick range.
- Mitigation is first subsequent range overlap; invalidation is a subsequent close beyond the far boundary.
- This baseline does not yet require a liquidity raid, displacement threshold, FVG, or higher-timeframe alignment. It must not be labelled an ICT-qualified order block until those filters are implemented.

### Fair Value Gap candidates (legacy v0.1 baseline)

For three consecutive candles A, B and C:
- Bullish FVG when A.high < C.low; zone is [A.high, C.low].
- Bearish FVG when A.low > C.high; zone is [C.high, A.low].
- Track first overlap, 50% consequent encroachment, and full fill as distinct lifecycle events in the next version. The current baseline only reports overlap and full fill.

## Rule-profile decisions to implement

| Concept | Configurable choices / required evidence |
|---|---|
| Swing structure | pivot length; strict vs equal-high/low tolerance; confirmation timestamp |
| MSS / BOS | protected swing selection; close vs wick break; continuation vs reversal classification |
| Liquidity pools | equal-high/low tolerance in ticks or ATR; minimum touches; lookback; level source |
| Sweep | penetration threshold; wick beyond + close back inside; reclaim window; sweep timestamp |
| Displacement | body/range threshold; ATR multiple; consecutive expansion bars; optional FVG requirement |
| Order-block bounds | full wick; body; open-to-extreme; custom ICT lesson/profile variant |
| Order-block origin | last opposing candle vs contiguous opposing-candle cluster |
| Qualification | required preceding sweep; structure shift; displacement; optional FVG; HTF context |
| Lifecycle | first touch; 50% mitigation; full mitigation; close-through invalidation; breaker conversion |
| FVG | minimum size; body/wick gap; consequent encroachment; partial/full fill; inverse FVG |
| Context | dealing range; premium/discount; OTE band; prior day/week levels; session ranges |
| Time | exchange-local session calendars; New York time conversion and daylight-saving handling |
| Validation | no lookahead; event confirmation timestamp; source candle IDs; rule version; data provider |

No default profile should silently mix these definitions. Every event stores the profile name, version, parameters, source candles and the first timestamp at which it was knowable.

## Data and validation requirements

- Never use a pivot before its right-side confirmation candles have closed.
- Never use future candles to qualify, rank, or filter an earlier setup.
- Keep spot FX provider-specific; do not describe tick volume as consolidated exchange volume.
- Keep crypto venue, symbol, quote currency, contract type and funding series explicit.
- Respect exchange sessions, holidays, corporate actions and tick sizes for equities.
- Backtests must model spread, fees, slippage, funding/borrow where applicable, and avoid survivorship and lookahead bias.
- Separate in-sample development, walk-forward validation and untouched out-of-sample evaluation.
- Report sample size, expectancy, drawdown, win rate, profit factor, average R, and uncertainty; do not market a strategy on win rate alone.

## Research references

These are secondary explanations and public implementations used for comparison, not authoritative substitutes for primary ICT lessons:

- [ICT 2024 Mentorship lecture notes](https://innercircletrader.net/tutorials/ict-2024/lecture-1/)
- [ICT concepts: order blocks, FVGs and premium/discount](https://www.tmgm.com/en-in/academy/trading-academy/ict-trading)
- [Public ICT order-block/FVG TradingView script](https://www.tradingview.com/script/YmAeBTG0-Simple-ICT-Order-Blocks-and-Fair-Value-Gaps-by-Gowtham-Kannakaje/)
- [Open-source SMC toolkit](https://github.com/btankutt/smc-pine-suite)
- [ICT 2016 study manual](https://ictstudymanuals.com/wp-content/uploads/2023/08/2016%201_1.pdf)

## REA role

morluto/rea is a general reverse-engineering toolkit for authorized inspection of applications, websites, runtime behavior and binaries. It is not a trading-strategy library. Use it only where there is an accessible target and a lawful, authorized inspection path. It does not grant access to private or paid source code, and it is not a reason to bypass authentication, DRM, or licensing controls.
