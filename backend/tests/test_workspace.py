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
