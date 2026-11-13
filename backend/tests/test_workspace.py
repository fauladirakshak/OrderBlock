from fastapi.testclient import TestClient

from app.main import app
from app.engine.structure import Candle
from app.engine.workspace import analyze_workspace

client = TestClient(app)


def make_candles():
    # Stable alternating series with a confirmed swing low, reclaim sweep and break.
    values = [
        (10, 12, 9, 11), (11, 13, 10, 12), (12, 14, 11, 13),
        (13, 14, 10, 11), (11, 12, 8, 9), (9, 12, 9, 11),
        (11, 13, 10, 12), (12, 15, 11, 14), (14, 17, 13, 16),
        (16, 18, 15, 17), (17, 19, 16, 18),
    ]
    return [
        Candle(timestamp=f"2026-01-01T00:{i:02d}:00Z", open=o, high=h, low=l, close=c)
        for i, (o, h, l, c) in enumerate(values)
    ]


def test_workspace_analysis_returns_all_overlay_collections():
    result = analyze_workspace(make_candles(), pivot=1)
    assert isinstance(result.structure_events, list)
    assert isinstance(result.order_blocks, list)
    assert isinstance(result.fair_value_gaps, list)
    assert isinstance(result.liquidity_sweeps, list)
    assert result.notes


def test_workspace_api_rejects_insufficient_history():
    response = client.post("/api/v1/analysis/workspace", json={
        "pivot": 2,
        "candles": [
            {"timestamp": f"2026-01-01T00:0{i}:00Z", "open": 1, "high": 2, "low": 0.5, "close": 1.5}
            for i in range(4)
        ],
    })
    assert response.status_code == 422


def test_workspace_api_serializes_overlay_payload():
    response = client.post("/api/v1/analysis/workspace", json={
        "pivot": 1,
        "candles": [c.model_dump() for c in make_candles()],
    })
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"structure_events", "order_blocks", "fair_value_gaps", "liquidity_sweeps", "notes"}


def test_workspace_marks_sweep_only_after_swing_confirmation():
    values = [
        (10, 11, 9, 10.5), (10.5, 11, 8, 9), (9, 10, 7, 8),
        (8, 10, 8, 9), (9, 10, 8, 9.5), (9, 10, 6.5, 8),
        (8, 10, 7.5, 9), (9, 11, 8, 10),
    ]
    candles = [
        Candle(timestamp=f"2026-02-01T00:{i:02d}:00Z", open=o, high=h, low=l, close=c)
        for i, (o, h, l, c) in enumerate(values)
    ]
    result = analyze_workspace(candles, pivot=1)
    assert any(
        sweep.direction == "bullish" and sweep.candle_index == 5 and sweep.level == 7
        for sweep in result.liquidity_sweeps
    )



def test_workspace_api_rejects_unordered_and_timezone_naive_candles():
    candles = [c.model_dump() for c in make_candles()]
    unordered = [dict(c) for c in candles]
    unordered[5]["timestamp"] = unordered[4]["timestamp"]
    response = client.post("/api/v1/analysis/workspace", json={"pivot": 1, "candles": unordered})
    assert response.status_code == 422
    assert "strictly increasing" in response.json()["detail"][0]["msg"]

    naive = [dict(c) for c in candles]
    naive[0]["timestamp"] = "2026-01-01T00:00:00"
    response = client.post("/api/v1/analysis/workspace", json={"pivot": 1, "candles": naive})
    assert response.status_code == 422
    assert "timezone" in response.json()["detail"][0]["msg"]
