"""Previous-period and equal-swing liquidity reference levels.

Levels are descriptive historical context. Swing clusters become eligible only
after their pivots are confirmed; sweeps are evaluated strictly after that point.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, model_validator

from app.engine.structure import Candle, detect_structure


class LiquidityReferenceRequest(BaseModel):
    candles: list[Candle] = Field(min_length=5, max_length=5000)
    timezone: str = "Etc/UTC"
    pivot: int = Field(default=2, ge=1, le=10)
    tick_size: float = Field(default=0.00001, gt=0)
    tolerance_ticks: float = Field(default=2.0, ge=0.5, le=100)

    @model_validator(mode="after")
    def validate_timestamps(self) -> "LiquidityReferenceRequest":
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
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"Unknown IANA timezone: {self.timezone}") from exc
        return self


class LiquidityReferenceLevel(BaseModel):
    kind: Literal["previous_day_high", "previous_day_low", "previous_week_high",
                  "previous_week_low", "equal_highs", "equal_lows"]
    label: str
    price: float
    source_period: str
    touch_count: int = 1
    first_touch_timestamp: str
    last_touch_timestamp: str
    confirmed_index: int
    swept: bool = False
    sweep_timestamp: str | None = None
    sweep_index: int | None = None


class LiquidityReferenceResult(BaseModel):
    timezone: str
    levels: list[LiquidityReferenceLevel]
    notes: list[str]


def _utc(candle: Candle) -> datetime:
    return datetime.fromisoformat(candle.timestamp.replace("Z", "+00:00")).astimezone(timezone.utc)


def _period_levels(candles: list[Candle], zone: ZoneInfo, weekly: bool):
    grouped: dict[tuple, list[tuple[int, Candle]]] = {}
    for index, candle in enumerate(candles):
        local = _utc(candle).astimezone(zone)
        key = (local.isocalendar().year, local.isocalendar().week) if weekly else (local.date().isoformat(),)
        grouped.setdefault(key, []).append((index, candle))
    keys = sorted(grouped)
    if len(keys) < 2:
        return []
    prior_key = keys[-2]
    rows = grouped[prior_key]
    label = "previous_week" if weekly else "previous_day"
    period_name = f"{prior_key[0]}-W{prior_key[1]:02d}" if weekly else prior_key[0]
    high_index, high_candle = max(rows, key=lambda item: item[1].high)
    low_index, low_candle = min(rows, key=lambda item: item[1].low)
    return [
        LiquidityReferenceLevel(
            kind=f"{label}_high", label="PWH" if weekly else "PDH",
            price=high_candle.high, source_period=period_name,
            first_touch_timestamp=high_candle.timestamp, last_touch_timestamp=high_candle.timestamp,
            confirmed_index=high_index,
        ),
        LiquidityReferenceLevel(
            kind=f"{label}_low", label="PWL" if weekly else "PDL",
            price=low_candle.low, source_period=period_name,
            first_touch_timestamp=low_candle.timestamp, last_touch_timestamp=low_candle.timestamp,
            confirmed_index=low_index,
        ),
    ]


def _equal_swing_levels(candles: list[Candle], pivot: int, tolerance: float):
    structure = detect_structure(candles, pivot=pivot)
    results: list[LiquidityReferenceLevel] = []
    for side, points, kind, label, is_high in (
        ("high", structure.swing_highs, "equal_highs", "EQH", True),
        ("low", structure.swing_lows, "equal_lows", "EQL", False),
    ):
        clusters: list[list[dict]] = []
        for point in sorted(points, key=lambda item: item["price"]):
            if not clusters or abs(point["price"] - sum(p["price"] for p in clusters[-1]) / len(clusters[-1])) > tolerance:
                clusters.append([point])
            else:
                clusters[-1].append(point)
        for cluster in clusters:
            if len(cluster) < 2:
                continue
            level = sum(point["price"] for point in cluster) / len(cluster)
            confirmed_index = max(point["confirmation_index"] for point in cluster)
            sweep = None
            for index in range(confirmed_index + 1, len(candles)):
                candle = candles[index]
                crossed = candle.high > level and candle.close < level if is_high else candle.low < level and candle.close > level
                if crossed:
                    sweep = (index, candle.timestamp)
                    break
            ordered = sorted(cluster, key=lambda item: item["index"])
            results.append(LiquidityReferenceLevel(
                kind=kind, label=label, price=level,
                source_period=f"bars {ordered[0]['index']}–{ordered[-1]['index']}",
                touch_count=len(cluster),
                first_touch_timestamp=ordered[0]["timestamp"],
                last_touch_timestamp=ordered[-1]["timestamp"],
                confirmed_index=confirmed_index,
                swept=sweep is not None,
                sweep_timestamp=sweep[1] if sweep else None,
                sweep_index=sweep[0] if sweep else None,
            ))
    return results


def analyze_liquidity_references(request: LiquidityReferenceRequest) -> LiquidityReferenceResult:
    zone = ZoneInfo(request.timezone)
    levels = _period_levels(request.candles, zone, weekly=False)
    levels.extend(_period_levels(request.candles, zone, weekly=True))
    levels.extend(_equal_swing_levels(request.candles, request.pivot,
                                     request.tick_size * request.tolerance_ticks))
    return LiquidityReferenceResult(
        timezone=request.timezone,
        levels=levels,
        notes=[
            "PDH/PDL and PWH/PWL refer to the previous available candle period in the supplied dataset; missing dates are not synthesized.",
            "Equal highs/lows cluster confirmed swing pivots within the configured tick tolerance.",
            "A sweep is a wick beyond the level followed by a close back inside, and is only considered after all clustered pivots are confirmed.",
            "Reference levels are descriptive context, not guaranteed liquidity pools or trade signals.",
            "Use a complete, correctly adjusted dataset and exchange calendar; corporate actions, holidays and partial sessions can distort period levels.",
        ],
    )
