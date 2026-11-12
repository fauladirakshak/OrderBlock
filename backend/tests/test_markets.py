from app.engine.markets import list_markets


def test_market_catalogue_covers_forex_crypto_and_stocks() -> None:
    result = list_markets()
    assert [market["id"] for market in result["markets"]] == ["forex", "crypto", "stocks"]
    symbols = {item["symbol"] for item in result["instruments"]}
    assert {"EUR/USD", "BTC/USDT", "NIFTY 50"}.issubset(symbols)
    assert result["data_status"] == "catalogue_only_no_market_prices"
