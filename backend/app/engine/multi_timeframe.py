"""Higher-timeframe context for a selected chart timeframe.

This module compares independently analysed OHLC candle sets. It does not resample
lower-timeframe candles or infer missing market data.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.engine.structure import Candle, StructureEvent, detect_structure

TIMEFRAME_ORDER = {"5m": 1, "15m": 2, "1H": 3, "4H": 4, "1D": 5, "1W": 6}
Bias = Literal["bullish", "bearish", "neutral"]
Alignment = Literal["bullish", "bearish", "mixed", "neutral"]


class MultiTimeframeRequest(BaseModel):
    primary_timeframe: str
    candles_by_timeframe: dict[str, list[Candle]] = Field(min_length=2)
    pivot: int = Field(default=2, ge=1, le=20)

    @model_validator(mode="after")
    def validate_timeframes(self) -> "MultiTimeframeRequest":
        if self.primary_timeframe not in TIMEFRAME_ORDER:
            raise ValueError("Unsupported primary timeframe.")
        if self.primary_timeframe not in self.candles_by_timeframe:
            raise ValueError("Candle data must include the primary timeframe.")
        if len(self.candles_by_timeframe) < 2:
            raise ValueError("At least one higher timeframe is required.")
        primary_rank = TIMEFRAME_ORDER[self.primary_timeframe]
        for timeframe, candles in self.candles_by_timeframe.items():
            if timeframe not in TIMEFRAME_ORDER:
                raise ValueError(f"Unsupported timeframe: {timeframe}")
            if timeframe != self.primary_timeframe and TIMEFRAME_ORDER[timeframe] <= primary_rank:
                raise ValueError("All context timeframes must be higher than the primary timeframe.")
            if len(candles) < max(5, 2 * self.pivot + 1):
                raise ValueError(f"Not enough candles for timeframe {timeframe}.")
        return self


class TimeframeContext(BaseModel):
    timeframe: str
    candle_count: int
    bias: Bias
    latest_event: StructureEvent | None
    latest_swing_high: float | None
    latest_swing_low: float | None
    explanation: str


class MultiTimeframeAnalysis(BaseModel):
    primary_timeframe: str
    primary_bias: Bias
    higher_timeframe_context: list[TimeframeContext]
    alignment: Alignment
    summary: str
    notes: list[str]


def _context(timeframe: str, candles: list[Candle], pivot: int) -> TimeframeContext:
    result = detect_structure(candles, pivot=pivot)
    latest_event = result.events[-1] if result.events else None
    bias: Bias = latest_event.direction if latest_event else "neutral"
    high = result.swing_highs[-1]["price"] if result.swing_highs else None
    low = result.swing_lows[-1]["price"] if result.swing_lows else None
    explanation = (
        f"Latest confirmed structure event is {latest_event.kind} {latest_event.direction}."
        if latest_event
        else "No confirmed structure break in the supplied history; bias remains neutral."
    )
    return TimeframeContext(
        timeframe=timeframe,
        candle_count=len(candles),
        bias=bias,
        latest_event=latest_event,
        latest_swing_high=high,
        latest_swing_low=low,
        explanation=explanation,
    )


def analyze_multi_timeframe(request: MultiTimeframeRequest) -> MultiTimeframeAnalysis:
    contexts = [
        _context(tf, candles, request.pivot)
        for tf, candles in request.candles_by_timeframe.items()
        if tf != request.primary_timeframe
    ]
    contexts.sort(key=lambda item: TIMEFRAME_ORDER[item.timeframe], reverse=True)
    primary = _context(
        request.primary_timeframe,
        request.candles_by_timeframe[request.primary_timeframe],
        request.pivot,
    )
    directional = {context.bias for context in contexts if context.bias != "neutral"}
    if not directional:
        alignment: Alignment = "neutral"
        summary = "Higher-timeframe structure is neutral; wait for clearer confirmed context."
    elif len(directional) > 1:
        alignment = "mixed"
        summary = "Higher timeframes disagree; treat directional context as mixed."
    else:
        alignment = next(iter(directional))  # type: ignore[assignment]
        summary = f"Higher-timeframe structure is {alignment}; compare lower-timeframe setups against this context."
    return MultiTimeframeAnalysis(
        primary_timeframe=request.primary_timeframe,
        primary_bias=primary.bias,
        higher_timeframe_context=contexts,
        alignment=alignment,
        summary=summary,
        notes=[
            "Each timeframe is analysed independently using confirmed swing points and close-based BOS/CHoCH rules.",
            "Higher-timeframe candles must be supplied by the caller; this endpoint does not resample or invent candles.",
            "The latest structure event is a descriptive bias proxy, not a prediction or trade signal.",
            "Use closed candles with consistent timestamps and the same instrument/venue across timeframes.",
        ],
    )
