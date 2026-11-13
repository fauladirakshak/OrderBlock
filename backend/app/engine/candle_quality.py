"""Historical candle-series quality audit; gaps are observations, not assumed missing bars."""
from __future__ import annotations

from datetime import datetime, timezone
from statistics import median
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.engine.structure import Candle

TIMEFRAME_SECONDS = {"5m": 300, "15m": 900, "1H": 3600, "4H": 14400, "1D": 86400, "1W": 604800}


class CandleQualityRequest(BaseModel):
    candles: list[Candle] = Field(min_length=2, max_length=5000)
    timeframe: Literal["5m", "15m", "1H", "4H", "1D", "1W"]
    gap_tolerance: float = Field(default=1.5, ge=1.0, le=10.0)

    @model_validator(mode="after")
    def validate_series(self) -> "CandleQualityRequest":
        stamps = []
        for candle in self.candles:
            try:
                parsed = datetime.fromisoformat(candle.timestamp.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("candle timestamps must be ISO-8601 values") from exc
            if parsed.tzinfo is None:
                raise ValueError("candle timestamps must include a timezone")
            stamps.append(parsed.astimezone(timezone.utc))
        if any(right <= left for left, right in zip(stamps, stamps[1:])):
            raise ValueError("candle timestamps must be strictly increasing")
        return self


class CandleGap(BaseModel):
    after_timestamp: str
    before_timestamp: str
    elapsed_seconds: int
    expected_intervals: float
    estimated_intervening_bars: int


class CandleQualityResult(BaseModel):
    candle_count: int
    timeframe: str
    expected_interval_seconds: int
    first_timestamp: str
    last_timestamp: str
    median_interval_seconds: float
    gap_count: int
    estimated_intervening_bars: int
    largest_gap_seconds: int
    zero_volume_candles: int
    flat_candles: int
    gaps: list[CandleGap]
    notes: list[str]


def audit_candle_quality(request: CandleQualityRequest) -> CandleQualityResult:
    expected = TIMEFRAME_SECONDS[request.timeframe]
    intervals = []
    gaps: list[CandleGap] = []
    zero_volume = 0
    flat = 0
    for candle in request.candles:
        if candle.volume == 0:
            zero_volume += 1
        if candle.open == candle.high == candle.low == candle.close:
            flat += 1

    for left, right in zip(request.candles, request.candles[1:]):
        a = datetime.fromisoformat(left.timestamp.replace("Z", "+00:00")).astimezone(timezone.utc)
        b = datetime.fromisoformat(right.timestamp.replace("Z", "+00:00")).astimezone(timezone.utc)
        elapsed = int((b - a).total_seconds())
        intervals.append(elapsed)
        ratio = elapsed / expected
        if ratio > request.gap_tolerance:
            estimated = max(0, round(ratio) - 1)
            gaps.append(CandleGap(
                after_timestamp=left.timestamp,
                before_timestamp=right.timestamp,
                elapsed_seconds=elapsed,
                expected_intervals=round(ratio, 3),
                estimated_intervening_bars=estimated,
            ))

    notes = [
        "A time gap is a timestamp-spacing observation; weekends, exchange holidays, session breaks and illiquid periods can be legitimate.",
        "Estimated intervening bars are arithmetic estimates only and are not proof that source candles are missing.",
        "Zero-volume candles are reported without assuming that zero volume is invalid for the selected venue or data source.",
        "This audit checks series shape and basic candle properties; it cannot verify source authenticity, licensing, corporate actions or exchange completeness.",
    ]
    return CandleQualityResult(
        candle_count=len(request.candles),
        timeframe=request.timeframe,
        expected_interval_seconds=expected,
        first_timestamp=request.candles[0].timestamp,
        last_timestamp=request.candles[-1].timestamp,
        median_interval_seconds=float(median(intervals)),
        gap_count=len(gaps),
        estimated_intervening_bars=sum(g.estimated_intervening_bars for g in gaps),
        largest_gap_seconds=max(intervals, default=0),
        zero_volume_candles=zero_volume,
        flat_candles=flat,
        gaps=gaps[:100],
        notes=notes,
    )
