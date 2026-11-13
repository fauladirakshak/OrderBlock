"""Timezone-aware market-session summaries for supplied historical candles.

The defaults are broad research windows, not canonical ICT killzones or exchange
holiday calendars. IANA timezones handle daylight-saving transitions.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, model_validator

from app.engine.markets import get_instrument
from app.engine.structure import Candle


class CustomSessionWindow(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    timezone: str = Field(min_length=1, max_length=64)
    start: str
    end: str

    @model_validator(mode="after")
    def validate_window(self) -> "CustomSessionWindow":
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"Unknown IANA session timezone: {self.timezone}") from exc
        start_minute = _minutes(self.start)
        end_minute = _minutes(self.end, allow_24=True)
        if start_minute == end_minute:
            raise ValueError("custom session start and end must differ")
        return self


class SessionAnalysisRequest(BaseModel):
    market: Literal["forex", "crypto", "stocks"]
    symbol: str = Field(min_length=1, max_length=32)
    candles: list[Candle] = Field(min_length=1, max_length=5000)
    custom_windows: list[CustomSessionWindow] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def validate_candle_order(self) -> "SessionAnalysisRequest":
        stamps = []
        for candle in self.candles:
            try:
                stamp = datetime.fromisoformat(candle.timestamp.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("candle timestamps must be ISO-8601 values") from exc
            if stamp.tzinfo is None:
                raise ValueError("candle timestamps must include a timezone")
            stamps.append(stamp.astimezone(timezone.utc))
        if any(right <= left for left, right in zip(stamps, stamps[1:])):
            raise ValueError("candle timestamps must be strictly increasing")
        names = [window.name.casefold() for window in self.custom_windows]
        if len(names) != len(set(names)):
            raise ValueError("custom session window names must be unique")
        return self

class SessionSummary(BaseModel):
    name: str
    session_date: str
    timezone: str
    start_timestamp: str
    end_timestamp: str
    open: float
    high: float
    low: float
    close: float
    range_points: float
    range_pct: float
    volume: float
    candle_count: int


class SessionAnalysis(BaseModel):
    market: str
    symbol: str
    session_model: str
    instrument_timezone: str
    latest_candle_timestamp: str
    latest_candle_sessions: list[str]
    sessions: list[SessionSummary]
    notes: list[str]


def _minutes(value: str, allow_24: bool = False) -> int:
    if allow_24 and value == "24:00":
        return 1440
    try:
        hour_text, minute_text = value.split(":")
        hour, minute = int(hour_text), int(minute_text)
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"Invalid session time: {value}; expected HH:MM") from exc
    if hour > 23 or minute > 59:
        raise ValueError(f"Invalid session time: {value}; expected HH:MM")
    return hour * 60 + minute


def _session_windows(request: SessionAnalysisRequest):
    if request.market == "forex":
        return [
            ("Asia", "Asia/Tokyo", "09:00", "18:00"),
            ("London", "Europe/London", "08:00", "17:00"),
            ("New York", "America/New_York", "08:00", "17:00"),
        ], "overlapping regional FX sessions"
    if request.market == "crypto":
        return [("UTC Daily", "Etc/UTC", "00:00", "24:00")], "24x7 UTC daily buckets"

    try:
        instrument = get_instrument(request.symbol)
    except ValueError as exc:
        raise ValueError(f"Unknown stock/index instrument: {request.symbol}") from exc
    if not instrument.session_open or not instrument.session_close:
        raise ValueError(f"No regular-session hours are configured for {request.symbol}")
    return [(f"{instrument.venue} Regular", instrument.timezone,
             instrument.session_open, instrument.session_close)], "exchange regular session"


def analyze_sessions(request: SessionAnalysisRequest) -> SessionAnalysis:
    windows, session_model = _session_windows(request)
    if request.custom_windows:
        windows = windows + [
            (window.name, window.timezone, window.start, window.end)
            for window in request.custom_windows
        ]
        session_model += " + user-configured windows"
    parsed_windows = []
    for name, zone_name, start_text, end_text in windows:
        try:
            zone = ZoneInfo(zone_name)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"Unknown IANA session timezone: {zone_name}") from exc
        parsed_windows.append((name, zone_name, zone, _minutes(start_text),
                               _minutes(end_text, allow_24=True)))

    groups: dict[tuple[str, str], list[tuple[datetime, Candle]]] = {}
    latest_sessions: list[str] = []
    latest = datetime.fromisoformat(request.candles[-1].timestamp.replace("Z", "+00:00"))
    for index, candle in enumerate(request.candles):
        stamp = datetime.fromisoformat(candle.timestamp.replace("Z", "+00:00"))
        for name, zone_name, zone, start_minute, end_minute in parsed_windows:
            local = stamp.astimezone(zone)
            minute = local.hour * 60 + local.minute
            if start_minute <= minute < end_minute:
                session_date = local.date()
            elif end_minute < start_minute and (minute >= start_minute or minute < end_minute):
                session_date = local.date() if minute >= start_minute else (local.date() - timedelta(days=1))
            else:
                continue
            groups.setdefault((name, session_date.isoformat()), []).append((stamp, candle))
            if index == len(request.candles) - 1:
                latest_sessions.append(name)

    summaries: list[SessionSummary] = []
    for (name, session_date), rows in sorted(groups.items(), key=lambda item: (item[0][1], item[0][0])):
        bars = [item[1] for item in rows]
        high = max(item.high for item in bars)
        low = min(item.low for item in bars)
        opening = bars[0].open
        summaries.append(SessionSummary(
            name=name,
            session_date=session_date,
            timezone=next(item[1] for item in parsed_windows if item[0] == name),
            start_timestamp=rows[0][0].astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            end_timestamp=rows[-1][0].astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            open=opening,
            high=high,
            low=low,
            close=bars[-1].close,
            range_points=high - low,
            range_pct=(high - low) / opening * 100 if opening else 0.0,
            volume=sum(item.volume for item in bars),
            candle_count=len(bars),
        ))

    try:
        instrument = get_instrument(request.symbol)
        instrument_timezone = instrument.timezone
    except ValueError:
        instrument_timezone = "Etc/UTC" if request.market == "crypto" else parsed_windows[0][1]

    return SessionAnalysis(
        market=request.market,
        symbol=request.symbol,
        session_model=session_model,
        instrument_timezone=instrument_timezone,
        latest_candle_timestamp=latest.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        latest_candle_sessions=latest_sessions,
        sessions=summaries,
        notes=[
            "Session windows are descriptive research groupings, not entry signals or canonical ICT killzones.",
            "IANA timezone rules are applied per candle, including daylight-saving changes.",
            "Forex regional sessions overlap; one candle may contribute to more than one session summary.",
            "Only the candles supplied in this request are summarized; incomplete history produces incomplete session highs and lows.",
            "Exchange holidays and special sessions are not inferred. Equity summaries use the configured regular-session clock only.",
        ],
    )
