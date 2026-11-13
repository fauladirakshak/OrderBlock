from fastapi.testclient import TestClient

from app.engine.higher_timeframe_zones import HigherTimeframeZonesRequest, analyze_higher_timeframe_zones
from app.engine.structure import Candle
from app.main import app

client = TestClient(app)


def series(prefix="2026-01-01T00"):
    rows = [
        (9, 10, 8, 9), (10, 12, 9, 11), (9, 11, 7, 8),
        (11, 13, 10, 12.5), (12, 14, 11, 13.5), (13, 15, 12, 14),
        (14, 16, 13, 15),
    ]
    return [Candle(timestamp=f"{prefix}:{i:02d}:00Z", open=o, high=h, low=l, close=c)
            for i, (o, h, l, c) in enumerate(rows)]


def test_higher_timeframe_zones_are_returned_by_timeframe():
    data = series()
    request = HigherTimeframeZonesRequest(
        primary_timeframe="5m",
        primary_candles=data,
        higher_timeframes=[
            {"timeframe": "4H", "candles": data},
            {"timeframe": "1H", "candles": data},
        ],
        pivot=1,
    )
    result = analyze_higher_timeframe_zones(request)
    assert [item.timeframe for item in result.contexts] == ["1H", "4H"]
    assert result.contexts[0].order_blocks
    assert all(item.latest_candle_timestamp == data[-1].timestamp for item in result.contexts)


def test_higher_timeframe_zones_reject_primary_or_future_context():
    data = series()
    try:
        HigherTimeframeZonesRequest(
            primary_timeframe="1H", primary_candles=data,
            higher_timeframes=[{"timeframe": "15m", "candles": data}],
        )
    except ValueError as exc:
        assert "must exceed" in str(exc)
    else:
        raise AssertionError("expected timeframe validation")

    future = [c.model_copy(update={"timestamp": f"2026-01-02T00:{i:02d}:00Z"}) for i, c in enumerate(data)]
    try:
        HigherTimeframeZonesRequest(
            primary_timeframe="5m", primary_candles=data,
            higher_timeframes=[{"timeframe": "1H", "candles": future}],
        )
    except ValueError as exc:
        assert "beyond the primary" in str(exc)
    else:
        raise AssertionError("expected future timestamp validation")


def test_higher_timeframe_zones_api():
    data = series()
    response = client.post("/api/v1/analysis/higher-timeframe-zones", json={
        "primary_timeframe": "5m",
        "primary_candles": [c.model_dump() for c in data],
        "higher_timeframes": [{"timeframe": "1H", "candles": [c.model_dump() for c in data]}],
        "pivot": 1,
    })
    assert response.status_code == 200
    assert response.json()["contexts"][0]["timeframe"] == "1H"
