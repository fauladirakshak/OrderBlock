"""Deterministic OHLC backtester for the configurable ICT-inspired setup engine.

Signals are evaluated only on candles closed at the signal index. Entries occur at
the next candle open. OHLC bars cannot reveal intrabar ordering, so stop wins when
stop and target are both touched in the same bar. This is a research simulator,
not an execution engine or investment advice.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.engine.setups import SetupProfile, analyze_setups
from app.engine.structure import Candle


class BacktestRequest(BaseModel):
    candles: list[Candle] = Field(min_length=5, max_length=20000)
    profile: SetupProfile = Field(default_factory=SetupProfile)
    starting_equity: float = Field(default=10000.0, gt=0)
    risk_per_trade_pct: float = Field(default=1.0, gt=0, le=10)
    target_r_multiple: float = Field(default=2.0, gt=0, le=20)
    commission_bps: float = Field(default=0.0, ge=0, le=500)
    spread_bps: float = Field(default=0.0, ge=0, le=500)
    slippage_bps: float = Field(default=0.0, ge=0, le=500)

    @model_validator(mode="after")
    def validate_order(self) -> "BacktestRequest":
        stamps = [c.timestamp for c in self.candles]
        if any(b <= a for a, b in zip(stamps, stamps[1:])):
            raise ValueError("candle timestamps must be strictly increasing")
        return self


class BacktestTrade(BaseModel):
    direction: Literal["long", "short"]
    signal_index: int
    entry_index: int
    exit_index: int
    signal_timestamp: str
    entry_timestamp: str
    exit_timestamp: str
    entry_price: float
    exit_price: float
    stop_price: float
    target_price: float
    quantity: float
    gross_pnl: float
    fees: float
    net_pnl: float
    r_multiple: float
    exit_reason: Literal["stop", "target", "end_of_data"]


class EquityPoint(BaseModel):
    timestamp: str
    equity: float


class BacktestMetrics(BaseModel):
    starting_equity: float
    ending_equity: float
    net_profit: float
    total_return_pct: float
    trade_count: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    profit_factor: float | None
    expectancy: float
    average_r: float
    max_drawdown_pct: float


class BacktestResult(BaseModel):
    strategy: str = "ICT-inspired-confluence-v0.1"
    is_synthetic: bool = False
    execution_model: str
    metrics: BacktestMetrics
    trades: list[BacktestTrade]
    equity_curve: list[EquityPoint]
    notes: list[str]


def run_backtest(request: BacktestRequest) -> BacktestResult:
    candles = request.candles
    minimum = max(2 * request.profile.pivot + 1, request.profile.atr_period + 2)
    if len(candles) < minimum:
        raise ValueError(f"not enough candles for this profile; at least {minimum} are required")

    equity = request.starting_equity
    risk_fraction = request.risk_per_trade_pct / 100.0
    half_spread = request.spread_bps / 20000.0
    slippage = request.slippage_bps / 10000.0
    commission = request.commission_bps / 10000.0
    trades: list[BacktestTrade] = []
    curve: list[EquityPoint] = []
    position: dict | None = None
    pending: dict | None = None

    for index, candle in enumerate(candles):
        # A signal from the previous closed bar can enter only at this bar's open.
        if position is None and pending is not None:
            direction = pending["direction"]
            raw_entry = candle.open
            stop = pending["stop"]
            risk_per_unit = abs(raw_entry - stop)
            if risk_per_unit > 0:
                risk_cash = equity * risk_fraction
                quantity = risk_cash / risk_per_unit
                target = raw_entry + risk_per_unit * request.target_r_multiple * (1 if direction == "long" else -1)
                entry_exec = raw_entry * (1 + half_spread + slippage) if direction == "long" else raw_entry * (1 - half_spread - slippage)
                position = {
                    "direction": direction, "signal_index": pending["signal_index"],
                    "signal_timestamp": pending["signal_timestamp"], "entry_index": index,
                    "entry_timestamp": candle.timestamp, "entry_raw": raw_entry,
                    "entry_exec": entry_exec, "stop": stop, "target": target,
                    "quantity": quantity,
                }
            pending = None

        if position is not None:
            long_side = position["direction"] == "long"
            stop_hit = candle.low <= position["stop"] if long_side else candle.high >= position["stop"]
            target_hit = candle.high >= position["target"] if long_side else candle.low <= position["target"]
            exit_reason = None
            raw_exit = None
            if stop_hit:
                exit_reason, raw_exit = "stop", position["stop"]
            elif target_hit:
                exit_reason, raw_exit = "target", position["target"]
            elif index == len(candles) - 1:
                exit_reason, raw_exit = "end_of_data", candle.close

            if exit_reason is not None:
                direction_sign = 1 if long_side else -1
                exit_exec = raw_exit * (1 - half_spread - slippage) if long_side else raw_exit * (1 + half_spread + slippage)
                gross = direction_sign * position["quantity"] * (exit_exec - position["entry_exec"])
                fees = commission * position["quantity"] * (position["entry_exec"] + exit_exec)
                net = gross - fees
                initial_risk = abs(position["entry_raw"] - position["stop"]) * position["quantity"]
                r_value = net / initial_risk if initial_risk else 0.0
                equity += net
                trades.append(BacktestTrade(
                    direction=position["direction"], signal_index=position["signal_index"],
                    entry_index=position["entry_index"], exit_index=index,
                    signal_timestamp=position["signal_timestamp"],
                    entry_timestamp=position["entry_timestamp"], exit_timestamp=candle.timestamp,
                    entry_price=position["entry_exec"], exit_price=exit_exec,
                    stop_price=position["stop"], target_price=position["target"],
                    quantity=position["quantity"], gross_pnl=gross, fees=fees,
                    net_pnl=net, r_multiple=r_value, exit_reason=exit_reason,
                ))
                position = None

        # Evaluate only the prefix ending at this closed candle. No future bar is
        # passed to the setup engine; a candidate may enter no earlier than i+1.
        if position is None and pending is None and index < len(candles) - 1:
            analysis = analyze_setups(candles[: index + 1], profile=request.profile)
            candidates = [s for s in analysis.setups if s.structure_index == index]
            if candidates:
                setup = candidates[-1]
                long_side = setup.direction == "bullish"
                if setup.order_block_top is not None and setup.order_block_bottom is not None:
                    stop = setup.order_block_bottom if long_side else setup.order_block_top
                else:
                    stop = candle.low if long_side else candle.high
                # Ignore malformed/zero-distance stop geometry.
                if (candle.close - stop) > 0 if long_side else (stop - candle.close) > 0:
                    pending = {
                        "direction": "long" if long_side else "short",
                        "signal_index": index, "signal_timestamp": candle.timestamp,
                        "stop": stop,
                    }

        curve.append(EquityPoint(timestamp=candle.timestamp, equity=equity))

    wins = [t for t in trades if t.net_pnl > 0]
    losses = [t for t in trades if t.net_pnl < 0]
    gross_wins = sum(t.net_pnl for t in wins)
    gross_losses = abs(sum(t.net_pnl for t in losses))
    peak = request.starting_equity
    max_dd = 0.0
    for point in curve:
        peak = max(peak, point.equity)
        if peak > 0:
            max_dd = max(max_dd, (peak - point.equity) / peak * 100)
    net_profit = equity - request.starting_equity
    count = len(trades)
    metrics = BacktestMetrics(
        starting_equity=request.starting_equity, ending_equity=equity,
        net_profit=net_profit, total_return_pct=net_profit / request.starting_equity * 100,
        trade_count=count, winning_trades=len(wins), losing_trades=len(losses),
        win_rate_pct=len(wins) / count * 100 if count else 0.0,
        profit_factor=(gross_wins / gross_losses if gross_losses else (None if gross_wins == 0 else float("inf"))),
        expectancy=sum(t.net_pnl for t in trades) / count if count else 0.0,
        average_r=sum(t.r_multiple for t in trades) / count if count else 0.0,
        max_drawdown_pct=max_dd,
    )
    return BacktestResult(
        execution_model="Signal on closed bar; next-bar-open entry; OHLC stop-first tie-break; configurable spread, slippage and commission; one position at a time.",
        metrics=metrics, trades=trades, equity_curve=curve,
        notes=[
            "Signals are recalculated on historical prefixes only; future candles are never supplied to signal generation.",
            "Entries occur at the next candle open, not at the signal candle close.",
            "If stop and target are both touched in one OHLC candle, the stop is assumed first because intrabar order is unknowable.",
            "Position size risks the configured fraction of current equity at the raw entry-to-stop distance; costs can increase realized loss beyond that amount.",
            "A remaining position is closed at the final candle close. No funding, borrow, swaps, taxes or exchange-specific contract multipliers are modeled.",
            "This independently implemented ICT-inspired research strategy is not canonical ICT code, investment advice or a live trading system.",
        ],
    )
