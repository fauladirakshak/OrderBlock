"""Confluence-based ICT-inspired setup candidates.

This is an independently implemented, configurable research profile. It is not a
claim to reproduce any proprietary ICT indicator or canonical interpretation.
A setup is only emitted after all required events are knowable from closed candles.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.engine.structure import Candle, detect_structure
from app.engine.zones import detect_fair_value_gaps


class SetupProfile(BaseModel):
    pivot: int = Field(default=2, ge=1, le=10)
    sweep_lookback: int = Field(default=20, ge=3, le=100)
    atr_period: int = Field(default=14, ge=3, le=100)
    min_displacement_atr: float = Field(default=1.2, gt=0, le=10)
    min_body_fraction: float = Field(default=0.6, gt=0, le=1)
    require_fvg: bool = True


class SetupCandidate(BaseModel):
    direction: Literal["bullish", "bearish"]
    status: Literal["candidate"] = "candidate"
    sweep_index: int
    sweep_timestamp: str
    liquidity_level: float
    structure_index: int
    structure_timestamp: str
    structure_kind: Literal["BOS", "CHoCH"]
    displacement_range: float
    prior_average_range: float
    body_fraction: float
    fvg_index: int | None
    order_block_index: int | None
    order_block_top: float | None
    order_block_bottom: float | None
    explanation: str
    profile: str = "ICT-inspired-confluence-v0.1"


class SetupAnalysis(BaseModel):
    profile: SetupProfile
    setups: list[SetupCandidate]
    notes: list[str]


def _average_prior_range(candles: list[Candle], index: int, period: int) -> float:
    start = max(0, index - period)
    prior = candles[start:index]
    if not prior:
        return 0.0
    return sum(c.high - c.low for c in prior) / len(prior)


def _last_opposing_candle(
    candles: list[Candle], end_index: int, direction: str
) -> tuple[int, float, float] | None:
    for index in range(end_index - 1, -1, -1):
        candle = candles[index]
        opposing = (
            candle.close < candle.open
            if direction == "bullish"
            else candle.close > candle.open
        )
        if opposing:
            return index, candle.high, candle.low
    return None


def analyze_setups(candles: list[Candle], profile: SetupProfile | None = None) -> SetupAnalysis:
    """Qualify a sweep -> displacement/structure-shift -> optional FVG sequence.

    Sweeps must reclaim a previously confirmed swing level. Structure events and
    displacement are evaluated on closed candles. ATR-like range baseline uses
    only candles strictly before the displacement candle.
    """
    config = profile or SetupProfile()
    structure = detect_structure(candles, pivot=config.pivot)
    gaps = detect_fair_value_gaps(candles)
    gap_by_middle = {gap.middle_candle_index: gap for gap in gaps}
    setups: list[SetupCandidate] = []
    seen: set[tuple[int, int, str]] = set()

    for event in structure.events:
        direction = event.direction
        if direction == "bullish":
            levels = structure.swing_lows
            swept = lambda candle, level: candle.low < level and candle.close > level
        else:
            levels = structure.swing_highs
            swept = lambda candle, level: candle.high > level and candle.close < level

        lower = max(0, event.candle_index - config.sweep_lookback)
        prior_sweeps: list[tuple[int, float]] = []
        for level in levels:
            sweep_index = level["confirmation_index"] + 1
            if lower <= sweep_index < event.candle_index:
                candle = candles[sweep_index]
                if swept(candle, level["price"]):
                    prior_sweeps.append((sweep_index, level["price"]))
        if not prior_sweeps:
            continue

        sweep_index, liquidity_level = prior_sweeps[-1]
        displacement = candles[event.candle_index]
        candle_range = displacement.high - displacement.low
        prior_average = _average_prior_range(candles, event.candle_index, config.atr_period)
        if candle_range <= 0 or prior_average <= 0:
            continue
        body_fraction = abs(displacement.close - displacement.open) / candle_range
        if candle_range < prior_average * config.min_displacement_atr:
            continue
        if body_fraction < config.min_body_fraction:
            continue

        gap = gap_by_middle.get(event.candle_index - 1)
        if config.require_fvg and gap is None:
            continue
        opposing = _last_opposing_candle(candles, event.candle_index, direction)
        key = (sweep_index, event.candle_index, direction)
        if key in seen:
            continue
        seen.add(key)

        setups.append(SetupCandidate(
            direction=direction,
            sweep_index=sweep_index,
            sweep_timestamp=candles[sweep_index].timestamp,
            liquidity_level=liquidity_level,
            structure_index=event.candle_index,
            structure_timestamp=event.timestamp,
            structure_kind=event.kind,
            displacement_range=candle_range,
            prior_average_range=prior_average,
            body_fraction=body_fraction,
            fvg_index=gap.middle_candle_index if gap else None,
            order_block_index=opposing[0] if opposing else None,
            order_block_top=opposing[1] if opposing else None,
            order_block_bottom=opposing[2] if opposing else None,
            explanation=(
                f"{direction.title()} setup: confirmed swing liquidity was swept and reclaimed, "
                f"then a {event.kind} close occurred with displacement "
                f"({candle_range / prior_average:.2f}x prior average range, "
                f"{body_fraction:.0%} body fraction)"
                + (" and a three-candle FVG." if gap else ".")
            ),
        ))

    return SetupAnalysis(
        profile=config,
        setups=setups,
        notes=[
            "Research candidate only; not an entry signal or investment advice.",
            "A sweep is a wick through a previously confirmed swing followed by a close back inside.",
            "The structure event and displacement are evaluated on the same closed candle in v0.1.",
            "This profile is configurable and does not claim to reproduce private or canonical ICT code.",
            "Use venue-specific data, costs, session context and out-of-sample validation before strategy evaluation.",
        ],
    )
