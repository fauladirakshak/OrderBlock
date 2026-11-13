"""Offline importer for HistData Generic ASCII M1 Forex ZIP files."""
from __future__ import annotations

import base64
import binascii
import csv
import io
import zipfile
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field, ValidationError

from app.engine.historical_import import HistoricalImportResult
from app.engine.structure import Candle


class HistDataForexRequest(BaseModel):
    symbol: str = Field(min_length=3, max_length=16)
    zip_base64: str = Field(min_length=40, max_length=30_000_000)


def parse_histdata_forex_zip(request: HistDataForexRequest) -> HistoricalImportResult:
    try:
        archive_bytes = base64.b64decode(request.zip_base64, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("zip_base64 must contain valid base64-encoded HistData ZIP bytes") from exc
    if len(archive_bytes) > 20_000_000:
        raise ValueError("HistData ZIP exceeds the 20 MB compressed upload limit")

    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            members = [item for item in archive.infolist() if not item.is_dir()]
            csv_members = [item for item in members if item.filename.lower().endswith(".csv")]
            if len(members) > 3 or len(csv_members) != 1:
                raise ValueError("HistData ZIP must contain exactly one CSV plus optional status metadata")
            member = csv_members[0]
            if member.file_size > 50_000_000:
                raise ValueError("HistData CSV exceeds the 50 MB uncompressed limit")
            csv_text = archive.read(member).decode("utf-8-sig")
    except (zipfile.BadZipFile, UnicodeDecodeError, OSError) as exc:
        raise ValueError(f"Unable to read HistData ZIP: {exc}") from exc

    # HistData documents its Generic ASCII M1 timestamps as fixed EST (UTC-5)
    # without DST. Etc/GMT+5 intentionally means UTC-5 in IANA's reversed sign.
    source_zone = timezone(timedelta(hours=-5))
    candles: list[Candle] = []
    try:
        reader = csv.reader(io.StringIO(csv_text), delimiter=";")
        for row_number, row in enumerate(reader, start=1):
            if not row or not any(field.strip() for field in row):
                continue
            if len(row) != 6:
                raise ValueError(f"expected six semicolon-separated columns, found {len(row)}")
            stamp = datetime.strptime(row[0].strip(), "%Y%m%d %H%M%S").replace(tzinfo=source_zone)
            candles.append(Candle(
                timestamp=stamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                open=float(row[1]), high=float(row[2]), low=float(row[3]),
                close=float(row[4]), volume=float(row[5] or 0),
            ))
            if len(candles) > 500_000:
                raise ValueError("HistData ZIP exceeds the 500,000-candle import limit")
    except (ValueError, TypeError, ValidationError) as exc:
        raise ValueError(f"Invalid HistData M1 row {row_number}: {exc}") from exc

    if not candles:
        raise ValueError("HistData ZIP contains no M1 candle rows")
    stamps = [datetime.fromisoformat(item.timestamp.replace("Z", "+00:00")) for item in candles]
    if any(right <= left for left, right in zip(stamps, stamps[1:])):
        raise ValueError("HistData M1 timestamps must be strictly increasing with no duplicates")

    return HistoricalImportResult(
        provider="histdata-generic-ascii-m1-user-zip",
        is_synthetic=False,
        symbol=request.symbol.strip().upper(),
        market="forex",
        timeframe="1m",
        timezone="EST fixed UTC-5 (no daylight-saving adjustment)",
        candle_count=len(candles),
        candles=candles,
    )
