from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator
from app.engine.markets import list_markets
from app.engine.providers import ProviderConfigurationError, MarketDataProviderError
from app.engine.structure import Candle, StructureResult, detect_structure
from app.engine.zones import ZoneAnalysis, analyze_zones
from app.engine.setups import SetupAnalysis, SetupProfile, analyze_setups
from app.engine.market_data import CandleSeries, Market, Timeframe, load_candle_series
from app.engine.workspace import WorkspaceAnalysis, analyze_workspace
from app.engine.multi_timeframe import MultiTimeframeAnalysis, MultiTimeframeRequest, analyze_multi_timeframe
from app.engine.historical_import import HistoricalImportRequest, HistoricalImportResult, parse_historical_csv
from app.engine.backtest import BacktestRequest, BacktestResult, run_backtest
from app.engine.walk_forward import WalkForwardRequest, WalkForwardResult, run_walk_forward
from app.engine.nse_bhavcopy import NseBhavcopyRequest, parse_nse_udiff_zip
from app.engine.histdata_forex import HistDataForexRequest, parse_histdata_forex_zip
from app.engine.dukascopy_bi5 import DukascopyBi5Request, parse_dukascopy_bi5_zip
from app.engine.session_context import SessionAnalysis, SessionAnalysisRequest, analyze_sessions
from app.engine.liquidity_references import LiquidityReferenceRequest, LiquidityReferenceResult, analyze_liquidity_references
from app.engine.dealing_range import DealingRangeRequest, DealingRangeResult, analyze_dealing_range
from app.engine.higher_timeframe_ranges import HigherTimeframeRangeRequest, HigherTimeframeRangeResult, analyze_higher_timeframe_ranges
from app.engine.higher_timeframe_zones import HigherTimeframeZonesRequest, HigherTimeframeZonesResult, analyze_higher_timeframe_zones

