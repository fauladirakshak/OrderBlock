import base64
import io
import lzma
import struct
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.engine.dukascopy_bi5 import DukascopyBi5Request, parse_dukascopy_bi5_zip
from app.main import app

client = TestClient(app)


def make_zip(members):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members:
            archive.writestr(name, payload)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def tick(ms, ask, bid, ask_volume=1.0, bid_volume=2.0):
    return struct.pack(">IIIff", ms, ask, bid, ask_volume, bid_volume)


def request(payload, **overrides):
    values = dict(symbol="EURUSD", zip_base64=payload, timeframe="1m", price_divisor=100000)
    values.update(overrides)
    return DukascopyBi5Request(**values)


def test_dukascopy_bi5_aggregates_bid_ticks_to_utc_ohlcv():
    raw = tick(0, 110000, 100000) + tick(20_000, 112000, 105000) + tick(60_000, 111000, 108000)
    payload = make_zip([("EURUSD/2024/00/01/00h_ticks.bi5", lzma.compress(raw, format=lzma.FORMAT_ALONE))])
    result = parse_dukascopy_bi5_zip(request(payload, timeframe="1m"))
    assert result.provider == "dukascopy-bi5-user-zip"
    assert result.candle_count == 2
    assert result.candles[0].timestamp == "2024-01-01T00:00:00Z"
    assert (result.candles[0].open, result.candles[0].high, result.candles[0].low, result.candles[0].close) == (1.0, 1.05, 1.0, 1.05)
    assert result.candles[0].volume == 6.0


def test_dukascopy_bi5_resamples_to_five_minute_bars():
    raw = tick(0, 110000, 100000) + tick(60_000, 111000, 102000) + tick(299_000, 112000, 101000)
    payload = make_zip([("EURUSD/2024/00/01/00h_ticks.bi5", lzma.compress(raw, format=lzma.FORMAT_ALONE))])
    result = parse_dukascopy_bi5_zip(request(payload, timeframe="5m"))
    assert result.candle_count == 1
    assert result.candles[0].high == 1.02
    assert result.candles[0].close == 1.01


@pytest.mark.parametrize("path", [
    "EURUSD/2024/12/01/00h_ticks.bi5",
    "GBPUSD/2024/00/01/00h_ticks.bi5",
    "EURUSD/2024/00/01/24h_ticks.bi5",
])
def test_dukascopy_rejects_invalid_member_paths(path):
    payload = make_zip([(path, lzma.compress(tick(0, 110000, 100000), format=lzma.FORMAT_ALONE))])
    with pytest.raises(ValueError):
        parse_dukascopy_bi5_zip(request(payload))


def test_dukascopy_rejects_truncated_and_invalid_tick_records():
    truncated = make_zip([("EURUSD/2024/00/01/00h_ticks.bi5", lzma.compress(b"abc", format=lzma.FORMAT_ALONE))])
    with pytest.raises(ValueError, match="truncated"):
        parse_dukascopy_bi5_zip(request(truncated))
    crossed = make_zip([("EURUSD/2024/00/01/00h_ticks.bi5", lzma.compress(tick(0, 90000, 100000), format=lzma.FORMAT_ALONE))])
    with pytest.raises(ValueError, match="ask/bid"):
        parse_dukascopy_bi5_zip(request(crossed))


def test_dukascopy_import_api_returns_user_supplied_forex_series():
    payload = make_zip([("EURUSD/2024/00/01/00h_ticks.bi5", lzma.compress(tick(0, 110000, 100000), format=lzma.FORMAT_ALONE))])
    response = client.post("/api/v1/market-data/import/dukascopy-bi5", json={
        "symbol": "EURUSD", "zip_base64": payload, "timeframe": "1m", "price_divisor": 100000,
    })
    assert response.status_code == 200
    assert response.json()["market"] == "forex"
    assert response.json()["is_synthetic"] is False
