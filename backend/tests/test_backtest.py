from types import SimpleNamespace

import pytest

from fastapi.testclient import TestClient

from app.engine.backtest import BacktestRequest, run_backtest
from app.engine.setups import SetupCandidate, SetupProfile
from app.engine.structure import Candle
from app.main import app

client = TestClient(app)


def candles(rows):
    return [Candle(timestamp=f"2026-01-01T00:{i:02d}:00Z", open=o, high=h, low=l, close=c)
            for i, (o, h, l, c) in enumerate(rows)]


def candidate():
    return SetupCandidate(
        direction="bullish", sweep_index=0, sweep_timestamp="2026-01-01T00:00:00Z",
        liquidity_level=99, structure_index=1, structure_timestamp="2026-01-01T00:01:00Z",
        structure_kind="BOS", displacement_range=2, prior_average_range=1,
        body_fraction=0.8, fvg_index=None, order_block_index=0,
        order_block_top=100, order_block_bottom=95, explanation="test candidate",
    )


def patch_signal(monkeypatch):
    item = candidate()
    def fake_analyze(prefix, profile=None):
        return SimpleNamespace(setups=[item] if len(prefix) == 2 else [])
    monkeypatch.setattr("app.engine.backtest.analyze_setups", fake_analyze)


def base_request(data, **overrides):
    values = dict(candles=data, profile=SetupProfile(pivot=1, atr_period=3, require_fvg=False),
                  starting_equity=10000, risk_per_trade_pct=1, target_r_multiple=2)
    values.update(overrides)
    return BacktestRequest(**values)


def test_entry_is_next_bar_open_and_same_bar_stop_target_uses_stop(monkeypatch):
    patch_signal(monkeypatch)
    data = candles([(100, 101, 99, 100), (100, 102, 99, 101),
                    (100, 111, 94, 105), (100, 101, 99, 100),
                    (100, 101, 99, 100), (100, 101, 99, 100)])
    result = run_backtest(base_request(data))
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.signal_index == 1
    assert trade.entry_index == 2
    assert trade.entry_price == 100
    assert trade.exit_reason == "stop"
    assert trade.exit_price == 95
    assert trade.net_pnl < 0


def test_costs_reduce_net_profit(monkeypatch):
    patch_signal(monkeypatch)
    data = candles([(100, 101, 99, 100), (100, 102, 99, 101),
                    (100, 103, 99, 102), (102, 104, 101, 103),
                    (103, 105, 102, 104), (104, 106, 103, 105)])
    free = run_backtest(base_request(data))
    charged = run_backtest(base_request(data, commission_bps=5, spread_bps=4, slippage_bps=3))
    assert len(free.trades) == len(charged.trades) == 1
    assert charged.trades[0].net_pnl < free.trades[0].net_pnl
    assert charged.trades[0].fees > 0
    assert charged.trades[0].initial_risk_cash == pytest.approx(100.0)
    assert free.trades[0].initial_risk_cash == pytest.approx(100.0)


def test_open_position_closes_at_end_of_data(monkeypatch):
    patch_signal(monkeypatch)
    data = candles([(100, 101, 99, 100), (100, 102, 99, 101),
                    (100, 103, 99, 102), (102, 104, 101, 103),
                    (103, 105, 102, 104), (104, 106, 103, 105)])
    result = run_backtest(base_request(data))
    assert result.trades[0].exit_reason == "end_of_data"
    assert result.trades[0].exit_index == len(data) - 1
    assert len(result.equity_curve) == len(data)


def test_rejects_non_increasing_timestamps():
    data = candles([(100, 101, 99, 100)] * 6)
    data[3] = data[2]
    try:
        base_request(data)
        assert False, "expected timestamp validation error"
    except ValueError as exc:
        assert "strictly increasing" in str(exc)


def test_backtest_api_returns_metrics_and_trade_records(monkeypatch):
    patch_signal(monkeypatch)
    data = candles([(100, 101, 99, 100), (100, 102, 99, 101),
                    (100, 103, 99, 102), (102, 104, 101, 103),
                    (103, 105, 102, 104), (104, 106, 103, 105)])
    response = client.post("/api/v1/backtests/run", json={
        "candles": [c.model_dump() for c in data],
        "profile": {"pivot": 1, "atr_period": 3, "require_fvg": False},
    })
    assert response.status_code == 200
    payload = response.json()
    assert "source provenance" in payload["data_source_note"]
    assert "profit_factor" in payload["metrics"]
    assert len(payload["equity_curve"]) == len(data)


