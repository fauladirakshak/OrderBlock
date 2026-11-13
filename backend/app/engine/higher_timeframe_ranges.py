"""Higher-timeframe dealing-range context from separately supplied closed candles.

The API deliberately does not resample lower-timeframe candles: callers must
supply genuine, completed candles for each higher timeframe.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.engine.dealing_range import DealingRangeRequest, DealingRangeResult, analyze_dealing_range
from app.engine.structure import Candle

Timeframe = Literal["1m", "5m", "15m", "30m", "1H", "4H", "1D", "1W"]
_TIMEFRAME_MINUTES = {
    "1m": 1, "5m": 5, "15m": 15, "30m": 30,
    "1H": 60, "4H": 240, "1D": 1440, "1W": 10080,
}


class HigherTimeframeSeries(BaseModel):
    timeframe: Timeframe
    candles: list[Candle] = Field(min_length=5, max_length=5000)


class HigherTimeframeRangeRequest(BaseModel):
    primary_timeframe: Timeframe
    primary_candles: list[Candle] = Field(min_length=2, max_length=5000)
    higher_timeframes: list[HigherTimeframeSeries] = Field(min_length=1, max_length=4)
    pivot: int = Field(default=2, ge=1, le=10)
    equilibrium_band_pct: float = Field(default=5.0, ge=0, le=25)

    @model_validator(mode="after")
    def validate_series(self) -> "HigherTimeframeRangeRequest":
        primary_minutes = _TIMEFRAME_MINUTES[self.primary_timeframe]
        if not self.higher_timeframes:
            raise ValueError("at least one higher timeframe is required")
        seen: set[str] = set()
        primary_stamps = [_utc(c.timestamp) for c in self.primary_candles]
        if any(b <= a for a, b in zip(primary_stamps, primary_stamps[1:])):
            raise ValueError("primary candle timestamps must be strictly increasing")
        primary_end = primary_stamps[-1]
        for series in self.higher_timeframes:
            if series.timeframe in seen:
                raise ValueError("higher timeframe entries must be unique")
            seen.add(series.timeframe)
            if _TIMEFRAME_MINUTES[series.timeframe] <= primary_minutes:
                raise ValueError("every supplied context timeframe must exceed the primary timeframe")
            stamps = [_utc(c.timestamp) for c in series.candles]
            if any(b <= a for a, b in zip(stamps, stamps[1:])):
                raise ValueError(f"{series.timeframe} candle timestamps must be strictly increasing")
            if stamps[-1] > primary_end:
                raise ValueError(f"{series.timeframe} candles cannot extend beyond the primary chart's latest timestamp")
        return self


def _utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("candle timestamps must be ISO-8601 values") from exc
    if parsed.tzinfo is None:
        raise ValueError("candle timestamps must include a timezone")
    return parsed.astimezone(timezone.utc)


class HigherTimeframeRangeItem(BaseModel):
    timeframe: Timeframe
    latest_candle_timestamp: str
    analysis: DealingRangeResult


class HigherTimeframeRangeResult(BaseModel):
    primary_timeframe: Timeframe
    primary_latest_timestamp: str
    contexts: list[HigherTimeframeRangeItem]
    notes: list[str]


def analyze_higher_timeframe_ranges(request: HigherTimeframeRangeRequest) -> HigherTimeframeRangeResult:
    contexts = []
    for series in sorted(request.higher_timeframes, key=lambda item: _TIMEFRAME_MINUTES[item.timeframe]):
        analysis = analyze_dealing_range(DealingRangeRequest(
            candles=series.candles,
            pivot=request.pivot,
            equilibrium_band_pct=request.equilibrium_band_pct,
        ))
        contexts.append(HigherTimeframeRangeItem(
            timeframe=series.timeframe,
            latest_candle_timestamp=series.candles[-1].timestamp,
            analysis=analysis,
        ))
    return HigherTimeframeRangeResult(
        primary_timeframe=request.primary_timeframe,
        primary_latest_timestamp=request.primary_candles[-1].timestamp,
        contexts=contexts,
        notes=[
            "Each context range is calculated independently from the separately supplied higher-timeframe candles.",
            "No lower-timeframe resampling or synthetic higher-timeframe candle construction is performed.",
            "Supply completed higher-timeframe candles only; the API validates timestamp ordering and prevents future-dated context, but cannot independently verify exchange candle-close status.",
            "Swing points are only eligible after right-side confirmation; the final supplied candle cannot confirm a pivot and use it simultaneously.",
            "Premium/discount labels are geometric context, not forecasts or trade signals.",
        ],
    )
