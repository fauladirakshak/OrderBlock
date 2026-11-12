from app.engine.markets import list_markets


def test_market_catalogue_covers_forex_crypto_and_stocks() -> None:
    result = list_markets()
    assert [market["id"] for market in result["markets"]] == ["forex", "crypto", "stocks"]
    symbols = {item["symbol"] for item in result["instruments"]}
    assert {"EUR/USD", "BTC/USDT", "NIFTY 50"}.issubset(symbols)
    assert result["data_status"] == "catalogue_only_no_market_prices"


def test_every_workspace_instrument_has_complete_venue_contract_metadata() -> None:
    result = list_markets()
    required = {"venue_id", "contract_type", "timezone", "session", "price_precision", "tick_size"}
    assert all(required.issubset(item) for item in result["instruments"])
    assert all(item["timezone"] and item["venue_id"] and item["contract_type"] for item in result["instruments"])


def test_catalogue_contains_every_frontend_selectable_instrument() -> None:
    result = list_markets()
    symbols = {item["symbol"] for item in result["instruments"]}
    assert {"EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CHF"}.issubset(symbols)
    assert {"BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"}.issubset(symbols)
    assert {"NIFTY 50", "BANKNIFTY", "RELIANCE", "HDFCBANK", "INFY"}.issubset(symbols)
