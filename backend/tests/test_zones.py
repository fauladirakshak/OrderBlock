from app.engine.structure import Candle, detect_structure
from app.engine.zones import detect_fair_value_gaps, detect_order_blocks


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


def test_detects_bearish_three_candle_fvg() -> None:
    candles = [
        candle("a", 16, 17, 15, 16),
        candle("b", 14, 15, 13, 13.5),
        candle("c", 12, 13, 10, 11),
    ]
    gaps = detect_fair_value_gaps(candles)
    assert len(gaps) == 1
    assert gaps[0].direction == "bearish"
    assert gaps[0].top == 15
    assert gaps[0].bottom == 13


def test_order_block_uses_last_opposing_candle_before_bullish_break() -> None:
    candles = [
        candle("t0", 9, 10, 8, 9),
        candle("t1", 10, 12, 9, 11),
        candle("t2", 9, 11, 7, 8),
        candle("t3", 11, 13, 10, 12.5),
        candle("t4", 12, 14, 11, 13.5),
    ]
    structure = detect_structure(candles, pivot=1)
    assert any(event.direction == "bullish" for event in structure.events)
    blocks = detect_order_blocks(candles, pivot=1)
    assert blocks
    assert blocks[0].direction == "bullish"
    assert blocks[0].candle_index == 2
    assert blocks[0].top == 11
    assert blocks[0].bottom == 7
