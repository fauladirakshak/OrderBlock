"""Deterministic, candle-based market structure primitives.

Events are rule-based observations of supplied OHLCV candles, not predictions.
"""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, model_validator


class Candle(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_ohlc(self) -> "Candle":
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high must be the greatest OHLC value")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low must be the smallest OHLC value")
        return self


class StructureEvent(BaseModel):
    kind: Literal["BOS", "CHoCH"]
    direction: Literal["bullish", "bearish"]
    level: float
    candle_index: int
    timestamp: str
    explanation: str


class StructureResult(BaseModel):
    swing_highs: list[dict]
    swing_lows: list[dict]
    events: list[StructureEvent]


def detect_structure(candles: list[Candle], pivot: int = 2) -> StructureResult:
    """Find confirmed pivots and close-based breaks of the latest opposing swing.

    A pivot at i is confirmed only after pivot candles have printed to its right.
    The first break is labelled BOS; a break against the current direction is CHoCH.
    """
    if pivot < 1:
        raise ValueError("pivot must be at least 1")
    highs: list[dict] = []
    lows: list[dict] = []
    for i in range(pivot, len(candles) - pivot):
        window = candles[i - pivot:i + pivot + 1]
        current = candles[i]
        others = [c for j, c in enumerate(window) if j != pivot]
        if all(current.high > c.high for c in others):
            highs.append({"index": i, "timestamp": current.timestamp, "price": current.high})
        if all(current.low < c.low for c in others):
            lows.append({"index": i, "timestamp": current.timestamp, "price": current.low})

    events: list[StructureEvent] = []
    direction: Literal["bullish", "bearish"] | None = None
    broken_highs: set[int] = set()
    broken_lows: set[int] = set()

    for i, candle in enumerate(candles):
        available_highs = [p for p in highs if p["index"] < i and p["index"] not in broken_highs]
        available_lows = [p for p in lows if p["index"] < i and p["index"] not in broken_lows]
        if available_highs:
            candidate = available_highs[-1]
            if candle.close > candidate["price"]:
                kind = "CHoCH" if direction == "bearish" else "BOS"
                events.append(StructureEvent(
                    kind=kind, direction="bullish", level=candidate["price"],
                    candle_index=i, timestamp=candle.timestamp,
                    explanation=f"Close crossed above confirmed swing high {candidate['price']:.6g}.",
                ))
                direction = "bullish"
                broken_highs.add(candidate["index"])
        if available_lows:
            candidate = available_lows[-1]
            if candle.close < candidate["price"]:
                kind = "CHoCH" if direction == "bullish" else "BOS"
                events.append(StructureEvent(
                    kind=kind, direction="bearish", level=candidate["price"],
                    candle_index=i, timestamp=candle.timestamp,
                    explanation=f"Close crossed below confirmed swing low {candidate['price']:.6g}.",
                ))
                direction = "bearish"
                broken_lows.add(candidate["index"])
    return StructureResult(swing_highs=highs, swing_lows=lows, events=events)
