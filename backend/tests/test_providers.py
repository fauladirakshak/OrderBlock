import httpx
import pytest

from app.engine.markets import get_instrument
from app.engine.providers import (
    BinanceSpotProvider, MarketDataProviderError, ProviderConfigurationError,
    TwelveDataProvider,
)


def test_twelvedata_normalizes_rows_to_utc(monkeypatch):
    payload = {
        "meta": {"exchange_timezone": "Asia/Kolkata"},
        "values": [
            {"datetime": "2026-01-02 09:30:00", "open": "10", "high": "12", "low": "9", "close": "11", "volume": "100"},
            {"datetime": "2026-01-02 09:15:00", "open": "9", "high": "11", "low": "8", "close": "10", "volume": "80"},
        ],
    }
    monkeypatch.setattr(httpx, "get", lambda *a, **k: httpx.Response(200, json=payload, request=httpx.Request("GET", "https://test")))
    candles = TwelveDataProvider(api_key="test", base_url="https://test").get_candles(get_instrument("RELIANCE"), "15m", 2)
    assert candles[0].timestamp == "2026-01-02T03:45:00Z"
    assert candles[1].timestamp == "2026-01-02T04:00:00Z"
    assert candles[0].volume == 80


def test_twelvedata_requires_api_key():
    with pytest.raises(ProviderConfigurationError):
        TwelveDataProvider(api_key="").get_candles(get_instrument("EUR/USD"), "1H", 20)


def test_twelvedata_provider_error_is_not_silently_synthetic(monkeypatch):
    payload = {"status": "error", "message": "API credits exhausted"}
    monkeypatch.setattr(httpx, "get", lambda *a, **k: httpx.Response(200, json=payload, request=httpx.Request("GET", "https://test")))
    with pytest.raises(MarketDataProviderError, match="credits exhausted"):
        TwelveDataProvider(api_key="test", base_url="https://test").get_candles(get_instrument("EUR/USD"), "1H", 20)


def test_binance_spot_maps_kline_payload(monkeypatch):
    row = [1767225600000, "100", "110", "95", "105", "12.5", 1767229199999, "0", 10, "0", "0", "0"]
    monkeypatch.setattr(httpx, "get", lambda *a, **k: httpx.Response(200, json=[row], request=httpx.Request("GET", "https://test")))
    candles = BinanceSpotProvider(base_url="https://test").get_candles(get_instrument("BTC/USDT"), "1H", 1)
    assert candles[0].timestamp == "2026-01-01T00:00:00Z"
    assert (candles[0].open, candles[0].high, candles[0].low, candles[0].close) == (100, 110, 95, 105)
    assert candles[0].volume == 12.5


def test_binance_rejects_non_binance_instrument():
    with pytest.raises(MarketDataProviderError):
        BinanceSpotProvider().get_candles(get_instrument("EUR/USD"), "1H", 20)


def test_auto_provider_routes_crypto_to_binance_and_fx_to_twelvedata(monkeypatch):
    from app.engine.providers import configured_provider

    monkeypatch.setenv("ORDERBLOCK_DATA_PROVIDER", "auto")
    assert isinstance(configured_provider(get_instrument("BTC/USDT")), BinanceSpotProvider)
    assert isinstance(configured_provider(get_instrument("EUR/USD")), TwelveDataProvider)
    assert isinstance(configured_provider(get_instrument("RELIANCE")), TwelveDataProvider)
