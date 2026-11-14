from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.engine import setups
from app.engine.setups import SetupProfile, analyze_setups
from app.engine.structure import Candle, StructureEvent, StructureResult
from app.engine.zones import FairValueGap
from app.main import app

client = TestClient(app)


def make_candles(count: int = 12, *, displacement: bool = True, sweep: bool = True) -> list[Candle]:
    candles = []
    for index in range(count):
        # Narrow, deterministic baseline candles.
        open_price = 10.5
        close_price = 10.7 if index % 2 == 0 else 10.3
        high = 11.0
        low = 10.0
        if index == 7 and sweep:
            low, close_price = 9.0, 10.5
        if index == 10 and displacement:
            open_price, close_price, high, low = 10.5, 14.0, 14.2, 10.2
        candles.append(Candle(
            timestamp=f"2026-01-01T00:{index:02d}:00Z",
            open=open_price,
            high=high,
            low=low,
            close=close_price,
            volume=100,
        ))
    return candles


def fake_structure() -> StructureResult:
    return StructureResult(
        swing_highs=[],
        swing_lows=[{
            "index": 3,
            "confirmation_index": 5,
            "timestamp": "2026-01-01T00:03:00Z",
            "price": 10.0,
        }],
        events=[StructureEvent(
            kind="CHoCH",
            direction="bullish",
            level=12.0,
            candle_index=10,
            timestamp="2026-01-01T00:10:00Z",
            explanation="Fixture bullish close break",
        )],
    )


def fake_gap():
    return [FairValueGap(
        direction="bullish",
        middle_candle_index=9,
        timestamp="2026-01-01T00:09:00Z",
        top=11.5,
        bottom=11.0,
        mitigated=False,
        filled=False,
        rule="fixture",
    )]


@pytest.fixture
def engine_fixtures(monkeypatch):
    monkeypatch.setattr(setups, "detect_structure", lambda candles, pivot: fake_structure())
    monkeypatch.setattr(setups, "detect_fair_value_gaps", lambda candles: fake_gap())


def test_emits_bullish_candidate_when_all_confluences_pass(engine_fixtures):
    candles = make_candles()
    profile = SetupProfile(pivot=2, sweep_lookback=10, atr_period=5)

    result = analyze_setups(candles, profile)

    assert len(result.setups) == 1
    candidate = result.setups[0]
    assert candidate.direction == "bullish"
    assert candidate.status == "candidate"
    assert candidate.sweep_index == 7
    assert candidate.liquidity_level == 10.0
    assert candidate.structure_index == 10
    assert candidate.structure_kind == "CHoCH"
    assert candidate.fvg_index == 9
    assert candidate.order_block_index == 9
    assert candidate.order_block_top == candles[9].high
    assert candidate.order_block_bottom == candles[9].low
    assert candidate.body_fraction == pytest.approx(3.5 / 4.0)


def test_ignores_setup_without_a_eligible_liquidity_sweep(engine_fixtures):
    result = analyze_setups(
        make_candles(sweep=False),
        SetupProfile(pivot=2, sweep_lookback=10, atr_period=5),
    )
    assert result.setups == []


def test_ignores_setup_below_displacement_threshold(engine_fixtures):
    result = analyze_setups(
        make_candles(displacement=False),
        SetupProfile(
            pivot=2,
            sweep_lookback=10,
            atr_period=5,
            min_displacement_atr=1.2,
        ),
    )
    assert result.setups == []


def test_fvg_can_be_optional(engine_fixtures, monkeypatch):
    monkeypatch.setattr(setups, "detect_fair_value_gaps", lambda candles: [])
    result = analyze_setups(
        make_candles(),
        SetupProfile(pivot=2, sweep_lookback=10, atr_period=5, require_fvg=False),
    )
    assert len(result.setups) == 1
    assert result.setups[0].fvg_index is None


def test_required_fvg_blocks_candidate_when_gap_missing(engine_fixtures, monkeypatch):
    monkeypatch.setattr(setups, "detect_fair_value_gaps", lambda candles: [])
    result = analyze_setups(
        make_candles(),
        SetupProfile(pivot=2, sweep_lookback=10, atr_period=5, require_fvg=True),
    )
    assert result.setups == []


def test_sweep_must_happen_after_swing_confirmation(engine_fixtures, monkeypatch):
    structure = fake_structure()
    structure.swing_lows[0]["confirmation_index"] = 7
    monkeypatch.setattr(setups, "detect_structure", lambda candles, pivot: structure)

    result = analyze_setups(
        make_candles(),
        SetupProfile(pivot=2, sweep_lookback=10, atr_period=5),
    )
    assert result.setups == []


def test_profile_rejects_out_of_range_configuration():
    with pytest.raises(ValueError):
        SetupProfile(pivot=0)
    with pytest.raises(ValueError):
        SetupProfile(min_body_fraction=1.5)
    with pytest.raises(ValueError):
        SetupProfile(sweep_lookback=2)


