"""Market-data provider boundary and deterministic synthetic demo implementation."""
from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta, timezone
from typing import Literal, Protocol

from pydantic import BaseModel

from app.engine.markets import Instrument, get_instrument
from app.engine.structure import Candle
from app.engine.market_data_cache import (
    cache_enabled, cache_ttl_seconds, get_cached_payload, make_cache_key,
    put_cached_payload,
)

Market = Literal["forex", "crypto", "stocks"]
Timeframe = Literal["5m", "15m", "1H", "4H", "1D", "1W"]

TIMEFRAME_SECONDS: dict[str, int] = {
    "5m": 300, "15m": 900, "1H": 3600, "4H": 14400, "1D": 86400, "1W": 604800,
}


class CandleSeries(BaseModel):
    market: Market
    symbol: str
    timeframe: Timeframe
    provider: str
    is_synthetic: bool
    venue: str
    venue_id: str
    contract_type: str
    timezone: str
    session: str
    price_precision: int
    tick_size: float
    cache_status: Literal["disabled", "hit", "miss", "demo"] = "disabled"
    candles: list[Candle]


class MarketDataProvider(Protocol):
    name: str

    def get_candles(self, market: Market, symbol: str, timeframe: Timeframe, limit: int) -> list[Candle]: ...


class SyntheticDemoProvider:
    """Stable seeded OHLC series for UI development only."""

    name = "synthetic-demo"

    def get_candles(self, market: Market, symbol: str, timeframe: Timeframe, limit: int) -> list[Candle]:
        seed_text = f"{market}:{symbol}:{timeframe}"
        seed = int.from_bytes(hashlib.sha256(seed_text.encode()).digest()[:8], "big")
        rng = random.Random(seed)
        interval = TIMEFRAME_SECONDS[timeframe]
        end = datetime(2026, 1, 1, tzinfo=timezone.utc)
        start = end - timedelta(seconds=interval * (limit - 1))
        base = 1.08 if market == "forex" else (42000.0 if market == "crypto" else 24000.0)
        scale = 0.001 if market == "forex" else (0.003 if market == "crypto" else 0.0008)
        previous = base + (seed % 1000) * scale
        candles: list[Candle] = []
        for index in range(limit):
            wave = (rng.random() - 0.48) * base * scale * 16
            open_price = previous
            close_price = max(0.00001, open_price + wave)
            wick = abs(wave) * 0.35 + base * scale * (0.2 + rng.random() * 0.35)
            high = max(open_price, close_price) + wick
            low = max(0.000001, min(open_price, close_price) - wick * (0.8 + rng.random() * 0.3))
            timestamp = start + timedelta(seconds=interval * index)
            candles.append(Candle(timestamp=timestamp.isoformat().replace("+00:00", "Z"),
                                  open=round(open_price, 6), high=round(high, 6),
                                  low=round(low, 6), close=round(close_price, 6),
                                  volume=round(rng.uniform(10, 1000), 2)))
            previous = close_price
        return candles


demo_provider = SyntheticDemoProvider()


def load_candle_series(market: Market, symbol: str, timeframe: Timeframe, limit: int = 200,
                       venue_id: str | None = None, contract_type: str | None = None) -> CandleSeries:
    instrument = get_instrument(symbol, venue_id, contract_type)
    allowed = {"forex": {"forex"}, "crypto": {"crypto"}, "stocks": {"equity", "equity_index"}}
    if instrument.asset_class not in allowed[market]:
        raise ValueError(f"{symbol} does not belong to market {market}.")
    from app.engine.providers import configured_provider
    provider = configured_provider(instrument)
    is_synthetic = provider.name == "synthetic-demo"
    cache_status: Literal["disabled", "hit", "miss", "demo"] = "demo" if is_synthetic else "disabled"
    candles: list[Candle]

    # Never persist demo data. Real-provider caching is opt-in because exchange
    # terms may prohibit local storage or impose a shorter retention window.
    if is_synthetic:
        candles = provider.get_candles(market, symbol, timeframe, limit)
    elif cache_enabled() and cache_ttl_seconds() > 0:
        cache_key = make_cache_key(
            provider=provider.name, venue_id=instrument.venue_id,
            contract_type=instrument.contract_type, symbol=instrument.symbol,
            timeframe=timeframe, limit=limit,
        )
        cached = get_cached_payload(cache_key)
        if cached is not None:
            candles = [Candle.model_validate(item) for item in cached.get("candles", [])]
            cache_status = "hit"
        else:
            candles = provider.get_candles(instrument, timeframe, limit)
            put_cached_payload(
                cache_key, {"candles": [item.model_dump() for item in candles]},
                ttl_seconds=cache_ttl_seconds(),
            )
            cache_status = "miss"
    else:
        candles = provider.get_candles(instrument, timeframe, limit)

    return CandleSeries(market=market, symbol=symbol, timeframe=timeframe,
                        provider=provider.name, is_synthetic=is_synthetic,
                        venue=instrument.venue, venue_id=instrument.venue_id,
                        contract_type=instrument.contract_type, timezone=instrument.timezone,
                        session=instrument.session, price_precision=instrument.price_precision,
                        tick_size=instrument.tick_size, cache_status=cache_status, candles=candles)
