from fastapi.testclient import TestClient

from app.engine.higher_timeframe_ranges import HigherTimeframeRangeRequest, analyze_higher_timeframe_ranges
from app.engine.structure import Candle
from app.main import app

client = TestClient(app)


def candles(offset=0):
    rows = [
        (100, 101, 99, 100), (100, 110, 98, 105), (105, 106, 99, 103),
        (100, 104, 90, 95), (95, 102, 92, 100), (100, 103, 94, 101),
        (101, 104, 96, 103),
    ]
    return [Candle(timestamp=f"2026-01-01T00:{i + offset:02d}:00Z", open=o, high=h, low=l, close=c)
            for i, (o, h, l, c) in enumerate(rows)]


def test_higher_timeframe_ranges_return_separate_contexts_in_timeframe_order():
    primary = candles()
    h1 = candles()
    h4 = candles()
    # Use later but not future timestamps for the supplied HTF data.
    h1 = [c.model_copy(update={"timestamp": f"2026-01-01T00:{i:02d}:00Z"}) for i, c in enumerate(h1)]
    h4 = [c.model_copy(update={"timestamp": f"2026-01-01T00:{i:02d}:00Z"}) for i, c in enumerate(h4)]
    request = HigherTimeframeRangeRequest(
        primary_timeframe="5m", primary_candles=primary,
        higher_timeframes=[
            {"timeframe": "4H", "candles": h4},
            {"timeframe": "1H", "candles": h1},
        ], pivot=1,
    )
    result = analyze_higher_timeframe_ranges(request)
    assert [item.timeframe for item in result.contexts] == ["1H", "4H"]
    assert all(item.analysis.available for item in result.contexts)


def test_rejects_context_not_higher_than_primary():
    data = candles()
    try:
        HigherTimeframeRangeRequest(
            primary_timeframe="1H", primary_candles=data,
            higher_timeframes=[{"timeframe": "15m", "candles": data}],
        )
    except ValueError as exc:
        assert "must exceed" in str(exc)
    else:
        raise AssertionError("expected timeframe ordering validation")


def test_rejects_future_dated_higher_timeframe_candles():
    data = candles()
    future = [c.model_copy(update={"timestamp": f"2026-01-02T00:{i:02d}:00Z"}) for i, c in enumerate(data)]
    try:
        HigherTimeframeRangeRequest(
            primary_timeframe="5m", primary_candles=data,
            higher_timeframes=[{"timeframe": "1H", "candles": future}],
        )
    except ValueError as exc:
        assert "beyond the primary" in str(exc)
    else:
        raise AssertionError("expected future context validation")


def test_higher_timeframe_ranges_api():
    data = candles()
    response = client.post("/api/v1/analysis/higher-timeframe-ranges", json={
        "primary_timeframe": "5m",
        "primary_candles": [c.model_dump() for c in data],
        "higher_timeframes": [{"timeframe": "1H", "candles": [c.model_dump() for c in data]}],
        "pivot": 1,
    })
    assert response.status_code == 200
    assert response.json()["contexts"][0]["timeframe"] == "1H"
