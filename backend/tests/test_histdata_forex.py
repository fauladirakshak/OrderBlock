import base64
import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.engine.histdata_forex import HistDataForexRequest, parse_histdata_forex_zip
from app.main import app

client = TestClient(app)


def make_zip(csv_text: str) -> str:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("DAT_ASCII_EURUSD_M1_201202.csv", csv_text)
        archive.writestr("status.txt", "source status metadata")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def test_histdata_m1_parses_fixed_est_and_preserves_bid_ohlcv():
    csv_text = (
        "20120201 000000;1.306600;1.306600;1.306560;1.306560;0\n"
        "20120201 000100;1.306570;1.306570;1.306470;1.306560;0\n"
    )
    result = parse_histdata_forex_zip(HistDataForexRequest(symbol="EUR/USD", zip_base64=make_zip(csv_text)))
    assert result.provider == "histdata-generic-ascii-m1-user-zip"
    assert result.timeframe == "1m"
    assert result.candle_count == 2
    assert result.candles[0].timestamp == "2012-02-01T05:00:00Z"
    assert result.candles[0].open == 1.3066
    assert result.candles[1].volume == 0


def test_histdata_rejects_invalid_rows_and_duplicate_timestamps():
    bad = "20120201 000000,1.1,1.2,1.0,1.1,0\n"
    with pytest.raises(ValueError, match="six semicolon-separated"):
        parse_histdata_forex_zip(HistDataForexRequest(symbol="EURUSD", zip_base64=make_zip(bad)))
    duplicate = (
        "20120201 000000;1.1;1.2;1.0;1.1;0\n"
        "20120201 000000;1.1;1.2;1.0;1.1;0\n"
    )
    with pytest.raises(ValueError, match="strictly increasing"):
        parse_histdata_forex_zip(HistDataForexRequest(symbol="EURUSD", zip_base64=make_zip(duplicate)))


def test_histdata_rejects_non_zip_payload():
    invalid = base64.b64encode(b"not a valid archive file").decode("ascii")
    with pytest.raises(ValueError, match="Unable to read HistData ZIP"):
        parse_histdata_forex_zip(HistDataForexRequest(symbol="EURUSD", zip_base64=invalid))


def test_histdata_api_returns_one_minute_forex_candles():
    response = client.post("/api/v1/market-data/import/histdata-forex", json={
        "symbol": "EUR/USD",
        "zip_base64": make_zip("20120201 000000;1.1;1.2;1.0;1.1;0\n"),
    })
    assert response.status_code == 200
    assert response.json()["market"] == "forex"
    assert response.json()["timeframe"] == "1m"
