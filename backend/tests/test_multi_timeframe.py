from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def candle_payload():
    values = [
        (10, 12, 9, 11), (11, 13, 10, 12), (12, 14, 11, 13),
        (13, 14, 10, 11), (11, 12, 8, 9), (9, 12, 9, 11),
        (11, 13, 10, 12), (12, 15, 11, 14), (14, 17, 13, 16),
        (16, 18, 15, 17), (17, 19, 16, 18),
    ]
    return [
        {
            "timestamp": f"2026-01-01T00:{i:02d}:00Z",
            "open": o, "high": h, "low": l, "close": c,
        }
        for i, (o, h, l, c) in enumerate(values)
    ]


def test_multi_timeframe_endpoint_returns_context_and_alignment():
    candles = candle_payload()
    response = client.post("/api/v1/analysis/multi-timeframe", json={
        "primary_timeframe": "15m",
        "pivot": 1,
        "candles_by_timeframe": {"15m": candles, "1H": candles, "4H": candles},
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["primary_timeframe"] == "15m"
    assert payload["alignment"] in {"bullish", "bearish", "mixed", "neutral"}
    assert [item["timeframe"] for item in payload["higher_timeframe_context"]] == ["4H", "1H"]
    assert len(payload["notes"]) >= 3


def test_multi_timeframe_rejects_lower_timeframe_as_context():
    candles = candle_payload()
    response = client.post("/api/v1/analysis/multi-timeframe", json={
        "primary_timeframe": "1H",
        "pivot": 1,
        "candles_by_timeframe": {"1H": candles, "15m": candles},
    })
    assert response.status_code == 422


def test_multi_timeframe_rejects_missing_primary_series():
    candles = candle_payload()
    response = client.post("/api/v1/analysis/multi-timeframe", json={
        "primary_timeframe": "15m",
        "pivot": 1,
        "candles_by_timeframe": {"1H": candles, "4H": candles},
    })
    assert response.status_code == 422



def test_multi_timeframe_rejects_future_dated_context():
    primary = candle_payload()
    future = [
        {**candle, "timestamp": f"2026-01-02T00:{i:02d}:00Z"}
        for i, candle in enumerate(candle_payload())
    ]
    response = client.post("/api/v1/analysis/multi-timeframe", json={
        "primary_timeframe": "15m", "pivot": 1,
        "candles_by_timeframe": {"15m": primary, "1H": future},
    })
    assert response.status_code == 422
    assert "cannot extend beyond" in response.json()["detail"][0]["msg"]


def test_multi_timeframe_rejects_unordered_or_timezone_naive_context():
    primary = candle_payload()
    unordered = candle_payload()
    unordered[4]["timestamp"] = unordered[3]["timestamp"]
    response = client.post("/api/v1/analysis/multi-timeframe", json={
        "primary_timeframe": "15m", "pivot": 1,
        "candles_by_timeframe": {"15m": primary, "1H": unordered},
    })
    assert response.status_code == 422
    assert "strictly increasing" in response.json()["detail"][0]["msg"]

    naive = candle_payload()
    naive[0]["timestamp"] = "2026-01-01T00:00:00"
    response = client.post("/api/v1/analysis/multi-timeframe", json={
        "primary_timeframe": "15m", "pivot": 1,
        "candles_by_timeframe": {"15m": primary, "1H": naive},
    })
    assert response.status_code == 422
    assert "timezone" in response.json()["detail"][0]["msg"]
