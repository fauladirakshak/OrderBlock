import base64
import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.engine.nse_bhavcopy import NseBhavcopyRequest, parse_nse_udiff_zip
from app.main import app

client = TestClient(app)


def make_zip(csv_text: str) -> str:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("BhavCopy_NSE_CM_sample.csv", csv_text)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


HEADER = "TradDt,TckrSymb,SctySrs,OpnPric,HghPric,LwPric,ClsPric,TtlTradgVol\n"


def test_nse_udiff_zip_filters_symbol_and_series_and_normalizes_date():
    csv_text = HEADER + (
        "2026-11-10,RELIANCE,EQ,1450,1470,1440,1460,100000\n"
        "2026-11-10,RELIANCE,BE,1450,1470,1440,1460,1000\n"
        "2026-11-11,TCS,EQ,3000,3050,2990,3030,50000\n"
        "2026-11-11,RELIANCE,EQ,1460,1480,1455,1475,120000\n"
    )
    result = parse_nse_udiff_zip(NseBhavcopyRequest(symbol="reliance", zip_base64=make_zip(csv_text)))
    assert result.provider == "nse-udiff-cm-bhavcopy-user-zip"
    assert result.candle_count == 2
    assert result.candles[0].timestamp == "2026-11-09T18:30:00Z"
    assert result.candles[1].close == 1475
    assert result.candles[1].volume == 120000


def test_nse_udiff_rejects_wrong_zip_and_missing_symbol():
    with pytest.raises(ValueError, match="Unable to read NSE UDiFF ZIP"):
        parse_nse_udiff_zip(NseBhavcopyRequest(symbol="TCS", zip_base64=base64.b64encode(b"this is definitely not a zip file").decode()))
    with pytest.raises(ValueError, match="No NSE UDiFF rows"):
        parse_nse_udiff_zip(NseBhavcopyRequest(symbol="INFY", zip_base64=make_zip(HEADER + "2026-11-10,TCS,EQ,1,2,1,2,10\n")))


def test_nse_udiff_rejects_wrong_format_and_duplicate_dates():
    with pytest.raises(ValueError, match="required headers"):
        parse_nse_udiff_zip(NseBhavcopyRequest(symbol="TCS", zip_base64=make_zip("Symbol,Open,High,Low,Close\n")))
    duplicate = HEADER + (
        "2026-11-10,TCS,EQ,10,12,9,11,100\n"
        "2026-11-10,TCS,EQ,11,13,10,12,200\n"
    )
    with pytest.raises(ValueError, match="duplicate or out-of-order"):
        parse_nse_udiff_zip(NseBhavcopyRequest(symbol="TCS", zip_base64=make_zip(duplicate)))


def test_nse_udiff_api_returns_daily_candles():
    response = client.post("/api/v1/market-data/import/nse-udiff", json={
        "symbol": "TCS",
        "zip_base64": make_zip(HEADER + "2026-11-10,TCS,EQ,3000,3050,2990,3030,50000\n"),
    })
    assert response.status_code == 200
    assert response.json()["timeframe"] == "1D"
    assert response.json()["market"] == "stocks"
