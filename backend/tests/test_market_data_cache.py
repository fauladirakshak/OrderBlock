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
