import pytest

from app.engine.historical_import import parse_historical_csv
from fastapi.testclient import TestClient
from app.main import app


def test_csv_import_normalizes_naive_timestamps_to_utc():
    text = "timestamp,open,high,low,close,volume\n2026-01-01 09:15:00,100,105,99,103,120\n2026-01-01 09:30:00,103,106,102,104,140\n"
    candles = parse_historical_csv(text, "Asia/Kolkata")
    assert candles[0].timestamp == "2026-01-01T03:45:00Z"
    assert candles[1].volume == 140


def test_csv_import_accepts_iso_z_and_optional_volume():
    text = "datetime,open,high,low,close\n2026-01-01T00:00:00Z,1,2,0.5,1.5\n"
    candles = parse_historical_csv(text)
    assert candles[0].volume == 0


@pytest.mark.parametrize("text", [
    "timestamp,open,high,low,close\n2026-01-01,1,0,2,1\n",
    "timestamp,open,high,low,close\n2026-01-01,1,2,0,1\n2026-01-01,1,2,0,1\n",
    "date,open,close\n2026-01-01,1,1\n",
])
def test_csv_import_rejects_invalid_ohlc_order_or_columns(text):
    with pytest.raises(ValueError):
        parse_historical_csv(text)


def test_csv_import_rejects_unknown_timezone():
    with pytest.raises(ValueError, match="Unknown IANA timezone"):
        parse_historical_csv("timestamp,open,high,low,close\n2026-01-01,1,2,0,1\n", "Mars/Olympus")


def test_csv_import_api_returns_source_metadata():
    client = TestClient(app)
    response = client.post("/api/v1/market-data/import/csv", json={
        "symbol": "EUR/USD", "market": "forex", "timeframe": "1H",
        "timezone": "UTC",
        "csv_text": "timestamp,open,high,low,close\n2026-01-01T00:00:00Z,1,2,0.5,1.5\n",
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "user-csv-import"
    assert payload["is_synthetic"] is False
    assert payload["candle_count"] == 1
