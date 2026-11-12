from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from app.engine.structure import Candle, StructureResult, detect_structure

app = FastAPI(title="OrderBlock API", version="0.1.0",
              description="Research-first market structure analysis. Not investment advice.")


class StructureRequest(BaseModel):
    candles: list[Candle] = Field(min_length=5)
    pivot: int = Field(default=2, ge=1, le=20)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "orderblock-api"}


@app.post("/api/v1/analysis/structure", response_model=StructureResult)
def analyze_structure(request: StructureRequest) -> StructureResult:
    if len(request.candles) < (2 * request.pivot + 1):
        raise HTTPException(status_code=422, detail="Not enough candles to confirm a pivot.")
    return detect_structure(request.candles, pivot=request.pivot)
