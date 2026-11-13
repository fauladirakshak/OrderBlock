"""Free/public market-data adapters; no paid API credentials are required."""
from __future__ import annotations

import os
from datetime import datetime, timezone

import httpx

from app.engine.markets import Instrument
from app.engine.structure import Candle


class ProviderConfigurationError(RuntimeError):
    pass


class MarketDataProviderError(RuntimeError):
    pass


class BinanceSpotProvider:
    """Unauthenticated Binance public Spot klines; no account/API key required."""

    name = "binance-spot"

    def __init__(self, base_url: str = "https://data-api.binance.vision"):
        self.base_url = base_url.rstrip(" /")

    def get_candles(self, instrument: Instrument, timeframe: str, limit: int) -> list[Candle]:
        if instrument.venue_id != "BINANCE:SPOT" or instrument.contract_type != "spot":
            raise MarketDataProviderError("BinanceSpotProvider only serves Binance Spot instruments.")
        interval = {"5m":"5m","15m":"15m","1H":"1h","4H":"4h","1D":"1d","1W":"1w"}[timeframe]
        try:
            response = httpx.get(
                self.base_url + "/api/v3/klines",
                params={"symbol": instrument.provider_symbol.replace("/", ""),
                        "interval": interval, "limit": limit},
                timeout=15.0,
            )
            response.raise_for_status()
            rows = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise MarketDataProviderError(f"Binance public market-data request failed: {exc}") from exc
        if not isinstance(rows, list):
            raise MarketDataProviderError("Binance returned an unexpected kline payload.")
        # Binance includes the currently forming kline in many responses.
        # Exclude it from the research API so downstream structure/FVG logic sees
        # completed bars only. Keep the open timestamp as the candle identity.
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        closed_rows = []
        for row in rows:
            try:
                if int(row[6]) < now_ms:
                    closed_rows.append(row)
            except (IndexError, TypeError, ValueError) as exc:
                raise MarketDataProviderError("Binance returned a malformed kline close timestamp.") from exc
        return [
            Candle(timestamp=datetime.fromtimestamp(int(row[0]) / 1000, tz=timezone.utc)
                   .isoformat().replace("+00:00", "Z"),
                   open=float(row[1]), high=float(row[2]), low=float(row[3]),
                   close=float(row[4]), volume=float(row[5]))
            for row in closed_rows
        ]


def configured_provider(instrument: Instrument):
    """Select a zero-subscription provider; never silently fall back to synthetic data."""
    selected = os.getenv("ORDERBLOCK_DATA_PROVIDER", "synthetic").lower()
    if selected == "synthetic":
        from app.engine.market_data import demo_provider
        return demo_provider
    if selected in {"auto", "binance"}:
        if instrument.venue_id == "BINANCE:SPOT" and instrument.contract_type == "spot":
            return BinanceSpotProvider()
        if selected == "binance":
            raise MarketDataProviderError(
                "The free Binance adapter supports Binance Spot only; this instrument needs a separate free source."
            )
        raise ProviderConfigurationError(
            "No free public adapter is configured for this instrument yet. "
            "Use the historical CSV importer or wait for the relevant source adapter."
        )
    if selected in {"twelvedata", "paid", "paid-api"}:
        raise ProviderConfigurationError(
            "Paid market-data providers are disabled by the zero-subscription project requirement."
        )
    raise ProviderConfigurationError(f"Unsupported ORDERBLOCK_DATA_PROVIDER: {selected}")