def test_setup_api_returns_profile_and_candidate():
    client = TestClient(app)
    candles = make_candles()
    # API integration test exercises request parsing and response serialization.
    # Patch only the pattern dependencies to keep the fixture deterministic.
    from unittest.mock import patch

    with patch("app.engine.setups.detect_structure", return_value=fake_structure()), patch(
        "app.engine.setups.detect_fair_value_gaps", return_value=fake_gap()
    ):
        response = client.post(
            "/api/v1/analysis/setups",
            json={
                "candles": [candle.model_dump() for candle in candles],
                "profile": {
                    "pivot": 2,
                    "sweep_lookback": 10,
                    "atr_period": 5,
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["profile"]["pivot"] == 2
    assert payload["setups"][0]["direction"] == "bullish"
    assert payload["setups"][0]["fvg_index"] == 9


def test_setup_api_rejects_insufficient_history():
    client = TestClient(app)
    response = client.post(
        "/api/v1/analysis/setups",
        json={
            "candles": [candle.model_dump() for candle in make_candles(5)],
            "profile": {"pivot": 2, "atr_period": 14},
        },
    )
    assert response.status_code == 422


def test_emits_bearish_candidate_for_high_sweep_and_bearish_displacement(monkeypatch):
    candles = make_candles()
    candles[7] = Candle(
        timestamp=candles[7].timestamp,
        open=11.5, high=13.0, low=11.0, close=11.5, volume=100,
    )
    candles[9] = Candle(
        timestamp=candles[9].timestamp,
        open=10.3, high=11.0, low=10.0, close=10.5, volume=100,
    )
    candles[10] = Candle(
        timestamp=candles[10].timestamp,
        open=14.0, high=14.2, low=10.2, close=10.5, volume=100,
    )
    bearish_structure = StructureResult(
        swing_highs=[{
            "index": 3,
            "confirmation_index": 5,
            "timestamp": "2026-01-01T00:03:00Z",
            "price": 12.0,
        }],
        swing_lows=[],
        events=[StructureEvent(
            kind="CHoCH",
            direction="bearish",
            level=9.0,
            candle_index=10,
            timestamp="2026-01-01T00:10:00Z",
            explanation="Fixture bearish close break",
        )],
    )
    bearish_gap = FairValueGap(
        direction="bearish",
        middle_candle_index=9,
        timestamp="2026-01-01T00:09:00Z",
        top=12.0,
        bottom=11.5,
        mitigated=False,
        filled=False,
        rule="fixture",
    )
    monkeypatch.setattr(setups, "detect_structure", lambda candles, pivot: bearish_structure)
    monkeypatch.setattr(setups, "detect_fair_value_gaps", lambda candles: [bearish_gap])

    result = analyze_setups(
        candles,
        SetupProfile(pivot=2, sweep_lookback=10, atr_period=5),
    )

    assert len(result.setups) == 1
    candidate = result.setups[0]
    assert candidate.direction == "bearish"
    assert candidate.sweep_index == 7
    assert candidate.liquidity_level == 12.0
    assert candidate.structure_kind == "CHoCH"
    assert candidate.fvg_index == 9
    assert candidate.order_block_index == 9



def test_order_block_must_form_after_the_liquidity_sweep(engine_fixtures):
    candles = make_candles()
    # Remove all bearish candles between the sweep (bar 7) and displacement (bar 10).
    candles[8] = Candle(timestamp=candles[8].timestamp, open=10.2, high=11.0, low=10.0, close=10.8)
    candles[9] = Candle(timestamp=candles[9].timestamp, open=10.2, high=11.0, low=10.0, close=10.8)

    result = analyze_setups(
        candles,
        SetupProfile(pivot=2, sweep_lookback=10, atr_period=5),
    )

    assert len(result.setups) == 1
    assert result.setups[0].order_block_index is None
    assert result.setups[0].order_block_top is None



def test_setup_api_rejects_unordered_candle_timestamps():
    candles = [c.model_dump() for c in make_candles()]
    candles[6]["timestamp"] = candles[5]["timestamp"]
    response = client.post("/api/v1/analysis/setups", json={
        "candles": candles,
        "profile": {"pivot": 2, "sweep_lookback": 10, "atr_period": 5},
    })
    assert response.status_code == 422
    assert "strictly increasing" in response.json()["detail"][0]["msg"]



def test_rejects_counter_direction_displacement_even_when_range_is_large(engine_fixtures):
    candles = make_candles()
    candles[10] = Candle(
        timestamp=candles[10].timestamp,
        open=14.0, high=14.2, low=10.2, close=10.5, volume=100,
    )
    result = analyze_setups(
        candles,
        SetupProfile(pivot=2, sweep_lookback=10, atr_period=5),
    )
    assert result.setups == []


def test_required_fvg_must_match_structure_direction(engine_fixtures, monkeypatch):
    opposing_gap = FairValueGap(
        direction="bearish",
        middle_candle_index=9,
        timestamp="2026-01-01T00:09:00Z",
        top=12.0,
        bottom=11.5,
        mitigated=False,
        filled=False,
        rule="fixture opposing gap",
    )
    monkeypatch.setattr(setups, "detect_fair_value_gaps", lambda candles: [opposing_gap])
    result = analyze_setups(
        make_candles(),
        SetupProfile(pivot=2, sweep_lookback=10, atr_period=5, require_fvg=True),
    )
    assert result.setups == []


def test_optional_opposing_fvg_is_not_attached_to_candidate(engine_fixtures, monkeypatch):
    opposing_gap = FairValueGap(
        direction="bearish",
        middle_candle_index=9,
        timestamp="2026-01-01T00:09:00Z",
        top=12.0,
        bottom=11.5,
        mitigated=False,
        filled=False,
        rule="fixture opposing gap",
    )
    monkeypatch.setattr(setups, "detect_fair_value_gaps", lambda candles: [opposing_gap])
    result = analyze_setups(
        make_candles(),
        SetupProfile(pivot=2, sweep_lookback=10, atr_period=5, require_fvg=False),
    )
    assert len(result.setups) == 1
    assert result.setups[0].fvg_index is None
