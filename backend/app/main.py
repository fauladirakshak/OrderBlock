from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from app.engine.markets import list_markets
from app.engine.structure import Candle, StructureResult, detect_structure
from app.engine.zones import ZoneAnalysis, analyze_zones
from app.engine.setups import SetupAnalysis, SetupProfile, analyze_setups

app = FastAPI(title="OrderBlock API", version="0.4.0",
              description="Multi-market, research-first price-action analysis. Not investment advice.")


class StructureRequest(BaseModel):
    candles: list[Candle] = Field(min_length=5)
    pivot: int = Field(default=2, ge=1, le=20)


class SetupRequest(BaseModel):
    candles: list[Candle] = Field(min_length=5)
    profile: SetupProfile = Field(default_factory=SetupProfile)


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
