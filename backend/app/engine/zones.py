"""Explainable order-block and fair-value-gap candidate detection.

These are candle-pattern interpretations, not evidence of institutional orders.
"""
from typing import Literal

from pydantic import BaseModel

from app.engine.structure import Candle, detect_structure


class OrderBlock(BaseModel):
    direction: Literal["bullish", "bearish"]
    candle_index: int
    timestamp: str
    top: float
    bottom: float
    break_index: int
    break_kind: Literal["BOS", "CHoCH"]
    mitigated: bool
    invalidated: bool
    rule: str


class FairValueGap(BaseModel):
    direction: Literal["bullish", "bearish"]
    middle_candle_index: int
    timestamp: str
    top: float
    bottom: float
    mitigated: bool
    filled: bool
    rule: str


class ZoneAnalysis(BaseModel):
    order_blocks: list[OrderBlock]
    fair_value_gaps: list[FairValueGap]


def detect_order_blocks(candles: list[Candle], pivot: int = 2) -> list[OrderBlock]:
    """Find the last opposing candle before each confirmed close-based structure break.

    The complete high-low range is used as the zone. Mitigation means a later candle
    overlaps the zone; invalidation requires a later close beyond the far boundary.
    """
    structure = detect_structure(candles, pivot=pivot)
    zones: list[OrderBlock] = []
    used_candles: set[tuple[int, str]] = set()

    for event in structure.events:
        opposing = [
            index for index in range(event.candle_index - 1, -1, -1)
            if (
                (candles[index].close < candles[index].open)
                if event.direction == "bullish"
                else (candles[index].close > candles[index].open)
            )
        ]
        if not opposing:
            continue
        index = opposing[0]
        identity = (index, event.direction)
        if identity in used_candles:
            continue
        used_candles.add(identity)
        origin = candles[index]
        later = candles[event.candle_index + 1:]
        if event.direction == "bullish":
            mitigated = any(c.low <= origin.high and c.high >= origin.low for c in later)
            invalidated = any(c.close < origin.low for c in later)
        else:
            mitigated = any(c.high >= origin.low and c.low <= origin.high for c in later)
            invalidated = any(c.close > origin.high for c in later)
        zones.append(OrderBlock(
            direction=event.direction,
            candle_index=index,
            timestamp=origin.timestamp,
            top=origin.high,
            bottom=origin.low,
            break_index=event.candle_index,
            break_kind=event.kind,
            mitigated=mitigated,
            invalidated=invalidated,
            rule="Last opposing candle before a confirmed close-based BOS/CHoCH; full wick range.",
        ))
    return zones


def detect_fair_value_gaps(candles: list[Candle]) -> list[FairValueGap]:
    """Detect three-candle gaps; report later overlap and complete fill separately."""
    gaps: list[FairValueGap] = []
    for middle in range(1, len(candles) - 1):
        first, third = candles[middle - 1], candles[middle + 1]
        if first.high < third.low:
            top, bottom = third.low, first.high
            later = candles[middle + 2:]
            mitigated = any(c.low <= top and c.high >= bottom for c in later)
            filled = any(c.low <= bottom for c in later)
            gaps.append(FairValueGap(
                direction="bullish", middle_candle_index=middle,
                timestamp=candles[middle].timestamp, top=top, bottom=bottom,
                mitigated=mitigated, filled=filled,
                rule="Three-candle bullish gap: first candle high is below third candle low.",
            ))
        elif first.low > third.high:
            top, bottom = first.low, third.high
            later = candles[middle + 2:]
            mitigated = any(c.high >= bottom and c.low <= top for c in later)
            filled = any(c.high >= top for c in later)
            gaps.append(FairValueGap(
                direction="bearish", middle_candle_index=middle,
                timestamp=candles[middle].timestamp, top=top, bottom=bottom,
                mitigated=mitigated, filled=filled,
                rule="Three-candle bearish gap: first candle low is above third candle high.",
            ))
    return gaps


def analyze_zones(candles: list[Candle], pivot: int = 2) -> ZoneAnalysis:
    return ZoneAnalysis(
        order_blocks=detect_order_blocks(candles, pivot=pivot),
        fair_value_gaps=detect_fair_value_gaps(candles),
    )
