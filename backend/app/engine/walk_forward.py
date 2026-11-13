"""Rolling walk-forward and out-of-sample evaluation helpers."""
from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.engine.backtest import BacktestMetrics, BacktestRequest, run_backtest


class WalkForwardRequest(BacktestRequest):
    training_window_bars: int = Field(default=500, ge=20, le=4000)
    test_window_bars: int = Field(default=100, ge=5, le=2000)
    step_bars: int = Field(default=100, ge=1, le=2000)

    @model_validator(mode="after")
    def validate_non_overlapping_tests(self) -> "WalkForwardRequest":
        if self.step_bars < self.test_window_bars:
            raise ValueError(
                "step_bars must be at least test_window_bars so out-of-sample folds do not overlap"
            )
        return self


class WalkForwardFold(BaseModel):
    fold: int
    training_start: str
    training_end: str
    test_start: str
    test_end: str
    training_metrics: BacktestMetrics
    out_of_sample_metrics: BacktestMetrics
    benchmark_return_pct: float
    excess_return_pct: float


class WalkForwardResult(BaseModel):
    method: str = "rolling-window walk-forward; each test fold is evaluated strictly after its training window"
    fold_count: int
    aggregate_out_of_sample_return_pct: float
    average_fold_return_pct: float
    average_benchmark_return_pct: float
    average_excess_return_pct: float
    total_out_of_sample_trades: int
    folds: list[WalkForwardFold]
    notes: list[str]


def run_walk_forward(request: WalkForwardRequest) -> WalkForwardResult:
    candles = request.candles
    minimum = max(2 * request.profile.pivot + 1, request.profile.atr_period + 2)
    if request.training_window_bars < minimum:
        raise ValueError(f"training_window_bars must be at least {minimum} for this setup profile")
    first_test = request.training_window_bars
    if first_test + 5 > len(candles):
        raise ValueError("dataset must contain at least five candles after the training window")

    folds: list[WalkForwardFold] = []
    compounded_return = 1.0
    fold_returns: list[float] = []
    benchmark_returns: list[float] = []
    excess_returns: list[float] = []
    total_trades = 0
    test_start = first_test
    fold_number = 1

    while test_start < len(candles) - 1:
        test_end = min(test_start + request.test_window_bars, len(candles))
        if test_end - test_start < 5:
            break
        train_start = max(0, test_start - request.training_window_bars)
        training_data = candles[train_start:test_start]
        if len(training_data) < minimum:
            raise ValueError("training window is too short for the configured setup profile")

        common = {
            "profile": request.profile,
            "starting_equity": request.starting_equity,
            "risk_per_trade_pct": request.risk_per_trade_pct,
            "target_r_multiple": request.target_r_multiple,
            "commission_bps": request.commission_bps,
            "spread_bps": request.spread_bps,
            "slippage_bps": request.slippage_bps,
            "market_type": request.market_type,
            "contract_multiplier": request.contract_multiplier,
            "funding_bps_per_8h": request.funding_bps_per_8h,
            "swap_bps_per_day": request.swap_bps_per_day,
            "borrow_bps_per_day": request.borrow_bps_per_day,
            "tax_bps_on_positive_pnl": request.tax_bps_on_positive_pnl,
        }
        training = run_backtest(BacktestRequest(candles=training_data, **common))
        # Keep the complete prefix so structure/sweep confirmation can use prior
        # candles, but block entries until the out-of-sample boundary.
        test_request = BacktestRequest(
            candles=candles[:test_end],
            evaluation_start_index=test_start,
            **common,
        )
        tested = run_backtest(test_request)
        benchmark_start = candles[test_start].open
        benchmark_end = candles[test_end - 1].close
        benchmark = ((benchmark_end / benchmark_start) - 1.0) * 100 if benchmark_start else 0.0
        strategy_return = tested.metrics.total_return_pct
        excess = strategy_return - benchmark
        folds.append(WalkForwardFold(
            fold=fold_number,
            training_start=training_data[0].timestamp,
            training_end=training_data[-1].timestamp,
            test_start=candles[test_start].timestamp,
            test_end=candles[test_end - 1].timestamp,
            training_metrics=training.metrics,
            out_of_sample_metrics=tested.metrics,
            benchmark_return_pct=benchmark,
            excess_return_pct=excess,
        ))
        compounded_return *= 1.0 + strategy_return / 100.0
        fold_returns.append(strategy_return)
        benchmark_returns.append(benchmark)
        excess_returns.append(excess)
        total_trades += tested.metrics.trade_count
        fold_number += 1
        test_start += request.step_bars

    if not folds:
        raise ValueError("no complete out-of-sample folds could be constructed")
    return WalkForwardResult(
        fold_count=len(folds),
        aggregate_out_of_sample_return_pct=(compounded_return - 1.0) * 100.0,
        average_fold_return_pct=sum(fold_returns) / len(fold_returns),
        average_benchmark_return_pct=sum(benchmark_returns) / len(benchmark_returns),
        average_excess_return_pct=sum(excess_returns) / len(excess_returns),
        total_out_of_sample_trades=total_trades,
        folds=folds,
        notes=[
            "Training and test windows are chronological; no candle after a fold's test end is supplied to that fold.",
            "Test signals are blocked until the out-of-sample boundary, while earlier candles remain available for swing and liquidity context.",
            "Each fold starts with fresh configured equity and no carried position; test windows are required to be non-overlapping so aggregate out-of-sample compounding does not double-count bars.",
            "Benchmark is a simple buy-and-hold return from the first test candle open to the final test candle close; it excludes dividends, funding, borrow, taxes and costs.",
            "The strategy profile is held fixed. This evaluator does not optimize parameters on the training window or guarantee that a selected profile generalizes.",
            "Results depend on caller-supplied OHLCV quality, source rights, instrument contract metadata and realistic market-specific costs.",
        ],
    )
