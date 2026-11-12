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


def test_swing_requires_right_side_confirmation_before_it_can_break() -> None:
    prefix = [
        candle("t0", 9, 10, 8, 9),
        candle("t1", 10, 12, 9, 11),
        candle("t2", 9, 11, 7, 8),
    ]
    prefix_result = detect_structure(prefix, pivot=1)
    assert prefix_result.swing_highs[0]["confirmation_index"] == 2
    assert not prefix_result.events

    complete = prefix + [candle("t3", 11, 13, 10, 12.5)]
    complete_result = detect_structure(complete, pivot=1)
    assert any(event.candle_index == 3 and event.direction == "bullish"
               for event in complete_result.events)
