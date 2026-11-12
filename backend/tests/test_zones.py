from app.engine.structure import Candle
from app.engine.zones import detect_fair_value_gaps


def candle(ts: str, open_: float, high: float, low: float, close: float) -> Candle:
    return Candle(timestamp=ts, open=open_, high=high, low=low, close=close)


def test_detects_bullish_three_candle_fvg() -> None:
    candles = [
        candle("a", 10, 11, 9, 10.5),
        candle("b", 12, 14, 12, 13.5),
        candle("c", 14, 16, 13, 15.5),
        candle("d", 15, 16, 14, 15),
    ]
    gaps = detect_fair_value_gaps(candles)
    assert len(gaps) == 1
    assert gaps[0].direction == "bullish"
    assert gaps[0].top == 13
    assert gaps[0].bottom == 11
    assert not gaps[0].mitigated
