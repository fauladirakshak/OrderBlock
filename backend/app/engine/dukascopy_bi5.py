"""Offline importer for classic Dukascopy hourly LZMA-compressed BI5 tick archives.

The parser deliberately requires an explicit price divisor because BI5 point
scales vary by instrument and source layout. It converts bid ticks to OHLC bars;
ask prices are used for validation but are not represented in the Candle model.
"""
from __future__ import annotations

import base64
import binascii
import io
import lzma
import math
import re
import struct
import zipfile
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field

from app.engine.historical_import import HistoricalImportResult
from app.engine.structure import Candle

_MEMBER = re.compile(
    r"(?:^|/)(?:[A-Z0-9._-]+/)?(?P<year>20\d{2})/(?P<month>0\d)/(?P<day>[0-3]\d)/(?P<hour>[0-2]\dh_ticks)\.bi5$",
    re.IGNORECASE,
)
_RECORD = struct.Struct(">IIIff")
_BUCKET_MINUTES = {"1m": 1, "5m": 5, "15m": 15, "1H": 60, "4H": 240, "1D": 1440}


class DukascopyBi5Request(BaseModel):
    symbol: str = Field(min_length=6, max_length=12, pattern=r"^[A-Za-z0-9._-]+$")
    zip_base64: str = Field(min_length=40, max_length=30_000_000)
    timeframe: str = Field(default="1m", pattern=r"^(1m|5m|15m|1H|4H|1D)$")
    price_divisor: float = Field(gt=0, le=1_000_000_000)


def _archive_hour(member_name: str, expected_symbol: str) -> datetime:
    match = _MEMBER.search(member_name.replace("\\", "/"))
    if not match:
        raise ValueError(
            "Each BI5 member path must include SYMBOL/YYYY/MM0/DD/HHh_ticks.bi5; "
            "month is zero-indexed as in Dukascopy's hourly datafeed layout."
        )
    # The symbol directory is checked separately to allow harmless parent folders.
    parts = member_name.replace("\\", "/").upper().split("/")
    if expected_symbol.upper() not in parts:
        raise ValueError(f"BI5 archive contains a file outside the {expected_symbol} instrument folder")
    year, month0, day, hour = (int(match.group(k)) for k in ("year", "month", "day", "hour"))
    if month0 > 11 or hour > 23:
        raise ValueError(f"Invalid Dukascopy date/hour in archive member: {member_name}")
    try:
        return datetime(year, month0 + 1, day, hour, tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError(f"Invalid Dukascopy date/hour in archive member: {member_name}") from exc


def parse_dukascopy_bi5_zip(request: DukascopyBi5Request) -> HistoricalImportResult:
    try:
        archive_bytes = base64.b64decode(request.zip_base64, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("zip_base64 must contain valid base64-encoded Dukascopy ZIP bytes") from exc
    if len(archive_bytes) > 20_000_000:
        raise ValueError("Dukascopy ZIP exceeds the 20 MB compressed upload limit")

    ticks: list[tuple[datetime, float, float, float]] = []
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            members = [item for item in archive.infolist() if not item.is_dir()]
            bi5_members = [item for item in members if item.filename.lower().endswith(".bi5")]
            if not bi5_members or len(bi5_members) > 744:
                raise ValueError("Dukascopy ZIP must contain between 1 and 744 hourly .bi5 files")
            if len(members) != len(bi5_members):
                raise ValueError("Dukascopy ZIP may contain only .bi5 tick files")
            if sum(item.file_size for item in bi5_members) > 100_000_000:
                raise ValueError("Dukascopy archive exceeds the 100 MB uncompressed limit")

            for member in sorted(bi5_members, key=lambda item: item.filename):
                hour_start = _archive_hour(member.filename, request.symbol)
                compressed = archive.read(member)
                if not compressed:
                    continue
                try:
                    decoder = lzma.LZMADecompressor()
                    raw = decoder.decompress(compressed, max_length=10_000_001)
                    if len(raw) > 10_000_000 or not decoder.eof:
                        raise ValueError(f"BI5 member {member.filename} exceeds the decompressed-size limit or is incomplete")
                except lzma.LZMAError as exc:
                    raise ValueError(f"Unable to decompress BI5 member {member.filename}") from exc
                if len(raw) % _RECORD.size:
                    raise ValueError(f"BI5 member {member.filename} has a truncated tick record")
                if len(raw) // _RECORD.size > 500_000:
                    raise ValueError(f"BI5 member {member.filename} exceeds the tick-count limit")

                previous_offset = -1
                for offset in range(0, len(raw), _RECORD.size):
                    milliseconds, ask_raw, bid_raw, ask_volume, bid_volume = _RECORD.unpack_from(raw, offset)
                    if milliseconds >= 3_600_000 or milliseconds <= previous_offset:
                        raise ValueError(f"BI5 member {member.filename} has invalid or unordered hour offsets")
                    if ask_raw <= 0 or bid_raw <= 0 or ask_raw < bid_raw:
                        raise ValueError(f"BI5 member {member.filename} has invalid ask/bid prices")
                    if not math.isfinite(ask_volume) or not math.isfinite(bid_volume) or ask_volume < 0 or bid_volume < 0:
                        raise ValueError(f"BI5 member {member.filename} has invalid tick volumes")
                    timestamp = hour_start + timedelta(milliseconds=milliseconds)
                    ticks.append((timestamp, bid_raw / request.price_divisor,
                                  ask_raw / request.price_divisor, ask_volume + bid_volume))
                    previous_offset = milliseconds
                    if len(ticks) > 2_000_000:
                        raise ValueError("Dukascopy archive exceeds the 2,000,000-tick import limit")
    except (zipfile.BadZipFile, OSError) as exc:
        raise ValueError(f"Unable to read Dukascopy ZIP: {exc}") from exc

    if not ticks:
        raise ValueError("Dukascopy ZIP contains no ticks in its BI5 files")
    ticks.sort(key=lambda item: item[0])
    if any(right[0] <= left[0] for left, right in zip(ticks, ticks[1:])):
        raise ValueError("Dukascopy BI5 files contain duplicate or out-of-order tick timestamps")

    bucket_ms = _BUCKET_MINUTES[request.timeframe] * 60_000
    buckets: dict[int, dict] = {}
    for timestamp, bid, ask, volume in ticks:
        epoch_ms = int(timestamp.timestamp() * 1000)
        bucket = epoch_ms // bucket_ms * bucket_ms
        if bucket not in buckets:
            buckets[bucket] = {"timestamp": datetime.fromtimestamp(bucket / 1000, tz=timezone.utc),
                               "open": bid, "high": bid, "low": bid, "close": bid,
                               "volume": volume, "spread_sum": ask - bid, "tick_count": 1}
        else:
            item = buckets[bucket]
            item["high"] = max(item["high"], bid)
            item["low"] = min(item["low"], bid)
            item["close"] = bid
            item["volume"] += volume
            item["spread_sum"] += ask - bid
            item["tick_count"] += 1

    candles = [
        Candle(timestamp=item["timestamp"].isoformat().replace("+00:00", "Z"),
               open=item["open"], high=item["high"], low=item["low"],
               close=item["close"], volume=item["volume"])
        for _, item in sorted(buckets.items())
    ]
    return HistoricalImportResult(
        provider="dukascopy-bi5-user-zip",
        is_synthetic=False,
        symbol=request.symbol.upper(),
        market="forex",
        timeframe=request.timeframe,
        timezone="UTC",
        candle_count=len(candles),
        candles=candles,
    )
