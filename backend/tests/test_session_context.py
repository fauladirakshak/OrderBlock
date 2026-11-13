import pytest
from fastapi.testclient import TestClient

from app.engine.session_context import SessionAnalysisRequest, analyze_sessions
from app.engine.structure import Candle
from app.main import app

client = TestClient(app)


def bars(rows):
    return [Candle(timestamp=stamp, open=o, high=h, low=l, close=c, volume=v)
            for stamp, o, h, l, c, v in rows]


def test_forex_sessions_use_iana_timezones_and_overlap():
    data = bars([
        ("2026-01-15T08:00:00Z", 1.1, 1.11, 1.09, 1.105, 10),
        ("2026-01-15T12:00:00Z", 1.105, 1.12, 1.10, 1.115, 20),
        ("2026-01-15T16:00:00Z", 1.115, 1.13, 1.11, 1.12, 30),
    ])
    result = analyze_sessions(SessionAnalysisRequest(market="forex", symbol="EUR/USD", candles=data))
    names = {item.name for item in result.sessions}
    assert {"Asia", "London", "New York"}.issubset(names)
    assert result.latest_candle_sessions == ["London", "New York"]
    london = next(item for item in result.sessions if item.name == "London")
    assert london.candle_count == 3
    assert london.high == 1.13


def test_london_timezone_observes_daylight_saving():
    winter = bars([("2026-01-15T08:00:00Z", 1, 1.1, 0.9, 1.05, 1)])
    summer = bars([("2026-07-15T07:00:00Z", 1, 1.1, 0.9, 1.05, 1)])
    a = analyze_sessions(SessionAnalysisRequest(market="forex", symbol="EUR/USD", candles=winter))
    b = analyze_sessions(SessionAnalysisRequest(market="forex", symbol="EUR/USD", candles=summer))
    assert any(item.name == "London" for item in a.sessions)
    assert any(item.name == "London" for item in b.sessions)


def test_nse_regular_session_excludes_preopen_and_after_close():
    data = bars([
        ("2026-11-10T03:40:00Z", 100, 101, 99, 100, 5),  # 09:10 IST
        ("2026-11-10T03:45:00Z", 100, 102, 99, 101, 10), # 09:15 IST
        ("2026-11-10T06:30:00Z", 101, 103, 100, 102, 20),
        ("2026-11-10T09:55:00Z", 102, 104, 101, 103, 30),
    ])
    result = analyze_sessions(SessionAnalysisRequest(market="stocks", symbol="RELIANCE", candles=data))
    assert len(result.sessions) == 1
    assert result.sessions[0].name == "NSE Regular"
    assert result.sessions[0].candle_count == 3
    assert result.sessions[0].timezone == "Asia/Kolkata"


def test_crypto_groups_by_utc_calendar_day():
    data = bars([
        ("2026-11-10T23:55:00Z", 100, 101, 99, 100, 1),
        ("2026-11-11T00:00:00Z", 100, 102, 98, 101, 2),
    ])
    result = analyze_sessions(SessionAnalysisRequest(market="crypto", symbol="BTC/USDT", candles=data))
    assert [item.session_date for item in result.sessions] == ["2026-11-10", "2026-11-11"]
    assert result.session_model == "24x7 UTC daily buckets"


def test_session_api_returns_market_context():
    data = bars([("2026-11-10T03:45:00Z", 100, 102, 99, 101, 10)])
    response = client.post("/api/v1/analysis/sessions", json={
        "market": "stocks", "symbol": "RELIANCE",
        "candles": [item.model_dump() for item in data],
    })
    assert response.status_code == 200
    assert response.json()["session_model"] == "exchange regular session"


def test_session_analysis_rejects_unordered_timestamps():
    data = bars([
        ("2026-11-10T03:45:00Z", 100, 102, 99, 101, 10),
        ("2026-11-10T03:45:00Z", 101, 103, 100, 102, 10),
    ])
    with pytest.raises(ValueError, match="strictly increasing"):
        SessionAnalysisRequest(market="stocks", symbol="RELIANCE", candles=data)



def test_custom_session_window_uses_configured_iana_timezone():
    data = bars([
        ("2026-07-15T07:00:00Z", 100, 103, 99, 102, 10),  # 08:00 BST
        ("2026-07-15T08:00:00Z", 102, 104, 101, 103, 20),  # 09:00 BST
        ("2026-07-15T10:00:00Z", 103, 105, 102, 104, 30),  # 11:00 BST
    ])
    request = SessionAnalysisRequest(
        market="forex", symbol="EUR/USD", candles=data,
        custom_windows=[{"name": "London Open Study", "timezone": "Europe/London",
                         "start": "08:00", "end": "10:00"}],
    )
    result = analyze_sessions(request)
    custom = [item for item in result.sessions if item.name == "London Open Study"]
    assert len(custom) == 1
    assert custom[0].candle_count == 2
    assert custom[0].timezone == "Europe/London"
    assert "user-configured windows" in result.session_model


def test_custom_session_window_rejects_invalid_timezone_and_duplicate_names():
    data = bars([("2026-11-10T03:45:00Z", 100, 102, 99, 101, 10)])
    with pytest.raises(ValueError, match="Unknown IANA session timezone"):
        SessionAnalysisRequest(
            market="forex", symbol="EUR/USD", candles=data,
            custom_windows=[{"name": "Custom", "timezone": "Mars/Olympus",
                             "start": "08:00", "end": "10:00"}],
        )
    with pytest.raises(ValueError, match="names must be unique"):
        SessionAnalysisRequest(
            market="forex", symbol="EUR/USD", candles=data,
            custom_windows=[
                {"name": "Window", "timezone": "Europe/London", "start": "08:00", "end": "10:00"},
                {"name": "window", "timezone": "America/New_York", "start": "08:00", "end": "10:00"},
            ],
        )


def test_custom_session_window_api():
    data = bars([("2026-11-10T08:00:00Z", 100, 102, 99, 101, 10)])
    response = client.post("/api/v1/analysis/sessions", json={
        "market": "forex", "symbol": "EUR/USD",
        "candles": [item.model_dump() for item in data],
        "custom_windows": [{"name": "User Killzone Study", "timezone": "Europe/London",
                            "start": "08:00", "end": "10:00"}],
    })
    assert response.status_code == 200
    assert any(item["name"] == "User Killzone Study" for item in response.json()["sessions"])



def test_custom_session_window_cannot_shadow_default_session_name():
    data = bars([("2026-11-10T08:00:00Z", 100, 102, 99, 101, 10)])
    request = SessionAnalysisRequest(
        market="forex", symbol="EUR/USD", candles=data,
        custom_windows=[{"name": "london", "timezone": "America/New_York",
                         "start": "08:00", "end": "10:00"}],
    )
    with pytest.raises(ValueError, match="unique across default and custom"):
        analyze_sessions(request)