app = FastAPI(title="OrderBlock API", version="0.6.0",
              description="Multi-market, research-first price-action analysis. Not investment advice.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _validate_candle_series_order(candles: list[Candle]) -> None:
    stamps: list[datetime] = []
    for candle in candles:
        try:
            parsed = datetime.fromisoformat(candle.timestamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("candle timestamps must be ISO-8601 values") from exc
        if parsed.tzinfo is None:
            raise ValueError("candle timestamps must include a timezone")
        stamps.append(parsed.astimezone(timezone.utc))
    if any(right <= left for left, right in zip(stamps, stamps[1:])):
        raise ValueError("candle timestamps must be strictly increasing")


class StructureRequest(BaseModel):
    candles: list[Candle] = Field(min_length=5, max_length=5000)
    pivot: int = Field(default=2, ge=1, le=20)

    @model_validator(mode="after")
    def validate_order(self) -> "StructureRequest":
        _validate_candle_series_order(self.candles)
        return self


class SetupRequest(BaseModel):
    candles: list[Candle] = Field(min_length=5, max_length=5000)
    profile: SetupProfile = Field(default_factory=SetupProfile)

    @model_validator(mode="after")
    def validate_order(self) -> "SetupRequest":
        _validate_candle_series_order(self.candles)
        return self


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "orderblock-api"}


@app.get("/api/v1/markets")
def markets() -> dict:
    """Return supported market categories and instrument metadata, not live prices."""
    return list_markets()


@app.post("/api/v1/analysis/structure", response_model=StructureResult)
def analyze_market_structure(request: StructureRequest) -> StructureResult:
    if len(request.candles) < (2 * request.pivot + 1):
        raise HTTPException(status_code=422, detail="Not enough candles to confirm a pivot.")
    return detect_structure(request.candles, pivot=request.pivot)


@app.post("/api/v1/analysis/zones", response_model=ZoneAnalysis)
def analyze_price_action_zones(request: StructureRequest) -> ZoneAnalysis:
    if len(request.candles) < (2 * request.pivot + 1):
        raise HTTPException(status_code=422, detail="Not enough candles to confirm a pivot.")
    return analyze_zones(request.candles, pivot=request.pivot)


@app.post("/api/v1/analysis/setups", response_model=SetupAnalysis)
def analyze_ict_inspired_setups(request: SetupRequest) -> SetupAnalysis:
    """Return configurable sweep + displacement + structure + FVG candidates."""
    minimum = max(2 * request.profile.pivot + 1, request.profile.atr_period + 2)
    if len(request.candles) < minimum:
        raise HTTPException(
            status_code=422,
            detail=f"Not enough candles for this profile; at least {minimum} are required.",
        )
    return analyze_setups(request.candles, profile=request.profile)


@app.post("/api/v1/analysis/workspace", response_model=WorkspaceAnalysis)
def analyze_trading_workspace(request: StructureRequest) -> WorkspaceAnalysis:
    """Return chart-ready structure, OB, FVG and liquidity-sweep annotations."""
    if len(request.candles) < (2 * request.pivot + 1):
        raise HTTPException(status_code=422, detail="Not enough candles to confirm a pivot.")
    return analyze_workspace(request.candles, pivot=request.pivot)


@app.post("/api/v1/analysis/multi-timeframe", response_model=MultiTimeframeAnalysis)
def analyze_multi_timeframe_context(request: MultiTimeframeRequest) -> MultiTimeframeAnalysis:
    """Compare primary chart structure with supplied higher-timeframe structure."""
    return analyze_multi_timeframe(request)


@app.get("/api/v1/market-data/candles", response_model=CandleSeries)
def get_market_candles(
    market: Market,
    symbol: str = Query(min_length=1, max_length=32),
    timeframe: Timeframe = "1H",
    limit: int = Query(default=200, ge=20, le=1000),
    venue_id: str | None = Query(default=None, max_length=40),
    contract_type: str | None = Query(default=None, max_length=20),
) -> CandleSeries:
    """Return OHLC candles from the explicitly configured provider."""
    try:
        return load_candle_series(market, symbol, timeframe, limit, venue_id, contract_type)
    except (ProviderConfigurationError, MarketDataProviderError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.post("/api/v1/market-data/import/csv", response_model=HistoricalImportResult)
def import_historical_csv(request: HistoricalImportRequest) -> HistoricalImportResult:
    """Validate and normalize a user-supplied historical OHLCV CSV dataset."""
    try:
        candles = parse_historical_csv(request.csv_text, request.timezone)
        return HistoricalImportResult(
            symbol=request.symbol, market=request.market, timeframe=request.timeframe,
            timezone=request.timezone, candle_count=len(candles), candles=candles,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc



@app.post("/api/v1/backtests/run", response_model=BacktestResult)
def run_historical_backtest(request: BacktestRequest) -> BacktestResult:
    """Run a deterministic, no-lookahead OHLC research backtest on supplied candles."""
    try:
        return run_backtest(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc



@app.post("/api/v1/backtests/walk-forward", response_model=WalkForwardResult)
def run_walk_forward_backtest(request: WalkForwardRequest) -> WalkForwardResult:
    """Run chronological rolling out-of-sample folds and a buy-and-hold benchmark."""
    try:
        return run_walk_forward(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc



@app.post("/api/v1/market-data/import/nse-udiff", response_model=HistoricalImportResult)
def import_nse_udiff_bhavcopy(request: NseBhavcopyRequest) -> HistoricalImportResult:
    """Import a user-downloaded NSE UDiFF CM daily bhavcopy ZIP for one symbol/series."""
    try:
        return parse_nse_udiff_zip(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc



@app.post("/api/v1/market-data/import/histdata-forex", response_model=HistoricalImportResult)
def import_histdata_forex_zip(request: HistDataForexRequest) -> HistoricalImportResult:
    """Import a user-downloaded HistData Generic ASCII M1 Forex ZIP."""
    try:
        return parse_histdata_forex_zip(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc



@app.post("/api/v1/market-data/import/dukascopy-bi5", response_model=HistoricalImportResult)
def import_dukascopy_bi5_archive(request: DukascopyBi5Request) -> HistoricalImportResult:
    """Import user-downloaded classic Dukascopy hourly BI5 tick files and aggregate bid OHLC bars."""
    try:
        return parse_dukascopy_bi5_zip(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc



@app.post("/api/v1/analysis/sessions", response_model=SessionAnalysis)
def analyze_market_sessions(request: SessionAnalysisRequest) -> SessionAnalysis:
    """Summarize timezone-aware regional or exchange sessions from supplied candles."""
    try:
        return analyze_sessions(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc



@app.post("/api/v1/analysis/liquidity-references", response_model=LiquidityReferenceResult)
def analyze_liquidity_reference_levels(request: LiquidityReferenceRequest) -> LiquidityReferenceResult:
    """Return previous-period and confirmed equal-swing liquidity reference levels."""
    try:
        return analyze_liquidity_references(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc







@app.post("/api/v1/analysis/higher-timeframe-zones", response_model=HigherTimeframeZonesResult)
def analyze_higher_timeframe_order_blocks_and_gaps(request: HigherTimeframeZonesRequest) -> HigherTimeframeZonesResult:
    """Analyse independently supplied higher-timeframe order blocks and fair value gaps."""
    try:
        return analyze_higher_timeframe_zones(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/analysis/higher-timeframe-ranges", response_model=HigherTimeframeRangeResult)
def analyze_higher_timeframe_dealing_ranges(request: HigherTimeframeRangeRequest) -> HigherTimeframeRangeResult:
    """Compare independently supplied, completed higher-timeframe dealing ranges."""
    try:
        return analyze_higher_timeframe_ranges(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/analysis/dealing-range", response_model=DealingRangeResult)
def analyze_premium_discount_range(request: DealingRangeRequest) -> DealingRangeResult:
    """Return premium/discount context from eligible confirmed swing points."""
    try:
        return analyze_dealing_range(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
