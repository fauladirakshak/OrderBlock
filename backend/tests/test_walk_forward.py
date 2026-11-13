from fastapi.testclient import TestClient

from app.engine.setups import SetupProfile
from app.engine.structure import Candle
from app.engine.walk_forward import WalkForwardRequest, run_walk_forward
from app.main import app

client = TestClient(app)


def make_candles(count, step=0.25):
    rows = []
    price = 100.0
    for index in range(count):
        open_price = price
        close = price + (step if index % 3 else -step / 2)
        rows.append(Candle(
            timestamp=f"2026-02-{1 + index // 1440:02d}T{(index // 60) % 24:02d}:{index % 60:02d}:00Z",
            open=open_price, high=max(open_price, close) + 0.4,
            low=min(open_price, close) - 0.4, close=close,
        ))
        price = close
    return rows


def request_for(data, **overrides):
    values = dict(
        candles=data,
        profile=SetupProfile(pivot=1, atr_period=3, sweep_lookback=5, require_fvg=False),
        training_window_bars=20, test_window_bars=10, step_bars=10,
        starting_equity=10000,
    )
    values.update(overrides)
    return WalkForwardRequest(**values)


def test_walk_forward_creates_chronological_folds_and_benchmark():
    data = make_candles(55)
    result = run_walk_forward(request_for(data))
    assert result.fold_count == 4
    assert result.folds[0].training_end < result.folds[0].test_start
    assert result.folds[0].test_end < result.folds[1].test_start
    assert result.folds[0].out_of_sample_metrics.starting_equity == 10000
    assert result.folds[0].benchmark_return_pct != 0
    assert result.total_out_of_sample_trades >= 0


def test_walk_forward_rejects_too_short_training_window():
    data = make_candles(50)
    try:
        run_walk_forward(request_for(data, training_window_bars=5, profile=SetupProfile(pivot=2, atr_period=14, require_fvg=False)))
        assert False, "expected minimum training window validation"
    except ValueError as exc:
        assert "at least" in str(exc)


def test_walk_forward_api_returns_fold_metrics():
    data = make_candles(55)
    response = client.post("/api/v1/backtests/walk-forward", json={
        "candles": [item.model_dump() for item in data],
        "profile": {"pivot": 1, "atr_period": 3, "sweep_lookback": 5, "require_fvg": False},
        "training_window_bars": 20, "test_window_bars": 10, "step_bars": 10,
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["fold_count"] == 4
    assert len(payload["folds"]) == 4
    assert "benchmark_return_pct" in payload["folds"][0]
    assert "average_excess_return_pct" in payload
