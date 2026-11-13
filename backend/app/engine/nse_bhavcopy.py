"""NSE UDiFF CM daily bhavcopy ZIP importer.

This is an offline parser for a user-downloaded official NSE report. It does not
scrape NSE, bypass access controls, or claim redistribution rights.
"""
from __future__ import annotations

import base64
import csv
import io
import zipfile
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from app.engine.historical_import import HistoricalImportResult
from app.engine.structure import Candle


class NseBhavcopyRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    series: str = Field(default="EQ", min_length=1, max_length=4)
    zip_base64: str = Field(min_length=40, max_length=30_000_000)


def parse_nse_udiff_zip(request: NseBhavcopyRequest) -> HistoricalImportResult:
    try:
        archive_bytes = base64.b64decode(request.zip_base64, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise ValueError("zip_base64 must contain a valid base64-encoded NSE ZIP file") from exc
    if len(archive_bytes) > 20_000_000:
        raise ValueError("NSE ZIP exceeds the 20 MB compressed upload limit")

    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            members = [item for item in archive.infolist() if not item.is_dir()]
            csv_members = [item for item in members if item.filename.lower().endswith(".csv")]
            if len(members) != 1 or len(csv_members) != 1:
                raise ValueError("NSE UDiFF ZIP must contain exactly one CSV data file")
            member = csv_members[0]
            if member.file_size > 50_000_000:
                raise ValueError("NSE CSV exceeds the 50 MB uncompressed limit")
            csv_text = archive.read(member).decode("utf-8-sig")
    except (zipfile.BadZipFile, UnicodeDecodeError, OSError) as exc:
        raise ValueError(f"Unable to read NSE UDiFF ZIP: {exc}") from exc

    reader = csv.DictReader(io.StringIO(csv_text))
    required = {"TradDt", "TckrSymb", "SctySrs", "OpnPric", "HghPric", "LwPric", "ClsPric", "TtlTradgVol"}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        raise ValueError("CSV is not a supported NSE UDiFF CM bhavcopy; required headers are missing")

    symbol = request.symbol.strip().upper()
    series = request.series.strip().upper()
    candles: list[Candle] = []
    for row_number, row in enumerate(reader, start=2):
        if (row.get("TckrSymb") or "").strip().upper() != symbol:
            continue
        if (row.get("SctySrs") or "").strip().upper() != series:
            continue
        try:
            trade_date = date.fromisoformat(row["TradDt"].strip())
            # The bhavcopy is a daily EOD record. Midnight IST is a date label,
            # not a claim that a trade occurred at midnight.
            stamp = datetime.combine(trade_date, time.min, tzinfo=ZoneInfo("Asia/Kolkata"))
            candles.append(Candle(
                timestamp=stamp.astimezone(ZoneInfo("UTC")).isoformat().replace("+00:00", "Z"),
                open=float(row["OpnPric"]),
                high=float(row["HghPric"]),
                low=float(row["LwPric"]),
                close=float(row["ClsPric"]),
                volume=float(row["TtlTradgVol"] or 0),
            ))
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError(f"Invalid NSE UDiFF row {row_number}: {exc}") from exc

    if not candles:
        raise ValueError(f"No NSE UDiFF rows found for {symbol} series {series}")
    stamps = [datetime.fromisoformat(item.timestamp.replace("Z", "+00:00")) for item in candles]
    if any(right <= left for left, right in zip(stamps, stamps[1:])):
        raise ValueError("NSE UDiFF rows contain duplicate or out-of-order trading dates")

    return HistoricalImportResult(
        provider="nse-udiff-cm-bhavcopy-user-zip",
        is_synthetic=False,
        symbol=symbol,
        market="stocks",
        timeframe="1D",
        timezone="Asia/Kolkata",
        candle_count=len(candles),
        candles=candles,
    )
