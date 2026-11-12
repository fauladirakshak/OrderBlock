"""Instrument identity and market-session metadata. Catalogue is not a price feed."""
from typing import Literal
from pydantic import BaseModel

AssetClass = Literal["forex", "crypto", "equity_index", "equity"]
ContractType = Literal["spot_fx", "spot", "perpetual", "equity", "index"]


class Instrument(BaseModel):
    symbol: str
    provider_symbol: str
    display_name: str
    asset_class: AssetClass
    venue: str
    venue_id: str
    contract_type: ContractType
    base_currency: str | None = None
    quote_currency: str
    price_precision: int
    tick_size: float
    timezone: str
    session: str
    session_open: str | None = None
    session_close: str | None = None
    trading_days: list[str]
    market_notes: list[str]
    tradeable_instrument: bool = True


INSTRUMENTS = [
    Instrument(symbol="EUR/USD", provider_symbol="EUR/USD", display_name="Euro / US Dollar", asset_class="forex", venue="OTC FX", venue_id="OTC:SPOT-FX", contract_type="spot_fx", base_currency="EUR", quote_currency="USD", price_precision=5, tick_size=0.00001, timezone="Etc/UTC", session="24x5", trading_days=["mon","tue","wed","thu","fri"], market_notes=["decentralized_spot_fx","provider_quote_source_must_be_disclosed","spread_required"]),
    Instrument(symbol="GBP/USD", provider_symbol="GBP/USD", display_name="British Pound / US Dollar", asset_class="forex", venue="OTC FX", venue_id="OTC:SPOT-FX", contract_type="spot_fx", base_currency="GBP", quote_currency="USD", price_precision=5, tick_size=0.00001, timezone="Etc/UTC", session="24x5", trading_days=["mon","tue","wed","thu","fri"], market_notes=["decentralized_spot_fx","provider_quote_source_must_be_disclosed","spread_required"]),
    Instrument(symbol="USD/JPY", provider_symbol="USD/JPY", display_name="US Dollar / Japanese Yen", asset_class="forex", venue="OTC FX", venue_id="OTC:SPOT-FX", contract_type="spot_fx", base_currency="USD", quote_currency="JPY", price_precision=3, tick_size=0.001, timezone="Etc/UTC", session="24x5", trading_days=["mon","tue","wed","thu","fri"], market_notes=["decentralized_spot_fx","provider_quote_source_must_be_disclosed","spread_required"]),
    Instrument(symbol="BTC/USDT", provider_symbol="BTCUSDT", display_name="Bitcoin / Tether", asset_class="crypto", venue="Binance", venue_id="BINANCE:SPOT", contract_type="spot", base_currency="BTC", quote_currency="USDT", price_precision=2, tick_size=0.01, timezone="Etc/UTC", session="24x7", trading_days=["mon","tue","wed","thu","fri","sat","sun"], market_notes=["venue_specific","spot_not_perpetual"]),
    Instrument(symbol="ETH/USDT", provider_symbol="ETHUSDT", display_name="Ether / Tether", asset_class="crypto", venue="Binance", venue_id="BINANCE:SPOT", contract_type="spot", base_currency="ETH", quote_currency="USDT", price_precision=2, tick_size=0.01, timezone="Etc/UTC", session="24x7", trading_days=["mon","tue","wed","thu","fri","sat","sun"], market_notes=["venue_specific","spot_not_perpetual"]),
    Instrument(symbol="NIFTY 50", provider_symbol="NIFTY 50", display_name="NIFTY 50 Index", asset_class="equity_index", venue="NSE", venue_id="XNSE:INDEX", contract_type="index", quote_currency="INR", price_precision=2, tick_size=0.05, timezone="Asia/Kolkata", session="exchange_calendar", session_open="09:15", session_close="15:30", trading_days=["mon","tue","wed","thu","fri"], market_notes=["index_value_not_tradeable_security","exchange_calendar_and_holidays_required"], tradeable_instrument=False),
    Instrument(symbol="RELIANCE", provider_symbol="RELIANCE", display_name="Reliance Industries", asset_class="equity", venue="NSE", venue_id="XNSE:EQUITY", contract_type="equity", quote_currency="INR", price_precision=2, tick_size=0.05, timezone="Asia/Kolkata", session="exchange_calendar", session_open="09:15", session_close="15:30", trading_days=["mon","tue","wed","thu","fri"], market_notes=["corporate_actions_required","exchange_data_entitlement_required"]),
    Instrument(symbol="HDFCBANK", provider_symbol="HDFCBANK", display_name="HDFC Bank", asset_class="equity", venue="NSE", venue_id="XNSE:EQUITY", contract_type="equity", quote_currency="INR", price_precision=2, tick_size=0.05, timezone="Asia/Kolkata", session="exchange_calendar", session_open="09:15", session_close="15:30", trading_days=["mon","tue","wed","thu","fri"], market_notes=["corporate_actions_required","exchange_data_entitlement_required"]),
    Instrument(symbol="INFY", provider_symbol="INFY", display_name="Infosys", asset_class="equity", venue="NSE", venue_id="XNSE:EQUITY", contract_type="equity", quote_currency="INR", price_precision=2, tick_size=0.05, timezone="Asia/Kolkata", session="exchange_calendar", session_open="09:15", session_close="15:30", trading_days=["mon","tue","wed","thu","fri"], market_notes=["corporate_actions_required","exchange_data_entitlement_required"]),
]


def get_instrument(symbol: str, venue_id: str | None = None, contract_type: str | None = None) -> Instrument:
    matches = [item for item in INSTRUMENTS if item.symbol == symbol]
    if venue_id:
        matches = [item for item in matches if item.venue_id == venue_id]
    if contract_type:
        matches = [item for item in matches if item.contract_type == contract_type]
    if not matches:
        raise ValueError(f"Unknown or ambiguous instrument identity: {symbol}")
    if len(matches) > 1:
        raise ValueError(f"Specify venue_id and contract_type for {symbol}")
    return matches[0]


def list_markets() -> dict:
    return {
        "markets": [
            {"id": "forex", "label": "Forex", "session_model": "24x5", "notes": ["Decentralized OTC spot FX; quote source must be disclosed"]},
            {"id": "crypto", "label": "Crypto", "session_model": "24x7", "notes": ["Venue and spot/perpetual contract identity are mandatory"]},
            {"id": "stocks", "label": "Stocks & Indices", "session_model": "exchange_calendar", "notes": ["Exchange timezone, holidays and corporate actions apply"]},
        ],
        "instruments": [item.model_dump() for item in INSTRUMENTS],
        "data_status": "catalogue_only_no_market_prices",
    }
