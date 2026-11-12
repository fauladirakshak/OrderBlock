# Price-action rule definitions (v0.1)

These are deterministic research heuristics. They are not proof of institutional activity, forecasts, or trade instructions. Rule versions and parameters must be stored with every generated event.

## Market structure
- A swing high/low is confirmed only after the configured number of right-side candles has closed.
- BOS is a close beyond the latest unbroken confirmed swing in the current/initial direction.
- CHoCH is a close beyond the latest unbroken confirmed swing against the previously detected direction.
- The engine must not expose a pivot before its right-side confirmation candles exist.

## Order-block candidate
- For each confirmed close-based BOS or CHoCH, search backward for the nearest opposing candle before the break candle.
- Bullish candidate: nearest candle with close below open before a bullish break.
- Bearish candidate: nearest candle with close above open before a bearish break.
- v0.1 zone boundaries use the full candle wick range (low to high).
- Mitigated means a subsequent candle range overlaps the zone.
- Invalidated means a subsequent candle closes beyond the far boundary: below the bullish zone low or above the bearish zone high.
- Candidate identity is the source candle plus direction; repeated breaks do not duplicate the same candidate.

## Fair Value Gap candidate
For three consecutive candles A, B and C:
- Bullish FVG when A.high < C.low. Zone is [A.high, C.low].
- Bearish FVG when A.low > C.high. Zone is [C.high, A.low].
- Mitigated means a later candle range overlaps the zone.
- Filled means a later candle reaches/passes the far edge of the gap.
- The middle candle timestamp/index identifies the pattern.

## Important limitations
- These rules are intentionally simple v0.1 definitions. Traders use different order-block and FVG conventions; future versions may offer configurable body/wick boundaries, displacement filters, volume filters and invalidation modes.
- A detected zone is a historical candle-pattern candidate, not a verified resting order or guaranteed support/resistance.
- Forex spot volume is generally provider-specific tick volume, not centralized consolidated volume.
- Crypto candles must remain exchange- and contract-specific.
- Backtests must use only information available at the time, include market costs and avoid lookahead bias.