def test_gap_through_stop_fills_at_adverse_open(monkeypatch):
    patch_signal(monkeypatch)
    data = candles([(100, 101, 99, 100), (100, 102, 99, 101),
                    (100, 103, 99, 102), (90, 92, 88, 90),
                    (90, 91, 89, 90), (90, 91, 89, 90)])
    result = run_backtest(base_request(data))
    assert result.trades[0].exit_reason == "stop"
    assert result.trades[0].exit_price == 90


def test_entry_is_skipped_if_next_open_has_already_gapped_through_stop(monkeypatch):
    patch_signal(monkeypatch)
    data = candles([(100, 101, 99, 100), (100, 102, 99, 101),
                    (90, 92, 88, 90), (90, 91, 89, 90),
                    (90, 91, 89, 90), (90, 91, 89, 90)])
    result = run_backtest(base_request(data))
    assert result.trades == []


def test_contract_multiplier_scales_quantity_and_keeps_cash_risk(monkeypatch):
    patch_signal(monkeypatch)
    data = candles([(100, 101, 99, 100), (100, 102, 99, 101),
                    (100, 103, 99, 102), (102, 104, 101, 103),
                    (103, 105, 102, 104), (104, 106, 103, 105)])
    standard = run_backtest(base_request(data, market_type="stocks", contract_multiplier=1))
    doubled = run_backtest(base_request(data, market_type="stocks", contract_multiplier=2))
    assert len(standard.trades) == len(doubled.trades) == 1
    assert doubled.trades[0].quantity == standard.trades[0].quantity / 2
    assert abs(doubled.trades[0].gross_pnl - standard.trades[0].gross_pnl) < 1e-8


def test_positive_pnl_tax_is_disclosed_and_deducted(monkeypatch):
    patch_signal(monkeypatch)
    data = candles([(100, 101, 99, 100), (100, 102, 99, 101),
                    (100, 103, 99, 102), (102, 104, 101, 103),
                    (103, 105, 102, 104), (104, 106, 103, 105)])
    untaxed = run_backtest(base_request(data))
    taxed = run_backtest(base_request(data, tax_bps_on_positive_pnl=1000))
    assert taxed.trades[0].taxes > 0
    assert taxed.trades[0].net_pnl < untaxed.trades[0].net_pnl


def test_crypto_funding_cost_is_applied_to_elapsed_holding_time(monkeypatch):
    patch_signal(monkeypatch)
    data = candles([(100, 101, 99, 100), (100, 102, 99, 101),
                    (100, 103, 99, 102), (102, 104, 101, 103),
                    (103, 105, 102, 104), (104, 106, 103, 105)])
    funded = run_backtest(base_request(data, market_type="crypto", funding_bps_per_8h=1000))
    assert funded.trades[0].holding_costs > 0


def test_evaluation_window_blocks_pre_test_signals(monkeypatch):
    patch_signal(monkeypatch)
    data = candles([(100, 101, 99, 100), (100, 102, 99, 101),
                    (100, 103, 99, 102), (102, 104, 101, 103),
                    (103, 105, 102, 104), (104, 106, 103, 105)])
    result = run_backtest(base_request(data, evaluation_start_index=3))
    assert result.trades == []


def test_forex_swap_is_applied_as_elapsed_holding_cost(monkeypatch):
    patch_signal(monkeypatch)
    data = candles([(100, 101, 99, 100), (100, 102, 99, 101),
                    (100, 103, 99, 102), (102, 104, 101, 103),
                    (103, 105, 102, 104), (104, 106, 103, 105)])
    swapped = run_backtest(base_request(data, market_type="forex", swap_bps_per_day=1000))
    assert swapped.trades[0].holding_costs > 0


def test_stock_borrow_is_charged_only_for_short_positions(monkeypatch):
    bearish = SetupCandidate(
        direction="bearish", sweep_index=0, sweep_timestamp="2026-01-01T00:00:00Z",
        liquidity_level=101, structure_index=1, structure_timestamp="2026-01-01T00:01:00Z",
        structure_kind="BOS", displacement_range=2, prior_average_range=1,
        body_fraction=0.8, fvg_index=None, order_block_index=0,
        order_block_top=105, order_block_bottom=100, explanation="bearish test candidate",
    )
    monkeypatch.setattr("app.engine.backtest.analyze_setups",
                        lambda prefix, profile=None: SimpleNamespace(setups=[bearish] if len(prefix) == 2 else []))
    data = candles([(100, 101, 99, 100), (100, 102, 99, 99),
                    (100, 101, 97, 98), (98, 99, 95, 96),
                    (96, 97, 94, 95), (95, 96, 93, 94)])
    borrowed = run_backtest(base_request(data, market_type="stocks", borrow_bps_per_day=1000))
    assert borrowed.trades[0].direction == "short"
    assert borrowed.trades[0].holding_costs > 0
