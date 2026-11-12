"""Combined chart overlay payload for the trading workspace."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.engine.structure import Candle, StructureEvent, detect_structure
from app.engine.zones import OrderBlock, FairValueGap, analyze_zones


class LiquiditySweep(BaseModel):
    direction: Literal["bullish", "bearish"]
    candle_index: int
    timestamp: str
    level: float
    explanation: str


class WorkspaceAnalysis(BaseModel):
    structure_events: list[StructureEvent]
    order_blocks: list[OrderBlock]
    fair_value_gaps: list[FairValueGap]
    liquidity_sweeps: list[LiquiditySweep]
    notes: list[str]


def analyze_workspace(candles: list[Candle], pivot: int = 2) -> WorkspaceAnalysis:
    """Build explainable, closed-candle overlays from the existing engine rules."""
    structure = detect_structure(candles, pivot=pivot)
    zones = analyze_zones(candles, pivot=pivot)
    sweeps: list[LiquiditySweep] = []
    seen: set[tuple[int, str, float]] = set()

    # A swing only becomes eligible after its right-side confirmation candle closes.
    for direction, levels in (("bullish", structure.swing_lows), ("bearish", structure.swing_highs)):
        for level in levels:
            first = level["confirmation_index"] + 1
            for index in range(first, len(candles)):
                candle = candles[index]
                swept = (
                    candle.low < level["price"] and candle.close > level["price"]
                    if direction == "bullish"
                    else candle.high > level["price"] and candle.close < level["price"]
                )
                identity = (index, direction, level["price"])
                if swept and identity not in seen:
                    seen.add(identity)
                    sweeps.append(LiquiditySweep(
                        direction=direction,
                        candle_index=index,
                        timestamp=candle.timestamp,
                        level=level["price"],
                        explanation=(
                            f"{direction.title()} liquidity sweep: wick crossed a confirmed "
                            f"swing level ({level['price']:.6g}) and candle closed back through it."
                        ),
                    ))

    return WorkspaceAnalysis(
        structure_events=structure.events,
        order_blocks=zones.order_blocks,
        fair_value_gaps=zones.fair_value_gaps,
        liquidity_sweeps=sweeps,
        notes=[
            "All overlays are rule-based observations of the supplied closed OHLC candles.",
            "Order blocks are the last opposing candle before a detected structure break; they are not proof of institutional orders.",
            "FVGs use a three-candle gap rule. Mitigation and fill are reported separately.",
            "Liquidity sweeps require a wick through a confirmed swing followed by a close back through that level.",
            "Historical chart annotations are descriptive and are not entry signals or investment advice.",
        ],
    )
