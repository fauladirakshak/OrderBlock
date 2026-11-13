import pytest
from fastapi.testclient import TestClient

from app.engine.liquidity_references import LiquidityReferenceRequest, analyze_liquidity_references
from app.engine.structure import Candle
from app.main import app

client = TestClient(app)


def candle(stamp, o, h, l, c):
    return Candle(timestamp=stamp, open=o, high=h, low=l, close=c)


def test_previous_day_and_week_levels_use_local_calendar():
    data = [
        candle("2026-11-02T04:00:00Z", 100, 105, 98, 102),
        candle("2026-11-03T04:00:00Z", 102, 108, 97, 104),
        candle("2026-11-04T04:00:00Z", 104, 110, 96, 103),
        candle("2026-11-05T04:00:00Z", 103, 107, 95, 101),
        candle("2026-11-06T04:00:00Z", 101, 106, 94, 100),
        candle("2026-11-09T04:00:00Z", 100, 104, 97, 102),
        candle("2026-11-10T04:00:00Z", 102, 103, 98, 101),
    ]
    result = analyze_liquidity_references(LiquidityReferenceRequest(
        candles=data, timezone="Asia/Kolkata", pivot=1, tick_size=0.05,
    ))
    by_label = {item.label: item for item in result.levels}
    assert by_label["PDH"].price == 103
    assert by_label["PDL"].price == 98
    assert by_label["PWH"].price == 110
    assert by_label["PWL"].price == 94
    # Previous-day level becomes known only after the final candle of that day.
    assert by_label["PDH"].confirmed_index == 5


def test_equal_high_cluster_is_confirmed_before_later_sweep():
    data = [
        candle("2026-01-01T00:00:00Z", 99, 100, 90, 98),
        candle("2026-01-01T00:01:00Z", 100, 105, 95, 101),
        candle("2026-01-01T00:02:00Z", 101, 102, 96, 100),
        candle("2026-01-01T00:03:00Z", 100, 104.9, 94, 99),
        candle("2026-01-01T00:04:00Z", 99, 102, 97, 100),
        candle("2026-01-01T00:05:00Z", 100, 106, 98, 104),
        candle("2026-01-01T00:06:00Z", 104, 105, 99, 103),
    ]
    result = analyze_liquidity_references(LiquidityReferenceRequest(
        candles=data, timezone="Etc/UTC", pivot=1, tick_size=0.1, tolerance_ticks=2,
    ))
    equal_highs = next(item for item in result.levels if item.kind == "equal_highs")
    assert equal_highs.touch_count == 2
    assert equal_highs.confirmed_index == 4
    assert equal_highs.swept is True
    assert equal_highs.sweep_index == 5


def test_reference_analysis_rejects_unknown_timezone_and_unordered_candles():
    data = [candle(f"2026-01-01T00:{i:02d}:00Z", 100, 101, 99, 100) for i in range(5)]
    with pytest.raises(ValueError, match="Unknown IANA timezone"):
        LiquidityReferenceRequest(candles=data, timezone="Mars/Olympus")
    data[2] = data[1]
    with pytest.raises(ValueError, match="strictly increasing"):
        LiquidityReferenceRequest(candles=data)


def test_liquidity_reference_api_returns_levels():
    data = [
        candle("2026-11-09T04:00:00Z", 100, 102, 98, 101),
        candle("2026-11-09T05:00:00Z", 101, 103, 97, 102),
        candle("2026-11-09T06:00:00Z", 102, 104, 96, 103),
        candle("2026-11-10T04:00:00Z", 103, 105, 95, 104),
        candle("2026-11-10T05:00:00Z", 104, 106, 94, 105),
    ]
    response = client.post("/api/v1/analysis/liquidity-references", json={
        "candles": [item.model_dump() for item in data],
        "timezone": "Asia/Kolkata", "pivot": 1, "tick_size": 0.05,
    })
    assert response.status_code == 200
    assert {item["label"] for item in response.json()["levels"]} >= {"PDH", "PDL"}
