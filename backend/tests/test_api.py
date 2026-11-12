from fastapi.testclient import TestClient

from app.main import app


def test_markets_endpoint_returns_catalogue_without_quotes() -> None:
    response = TestClient(app).get("/api/v1/markets")
    assert response.status_code == 200
    payload = response.json()
    assert payload["data_status"] == "catalogue_only_no_market_prices"
    assert {market["id"] for market in payload["markets"]} == {"forex", "crypto", "stocks"}
