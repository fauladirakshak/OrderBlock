import httpx
import pytest

from app.engine.markets import get_instrument
from app.engine.providers import (
    BinanceSpotProvider, MarketDataProviderError, ProviderConfigurationError,
    configured_provider,
)


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


def test_auto_provider_routes_binance_spot_without_credentials(monkeypatch):
    monkeypatch.setenv("ORDERBLOCK_DATA_PROVIDER", "auto")
    assert isinstance(configured_provider(get_instrument("BTC/USDT")), BinanceSpotProvider)


def test_auto_provider_does_not_fall_back_to_paid_feed_for_forex_or_nse(monkeypatch):
    monkeypatch.setenv("ORDERBLOCK_DATA_PROVIDER", "auto")
    with pytest.raises(ProviderConfigurationError, match="No free public adapter"):
        configured_provider(get_instrument("EUR/USD"))
    with pytest.raises(ProviderConfigurationError, match="No free public adapter"):
        configured_provider(get_instrument("RELIANCE"))


def test_paid_provider_selection_is_disabled(monkeypatch):
    monkeypatch.setenv("ORDERBLOCK_DATA_PROVIDER", "twelvedata")
    with pytest.raises(ProviderConfigurationError, match="Paid market-data providers are disabled"):
        configured_provider(get_instrument("EUR/USD"))
