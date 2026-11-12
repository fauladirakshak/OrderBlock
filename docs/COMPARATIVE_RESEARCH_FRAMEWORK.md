# OrderBlock comparative reverse-engineering framework

**Target:** Combined — ICT + public TradingView indicators + open-source SMC implementations + other established public methodologies.

**Purpose:** Build an original, explainable, multi-market price-action research engine. This is not an attempt to copy a proprietary indicator or claim access to private source code.

## 1. Source families

| Source family | What we study | How we use it |
|---|---|---|
| ICT methodology | Core concepts, terminology, setup sequences, session and liquidity models | Foundational conceptual reference; document lesson/source and interpretation |
| Public TradingView indicators | Inputs, visible outputs, alert timing, chart behaviour, repainting/confirmation characteristics | Behavioural comparison only where publicly observable and permitted |
| Open-source SMC projects | Code structure, formulas, edge cases, test design, licensing | Learn implementation alternatives; respect each project's license and notices |
| Other public methodologies | Alternative structure, liquidity, zone and confirmation definitions | Identify competing hypotheses and useful variants |
| Market data/research | OHLCV behaviour across FX, crypto and equities | Validate robustness across instruments, sessions and venues |

## 2. Comparison matrix

Every researched concept gets a row in a maintained matrix with:
- Concept and precise operational definition.
- Source family, exact source URL/name, version/date and license where relevant.
- Required input data and timeframe.
- Detection formula / state transition, when public and observable.
- Confirmation time: when the event first becomes knowable.
- Whether it can repaint or be revised as new candles arrive.
- Configurable parameters and default values.
- Known edge cases and market-specific limitations.
- Differences from other sources.
- Proposed OrderBlock rule profile and rationale.
- Golden test fixture and expected event output.

## 3. Concepts to compare

1. Swing highs/lows, internal/external structure, BOS, CHoCH and MSS.
2. Buy-side/sell-side liquidity, equal highs/lows, inducement, sweep/raid and reclaim.
3. Displacement, impulse strength, candle body/range and FVG association.
4. Order blocks: origin candle/cluster, body/wick boundaries, qualification and mitigation.
5. Breaker blocks, mitigation blocks, rejection blocks and inverse FVGs.
6. Fair value gaps, consequent encroachment, partial fill and full fill.
7. Dealing ranges, premium/discount, equilibrium and OTE.
8. Higher-timeframe alignment, session windows, kill zones and previous day/week levels.
9. Entry triggers, stop/invalidation placement, liquidity targets and trade management.
10. Alerts, confirmation delay, repainting, historical plotting and live-bar behaviour.

## 4. Research protocol

For each source:
1. Verify that the source is public and accessible; record its provenance and date.
2. Read its documentation and source code where openly licensed and available.
3. Record visible settings and outputs from representative examples; do not infer hidden internals as facts.
4. Create standardized OHLC fixtures covering clean cases, ambiguous cases and edge cases.
5. Compare event labels, price boundaries, confirmation timestamps and lifecycle transitions.
6. Classify every observed rule as **documented**, **directly observable**, **inferred**, or **unknown**.
7. Record disagreements rather than forcing false consensus.
8. Select an OrderBlock default only when the rationale is documented; retain alternative profiles where meaningful.

## 5. Evidence and decision rules

- No source is automatically ground truth. ICT is the conceptual anchor, not a guarantee of profitable signals.
- Public scripts are independent implementations; do not describe them as official ICT logic unless the author establishes that provenance.
- A visual chart match is not enough: compare exact candle indices, prices, event timestamps and state changes.
- Do not claim non-repainting until tested on bar-by-bar data, including reload/replay behaviour.
- Do not use future candles to make an earlier signal appear valid.
- Preserve attribution and license notices when code reuse is permitted. Prefer independent implementations of public concepts.
- Do not bypass logins, DRM, paid access, or technical restrictions to obtain protected material.
- Treat all strategies as hypotheses until evaluated with realistic costs and out-of-sample data.

## 6. OrderBlock architecture outcome

The engine should separate:
- **Data adapters:** venue/provider-specific candles, sessions, symbol metadata and costs.
- **Primitive detectors:** pivots, equal levels, sweeps, displacement and gaps.
- **Structure state:** protected swings, BOS/MSS transitions and trend context.
- **Zone lifecycle:** candidate creation, qualification, first touch, partial mitigation, full fill, invalidation and breaker conversion.
- **Context engine:** dealing ranges, premium/discount, sessions and multi-timeframe alignment.
- **Setup composer:** explicit ordered conditions, configurable confluence and deterministic scoring.
- **Evidence ledger:** source candle IDs, event timestamps, rule profile/version, parameters and explanation.
- **Research harness:** replay, golden fixtures, walk-forward tests and cost-aware backtesting.

## 7. Market-specific controls

- **Forex:** identify the data provider; spot FX has no single consolidated exchange volume. Treat tick volume as provider-specific.
- **Crypto:** keep exchange, symbol, quote asset, spot/perpetual contract and funding/open-interest feeds distinct.
- **Equities/indices:** respect exchange sessions, holidays, corporate actions, tick sizes and instrument-specific trading halts.

## 8. Deliverables

1. Source register with provenance and licensing notes.
2. Concept-by-concept comparison matrix.
3. Versioned OrderBlock rulebook with explicit defaults and alternatives.
4. Golden fixtures and regression tests.
5. Bar-by-bar replay evidence for confirmation and repainting checks.
6. Cost-aware, out-of-sample evaluation report.
7. Product explanations that distinguish detected price patterns from claims about institutional orders.

**Current status:** Framework established. Existing detectors remain preliminary baselines. No full comparative source audit or profitability validation is claimed complete yet.
