"""Static, explicit market catalogue. These are instrument definitions, not price feeds."""
from typing import Literal
from pydantic import BaseModel

AssetClass = Literal["forex", "crypto", "equity_index", "equity"]


class Instrument(BaseModel):
    symbol: str
    display_name: str
    asset_class: AssetClass
    venue: str
    quote_currency: str
    price_precision: int
    tick_size: float
    session: str
    market_notes: list[str]


INSTRUMENTS = [
    Instrument(symbol="EUR/USD", display_name="Euro / US Dollar", asset_class="forex", venue="OTC", quote_currency="USD", price_precision=5, tick_size=0.00001, session="24x5", market_notes=["decentralized_spot_fx", "spread_required"]),
    Instrument(symbol="GBP/USD", display_name="British Pound / US Dollar", asset_class="forex", venue="OTC", quote_currency="USD", price_precision=5, tick_size=0.00001, session="24x5", market_notes=["decentralized_spot_fx", "spread_required"]),
    Instrument(symbol="USD/JPY", display_name="US Dollar / Japanese Yen", asset_class="forex", venue="OTC", quote_currency="JPY", price_precision=3, tick_size=0.001, session="24x5", market_notes=["decentralized_spot_fx", "spread_required"]),
    Instrument(symbol="BTC/USDT", display_name="Bitcoin / Tether", asset_class="crypto", venue="exchange_specific", quote_currency="USDT", price_precision=2, tick_size=0.01, session="24x7", market_notes=["venue_specific", "spot_or_perpetual_must_be_explicit"]),
    Instrument(symbol="ETH/USDT", display_name="Ether / Tether", asset_class="crypto", venue="exchange_specific", quote_currency="USDT", price_precision=2, tick_size=0.01, session="24x7", market_notes=["venue_specific", "spot_or_perpetual_must_be_explicit"]),
    Instrument(symbol="NIFTY 50", display_name="NIFTY 50 Index", asset_class="equity_index", venue="NSE", quote_currency="INR", price_precision=2, tick_size=0.05, session="exchange_calendar", market_notes=["exchange_calendar_required", "index_value_not_tradeable_security"]),
    Instrument(symbol="RELIANCE", display_name="Reliance Industries", asset_class="equity", venue="NSE", quote_currency="INR", price_precision=2, tick_size=0.05, session="exchange_calendar", market_notes=["corporate_actions_required"]),
]


def list_markets() -> dict:
    return {
        "markets": [
            {"id": "forex", "label": "Forex", "session_model": "24x5", "notes": ["OTC spot FX is decentralized", "Use provider-specific bid/ask and tick-volume metadata"]},
            {"id": "crypto", "label": "Crypto", "session_model": "24x7", "notes": ["Keep venue and spot/perpetual contract identity", "Funding and open interest are optional provider data"]},
            {"id": "stocks", "label": "Stocks & Indices", "session_model": "exchange_calendar", "notes": ["Respect exchange sessions, holidays and corporate actions"]},
        ],
        "instruments": [item.model_dump() for item in INSTRUMENTS],
        "data_status": "catalogue_only_no_market_prices",
    }
