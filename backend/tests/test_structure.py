from app.engine.structure import Candle, detect_structure


def candle(timestamp: str, open_: float, high: float, low: float, close: float) -> Candle:
    return Candle(timestamp=timestamp, open=open_, high=high, low=low, close=close)


def test_detects_confirmed_swing_and_bullish_break() -> None:
    candles = [
        candle("t0", 9, 10, 8, 9),
        candle("t1", 10, 12, 9, 11),
        candle("t2", 9, 11, 7, 8),
        candle("t3", 11, 13, 10, 12.5),
        candle("t4", 12, 14, 11, 13.5),
    ]

    result = detect_structure(candles, pivot=1)

    assert any(point["index"] == 1 and point["price"] == 12 for point in result.swing_highs)
    assert any(event.kind == "BOS" and event.direction == "bullish" for event in result.events)


def test_pivot_is_not_usable_on_its_confirmation_bar() -> None:
    candles = [
        candle("t0", 9, 10, 8, 9),
        candle("t1", 10, 12, 9, 11),
        candle("t2", 12, 13, 11, 12.5),
        candle("t3", 12.2, 13.2, 12, 12.8),
    ]

    result = detect_structure(candles, pivot=1)

    assert result.swing_highs[0]["index"] == 1
    assert result.swing_highs[0]["confirmation_index"] == 2
    assert not any(event.candle_index == 2 for event in result.events)
    assert any(event.candle_index == 3 and event.direction == "bullish" for event in result.events)
