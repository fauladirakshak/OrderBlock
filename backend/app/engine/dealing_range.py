"""Premium/discount context from the latest eligible confirmed swing range."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.engine.structure import Candle, detect_structure


class DealingRangeRequest(BaseModel):
    candles: list[Candle] = Field(min_length=5, max_length=5000)
    pivot: int = Field(default=2, ge=1, le=10)
    equilibrium_band_pct: float = Field(default=5.0, ge=0, le=25)

    @model_validator(mode="after")
    def validate_timestamps(self) -> "DealingRangeRequest":
        from datetime import datetime, timezone
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
        return self


class DealingRange(BaseModel):
    high: float
    low: float
    equilibrium: float
    current_price: float
    position_pct: float
    location: Literal["premium", "discount", "equilibrium", "above_range", "below_range"]
    high_swing_timestamp: str
    low_swing_timestamp: str
    high_confirmation_index: int
    low_confirmation_index: int
    equilibrium_band_low: float
    equilibrium_band_high: float


class DealingRangeResult(BaseModel):
    available: bool
    range: DealingRange | None
    notes: list[str]


def analyze_dealing_range(request: DealingRangeRequest) -> DealingRangeResult:
    structure = detect_structure(request.candles, pivot=request.pivot)
    last_eligible_index = len(request.candles) - 2
    highs = [point for point in structure.swing_highs if point["confirmation_index"] <= last_eligible_index]
    lows = [point for point in structure.swing_lows if point["confirmation_index"] <= last_eligible_index]
    notes = [
        "The range uses the latest confirmed swing high and swing low that were eligible before the final candle.",
        "Premium and discount are geometric halves of this selected range; they are not directional forecasts or trade signals.",
        "The equilibrium band is configurable and centered on the 50% midpoint.",
        "A range is unavailable until both a confirmed swing high and low exist in the supplied history.",
    ]
    if not highs or not lows:
        return DealingRangeResult(available=False, range=None, notes=notes)
    high_point = max(highs, key=lambda point: point["index"])
    low_point = max(lows, key=lambda point: point["index"])
    top, bottom = high_point["price"], low_point["price"]
    if top <= bottom:
        return DealingRangeResult(available=False, range=None,
                                  notes=notes + ["The latest confirmed swing points do not form a positive high/low range."])
    equilibrium = (top + bottom) / 2.0
    band = (top - bottom) * request.equilibrium_band_pct / 100.0
    current = request.candles[-1].close
    position = (current - bottom) / (top - bottom) * 100.0
    if current > top:
        location = "above_range"
    elif current < bottom:
        location = "below_range"
    elif abs(current - equilibrium) <= band:
        location = "equilibrium"
    elif current > equilibrium:
        location = "premium"
    else:
        location = "discount"
    return DealingRangeResult(
        available=True,
        range=DealingRange(
            high=top, low=bottom, equilibrium=equilibrium, current_price=current,
            position_pct=position, location=location,
            high_swing_timestamp=high_point["timestamp"],
            low_swing_timestamp=low_point["timestamp"],
            high_confirmation_index=high_point["confirmation_index"],
            low_confirmation_index=low_point["confirmation_index"],
            equilibrium_band_low=equilibrium - band,
            equilibrium_band_high=equilibrium + band,
        ),
        notes=notes,
    )
