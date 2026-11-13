from fastapi.testclient import TestClient

from app.engine.dealing_range import DealingRangeRequest, analyze_dealing_range
from app.engine.structure import Candle
from app.main import app

client = TestClient(app)


def sample_candles():
    rows = [
        (100, 101, 99, 100),
        (100, 110, 98, 105),
        (105, 106, 99, 103),
        (100, 104, 90, 95),
        (95, 102, 92, 100),
        (100, 103, 94, 101),
        (101, 104, 96, 103),
    ]
    return [Candle(timestamp=f"2026-01-01T00:0{i}:00Z", open=o, high=h, low=l, close=c)
            for i, (o, h, l, c) in enumerate(rows)]


def test_dealing_range_uses_confirmed_swings_and_classifies_premium():
    result = analyze_dealing_range(DealingRangeRequest(candles=sample_candles(), pivot=1, equilibrium_band_pct=5))
    assert result.available is True
    assert result.range is not None
    assert result.range.high == 110
    assert result.range.low == 90
    assert result.range.equilibrium == 100
    assert result.range.location == "premium"
    assert result.range.high_confirmation_index == 2
    assert result.range.low_confirmation_index == 4


def test_dealing_range_can_classify_equilibrium_and_outside_range():
    data = sample_candles()
    data[-1] = Candle(timestamp=data[-1].timestamp, open=100, high=101, low=99, close=100)
    result = analyze_dealing_range(DealingRangeRequest(candles=data, pivot=1))
    assert result.range is not None
    assert result.range.location == "equilibrium"


def test_dealing_range_unavailable_without_confirmed_swings():
    data = [Candle(timestamp=f"2026-01-01T00:0{i}:00Z", open=100, high=101+i, low=99-i, close=100)
            for i in range(5)]
    result = analyze_dealing_range(DealingRangeRequest(candles=data, pivot=1))
    assert result.available is False
    assert result.range is None


def test_dealing_range_api_returns_context():
    response = client.post("/api/v1/analysis/dealing-range", json={
        "candles": [item.model_dump() for item in sample_candles()],
        "pivot": 1, "equilibrium_band_pct": 5,
    })
    assert response.status_code == 200
    assert response.json()["range"]["location"] == "premium"
