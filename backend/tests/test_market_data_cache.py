from app.engine.market_data_cache import (
    get_cached_payload, make_cache_key, put_cached_payload,
)


def test_persistent_cache_round_trip_and_expiry(tmp_path, monkeypatch):
    monkeypatch.setenv("ORDERBLOCK_CACHE_DB", str(tmp_path / "cache.sqlite3"))
    key = make_cache_key(
        provider="test-provider", venue_id="TEST:SPOT", contract_type="spot",
        symbol="ABC/USDT", timeframe="1H", limit=20,
    )
    put_cached_payload(key, {"candles": [{"close": 123.4}]}, ttl_seconds=60, now=100)
    assert get_cached_payload(key, now=120) == {"candles": [{"close": 123.4}]}
    assert get_cached_payload(key, now=161) is None


def test_cache_key_is_scoped_to_provider_and_instrument():
    base = dict(provider="provider-a", venue_id="VENUE:A", contract_type="spot",
                symbol="ABC/USDT", timeframe="1H", limit=20)
    key = make_cache_key(**base)
    assert key != make_cache_key(**{**base, "provider": "provider-b"})
    assert key != make_cache_key(**{**base, "venue_id": "VENUE:B"})
    assert key != make_cache_key(**{**base, "timeframe": "4H"})


def test_market_data_loader_uses_cache_after_provider_fetch(tmp_path, monkeypatch):
    from app.engine import providers
    from app.engine.market_data import load_candle_series
    from app.engine.structure import Candle

    monkeypatch.setenv("ORDERBLOCK_CACHE_DB", str(tmp_path / "integration.sqlite3"))
    monkeypatch.setenv("ORDERBLOCK_CACHE_ENABLED", "true")
    monkeypatch.setenv("ORDERBLOCK_CACHE_TTL_SECONDS", "300")

    class FakeProvider:
        name = "fake-licensed-provider"

        def __init__(self):
            self.calls = 0

        def get_candles(self, instrument, timeframe, limit):
            self.calls += 1
            return [Candle(timestamp="2026-01-01T00:00:00Z", open=1.0, high=1.2,
                           low=0.9, close=1.1, volume=10.0)]

    fake = FakeProvider()
    monkeypatch.setattr(providers, "configured_provider", lambda instrument: fake)

    first = load_candle_series("forex", "EUR/USD", "1H", 20)
    second = load_candle_series("forex", "EUR/USD", "1H", 20)

    assert first.cache_status == "miss"
    assert second.cache_status == "hit"
    assert fake.calls == 1
    assert second.candles[0].close == 1.1
