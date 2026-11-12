from datetime import datetime

from fastapi.testclient import TestClient

from app.engine.market_data import SyntheticDemoProvider, TIMEFRAME_SECONDS
from app.main import app

client = TestClient(app)


def test_demo_provider_is_deterministic():
    provider = SyntheticDemoProvider()
    first = provider.get_candles("crypto", "BTC/USDT", "1H", 30)
    second = provider.get_candles("crypto", "BTC/USDT", "1H", 30)
    assert [c.model_dump() for c in first] == [c.model_dump() for c in second]


def test_demo_provider_respects_requested_timeframe():
    candles = SyntheticDemoProvider().get_candles("forex", "EUR/USD", "15m", 25)
    assert len(candles) == 25
    stamps = [datetime.fromisoformat(c.timestamp.replace("Z", "+00:00")) for c in candles]
    assert all(
        (b - a).total_seconds() == TIMEFRAME_SECONDS["15m"]
        for a, b in zip(stamps, stamps[1:])
    )


def test_market_data_api_returns_explicit_demo_metadata():
    response = client.get(
        "/api/v1/market-data/candles",
        params={"market": "crypto", "symbol": "BTC/USDT", "timeframe": "4H", "limit": 40},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "synthetic-demo"
    assert payload["is_synthetic"] is True
    assert payload["timeframe"] == "4H"
    assert len(payload["candles"]) == 40


def test_market_data_api_rejects_unknown_timeframe():
    response = client.get(
        "/api/v1/market-data/candles",
        params={"market": "forex", "symbol": "EUR/USD", "timeframe": "2H"},
    )
    assert response.status_code == 422
