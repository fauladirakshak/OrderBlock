"""HTTP historical-data adapters. Credentials are read only from server environment."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import httpx

from app.engine.markets import Instrument
from app.engine.structure import Candle


class ProviderConfigurationError(RuntimeError):
    pass


class MarketDataProviderError(RuntimeError):
    pass


def _utc_timestamp(value: str, default_timezone: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(default_timezone))
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class TwelveDataProvider:
    """Twelve Data /time_series adapter for entitled FX, crypto and equity symbols."""

    name = "twelvedata"

    def __init__(self, api_key: str | None = None, base_url: str = "https://api.twelvedata.com"):
        self.api_key = api_key or os.getenv("TWELVEDATA_API_KEY", "")
        self.base_url = base_url.rstrip(" /")

    def get_candles(self, instrument: Instrument, timeframe: str, limit: int) -> list[Candle]:
        if not self.api_key:
            raise ProviderConfigurationError("TWELVEDATA_API_KEY is required for Twelve Data.")
        interval = {"5m":"5min","15m":"15min","1H":"1h","4H":"4h","1D":"1day","1W":"1week"}[timeframe]
        try:
            response = httpx.get(
                self.base_url + "/time_series",
                params={"symbol": instrument.provider_symbol, "interval": interval, "outputsize": limit,
                        "apikey": self.api_key, "format": "JSON", "timezone": instrument.timezone,
                        **({"exchange": instrument.venue} if instrument.asset_class in {"equity", "equity_index"} else {})},
                timeout=15.0,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise MarketDataProviderError(f"Twelve Data request failed: {exc}") from exc
        if payload.get("status") == "error" or "values" not in payload:
            message = payload.get("message", "Unexpected response")
            raise MarketDataProviderError(f"Twelve Data error: {message}")
        meta = payload.get("meta") or {}
        source_timezone = meta.get("exchange_timezone") or instrument.timezone
        rows = payload["values"]
        candles = [
            Candle(timestamp=_utc_timestamp(row["datetime"], source_timezone),
                   open=float(row["open"]), high=float(row["high"]),
                   low=float(row["low"]), close=float(row["close"]),
                   volume=float(row["volume"]) if row.get("volume") not in (None, "") else 0.0)
            for row in reversed(rows)
        ]
        return candles[-limit:]


class BinanceSpotProvider:
    """Unauthenticated Binance public spot klines; no private account access."""

    name = "binance-spot"

    def __init__(self, base_url: str = "https://data-api.binance.vision"):
        self.base_url = base_url.rstrip(" /")

    def get_candles(self, instrument: Instrument, timeframe: str, limit: int) -> list[Candle]:
        if instrument.venue_id != "BINANCE:SPOT" or instrument.contract_type != "spot":
            raise MarketDataProviderError("BinanceSpotProvider only serves Binance spot instruments.")
        interval = {"5m":"5m","15m":"15m","1H":"1h","4H":"4h","1D":"1d","1W":"1w"}[timeframe]
        try:
            response = httpx.get(self.base_url + "/api/v3/klines",
                                 params={"symbol": instrument.provider_symbol.replace("/", ""), "interval": interval, "limit": limit},
                                 timeout=15.0)
            response.raise_for_status()
            rows = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise MarketDataProviderError(f"Binance market-data request failed: {exc}") from exc
        if not isinstance(rows, list):
            raise MarketDataProviderError("Binance returned an unexpected kline payload.")
        return [
            Candle(timestamp=datetime.fromtimestamp(int(row[0]) / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
                   open=float(row[1]), high=float(row[2]), low=float(row[3]), close=float(row[4]),
                   volume=float(row[5]))
            for row in rows
        ]


def configured_provider(instrument: Instrument):
    """Select provider by explicit env configuration; never silently fall back to demo."""
    selected = os.getenv("ORDERBLOCK_DATA_PROVIDER", "synthetic").lower()
    if selected == "synthetic":
        from app.engine.market_data import demo_provider
        return demo_provider
    if selected == "twelvedata":
        return TwelveDataProvider()
    if selected == "binance":
        if instrument.venue_id != "BINANCE:SPOT":
            raise MarketDataProviderError("ORDERBLOCK_DATA_PROVIDER=binance only supports Binance spot contracts.")
        return BinanceSpotProvider()
    raise ProviderConfigurationError(f"Unsupported ORDERBLOCK_DATA_PROVIDER: {selected}")
