"""Validated CSV import for user-supplied historical OHLCV data.

Accepted headers are timestamp/date/datetime plus open, high, low, close,
and optional volume. Naive timestamps require an explicit IANA timezone.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, ValidationError

from app.engine.structure import Candle


class HistoricalImportRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    market: str = Field(pattern=r"^(forex|crypto|stocks)$")
    timeframe: str = Field(pattern=r"^(5m|15m|1H|4H|1D|1W)$")
    csv_text: str = Field(min_length=20, max_length=20_000_000)
    timezone: str = "UTC"


class HistoricalImportResult(BaseModel):
    provider: str = "user-csv-import"
    is_synthetic: bool = False
    symbol: str
    market: str
    timeframe: str
    timezone: str
    candle_count: int
    candles: list[Candle]


def _utc(value: str, zone: ZoneInfo) -> str:
    raw = value.strip()
    parsed: datetime
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Invalid candle timestamp: {raw}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=zone)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_historical_csv(csv_text: str, source_timezone: str = "UTC") -> list[Candle]:
    try:
        zone = ZoneInfo(source_timezone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"Unknown IANA timezone: {source_timezone}") from exc

    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        raise ValueError("CSV must include a header row.")
    headers = {name.strip().lower(): name for name in reader.fieldnames if name}
    time_key = next((headers[k] for k in ("timestamp", "datetime", "date", "time") if k in headers), None)
    required = {"open", "high", "low", "close"}
    missing = required - set(headers)
    if time_key is None or missing:
        raise ValueError("CSV requires timestamp/date and open, high, low, close columns.")

    candles: list[Candle] = []
    try:
        for row_number, row in enumerate(reader, start=2):
            if not row or not any((v or "").strip() for v in row.values()):
                continue
            timestamp = _utc(row.get(time_key, ""), zone)
            volume_text = row.get(headers["volume"], "0") if "volume" in headers else "0"
            candles.append(Candle(
                timestamp=timestamp,
                open=float(row[headers["open"]]),
                high=float(row[headers["high"]]),
                low=float(row[headers["low"]]),
                close=float(row[headers["close"]]),
                volume=float(volume_text or 0),
            ))
    except (ValueError, TypeError, ValidationError) as exc:
        raise ValueError(f"Invalid CSV candle at row {row_number}: {exc}") from exc

    if not candles:
        raise ValueError("CSV contains no candle rows.")
    stamps = [datetime.fromisoformat(c.timestamp.replace("Z", "+00:00")) for c in candles]
    if any(b <= a for a, b in zip(stamps, stamps[1:])):
        raise ValueError("CSV timestamps must be strictly increasing with no duplicates.")
    return candles
