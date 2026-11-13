"""Multi-timeframe order-block and fair-value-gap context.

Each timeframe is analysed independently. No lower-timeframe resampling is
performed and context candles later than the primary chart are rejected.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.engine.structure import Candle
from app.engine.zones import OrderBlock, FairValueGap, analyze_zones

Timeframe = Literal["5m", "15m", "1H", "4H", "1D", "1W"]
TIMEFRAME_RANK = {"5m": 1, "15m": 2, "1H": 3, "4H": 4, "1D": 5, "1W": 6}


def _parse_utc(value: str) -> datetime:
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("candle timestamps must be ISO-8601 values") from exc
    if stamp.tzinfo is None:
        raise ValueError("candle timestamps must include a timezone")
    return stamp.astimezone(timezone.utc)


class TimeframeZoneSeries(BaseModel):
    timeframe: Timeframe
    candles: list[Candle] = Field(min_length=5, max_length=5000)


class HigherTimeframeZonesRequest(BaseModel):
    primary_timeframe: Timeframe
    primary_candles: list[Candle] = Field(min_length=2, max_length=5000)
    higher_timeframes: list[TimeframeZoneSeries] = Field(min_length=1, max_length=4)
    pivot: int = Field(default=2, ge=1, le=10)
    max_zones_per_type: int = Field(default=8, ge=1, le=30)

    @model_validator(mode="after")
    def validate_series(self) -> "HigherTimeframeZonesRequest":
        primary_rank = TIMEFRAME_RANK[self.primary_timeframe]
        primary_stamps = [_parse_utc(c.timestamp) for c in self.primary_candles]
        if any(right <= left for left, right in zip(primary_stamps, primary_stamps[1:])):
            raise ValueError("primary candle timestamps must be strictly increasing")
        primary_end = primary_stamps[-1]
        seen: set[str] = set()
        for series in self.higher_timeframes:
            if series.timeframe in seen:
                raise ValueError("higher timeframe entries must be unique")
            seen.add(series.timeframe)
            if TIMEFRAME_RANK[series.timeframe] <= primary_rank:
                raise ValueError("every context timeframe must exceed the primary timeframe")
            stamps = [_parse_utc(c.timestamp) for c in series.candles]
            if any(right <= left for left, right in zip(stamps, stamps[1:])):
                raise ValueError(f"{series.timeframe} candle timestamps must be strictly increasing")
            if stamps[-1] > primary_end:
                raise ValueError(f"{series.timeframe} candles cannot extend beyond the primary chart's latest timestamp")
        return self


class TimeframeZoneContext(BaseModel):
    timeframe: Timeframe
    latest_candle_timestamp: str
    order_blocks: list[OrderBlock]
    fair_value_gaps: list[FairValueGap]
    notes: list[str]


class HigherTimeframeZonesResult(BaseModel):
    primary_timeframe: Timeframe
    primary_latest_timestamp: str
    contexts: list[TimeframeZoneContext]
    notes: list[str]


def analyze_higher_timeframe_zones(request: HigherTimeframeZonesRequest) -> HigherTimeframeZonesResult:
    contexts = []
    for series in sorted(request.higher_timeframes, key=lambda item: TIMEFRAME_RANK[item.timeframe]):
        zones = analyze_zones(series.candles, pivot=request.pivot)
        contexts.append(TimeframeZoneContext(
            timeframe=series.timeframe,
            latest_candle_timestamp=series.candles[-1].timestamp,
            order_blocks=zones.order_blocks[-request.max_zones_per_type:],
            fair_value_gaps=zones.fair_value_gaps[-request.max_zones_per_type:],
            notes=[
                "Order blocks are the last opposing candle before a confirmed close-based structure break.",
                "Fair value gaps use the three-candle non-overlap rule.",
                "Mitigation and invalidation describe later candles in this same timeframe only.",
            ],
        ))
    return HigherTimeframeZonesResult(
        primary_timeframe=request.primary_timeframe,
        primary_latest_timestamp=request.primary_candles[-1].timestamp,
        contexts=contexts,
        notes=[
            "Each timeframe is analysed independently from its own supplied OHLC candles.",
            "No timeframe resampling or synthetic candle construction is performed.",
            "Only completed, correctly aligned higher-timeframe candles should be supplied; candle-close status is the provider's responsibility.",
            "These are deterministic pattern observations, not evidence of institutional orders or trade signals.",
        ],
    )
