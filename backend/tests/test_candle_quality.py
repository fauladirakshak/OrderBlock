from fastapi.testclient import TestClient

from app.engine.candle_quality import CandleQualityRequest, audit_candle_quality
from app.main import app


def make_candle(ts: str, price: float, volume: float = 1):
    return {"timestamp": ts, "open": price, "high": price + 1, "low": price - 1,
            "close": price, "volume": volume}


def test_quality_audit_reports_gap_without_calling_it_missing_data():
    request = CandleQualityRequest(timeframe="1H", candles=[
        make_candle("2026-01-05T09:00:00Z", 100),
        make_candle("2026-01-05T10:00:00Z", 101),
        make_candle("2026-01-05T13:00:00Z", 102, 0),
    ])
    result = audit_candle_quality(request)
    assert result.gap_count == 1
    assert result.estimated_intervening_bars == 2
    assert result.zero_volume_candles == 1
    assert "not proof" in result.notes[1]


def test_quality_audit_does_not_flag_regular_spacing():
    request = CandleQualityRequest(timeframe="15m", candles=[
        make_candle("2026-01-05T09:00:00Z", 100),
        make_candle("2026-01-05T09:15:00Z", 101),
        make_candle("2026-01-05T09:30:00Z", 102),
    ])
    result = audit_candle_quality(request)
    assert result.gap_count == 0
    assert result.median_interval_seconds == 900


def test_quality_api_returns_series_diagnostics():
    client = TestClient(app)
    response = client.post("/api/v1/analysis/candle-quality", json={
        "timeframe": "1H",
        "candles": [
            make_candle("2026-01-05T09:00:00Z", 100),
            make_candle("2026-01-05T10:00:00Z", 101),
            make_candle("2026-01-05T11:00:00Z", 102),
        ],
    })
    assert response.status_code == 200
    assert response.json()["candle_count"] == 3


def test_quality_api_rejects_timezone_naive_timestamps():
    client = TestClient(app)
    response = client.post("/api/v1/analysis/candle-quality", json={
        "timeframe": "1H",
        "candles": [
            make_candle("2026-01-05T09:00:00", 100),
            make_candle("2026-01-05T10:00:00Z", 101),
        ],
    })
    assert response.status_code == 422


def test_quality_request_rejects_duplicate_timestamps():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="strictly increasing"):
        CandleQualityRequest(timeframe="1H", candles=[
            make_candle("2026-01-05T09:00:00Z", 100),
            make_candle("2026-01-05T09:00:00Z", 101),
        ])


def test_quality_request_rejects_invalid_ohlc():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="high must be the greatest"):
        CandleQualityRequest(timeframe="1H", candles=[
            make_candle("2026-01-05T09:00:00Z", 100),
            {"timestamp": "2026-01-05T10:00:00Z", "open": 100, "high": 99,
             "low": 98, "close": 100, "volume": 1},
        ])
