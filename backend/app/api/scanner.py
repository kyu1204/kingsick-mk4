"""
Stock Scanner API router for KingSick.

Provides endpoints for AI-powered stock market scanning.
"""

from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.auth import get_current_user
from app.models import User
from app.services.indicator import IndicatorCalculator
from app.services.kis_api import KISApiClient
from app.services.signal_generator import SignalGenerator
from app.services.stock_scanner import ScanResult, ScanType, StockScanner, StockUniverse

router = APIRouter(prefix="/scan", tags=["Scanner"])


class ScanTypeEnum(str, Enum):
    """Scan type for API."""

    BUY = "BUY"
    SELL = "SELL"


class ScanResultResponse(BaseModel):
    """Response for a single scan result."""

    stock_code: str = Field(..., description="Stock code")
    stock_name: str = Field(..., description="Stock name")
    signal: str = Field(..., description="Signal type (BUY/SELL)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    current_price: float = Field(..., description="Current stock price")
    rsi: float = Field(..., description="RSI value")
    volume_spike: bool = Field(..., description="Whether volume spike detected")
    reasoning: list[str] = Field(default_factory=list, description="Signal reasoning")


class ScanResponse(BaseModel):
    """Response for scan operation."""

    results: list[ScanResultResponse] = Field(..., description="Scan results")
    total: int = Field(..., description="Total results count")
    scan_type: str = Field(..., description="Scan type used")
    min_confidence: float = Field(..., description="Minimum confidence threshold")


class StockInfo(BaseModel):
    """Stock information."""

    code: str = Field(..., description="Stock code")
    name: str = Field(..., description="Stock name")


class StockUniverseResponse(BaseModel):
    """Response for stock universe."""

    kospi: list[StockInfo] = Field(..., description="KOSPI stocks")
    kosdaq: list[StockInfo] = Field(..., description="KOSDAQ stocks")
    total: int = Field(..., description="Total stock count")


def scan_result_to_response(result: ScanResult) -> ScanResultResponse:
    """Convert ScanResult to response schema."""
    return ScanResultResponse(
        stock_code=result.stock_code,
        stock_name=result.stock_name,
        signal=result.signal,
        confidence=result.confidence,
        current_price=result.current_price,
        rsi=result.rsi,
        volume_spike=result.volume_spike,
        reasoning=result.reasoning,
    )


def get_scanner() -> StockScanner:
    """Create a StockScanner instance with dependencies."""
    kis_api = KISApiClient()
    indicator_calc = IndicatorCalculator()
    signal_generator = SignalGenerator(indicator_calc)
    return StockScanner(kis_api, signal_generator)


@router.get(
    "",
    response_model=ScanResponse,
)
async def scan_market(
    current_user: Annotated[User, Depends(get_current_user)],
    scan_type: ScanTypeEnum = Query(ScanTypeEnum.BUY, description="Scan type"),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0, description="Minimum confidence"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
):
    """
    Scan the market for trading opportunities.

    Analyzes stocks in the universe and returns those matching the criteria.
    Requires authentication.
    """
    try:
        scanner = get_scanner()
        internal_scan_type = ScanType.BUY if scan_type == ScanTypeEnum.BUY else ScanType.SELL

        results = await scanner.scan_market(
            scan_type=internal_scan_type,
            min_confidence=min_confidence,
            limit=limit,
        )

        return ScanResponse(
            results=[scan_result_to_response(r) for r in results],
            total=len(results),
            scan_type=scan_type.value,
            min_confidence=min_confidence,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scan failed: {e!s}",
        ) from e


@router.get(
    "/universe",
    response_model=StockUniverseResponse,
)
async def get_stock_universe(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get the stock universe available for scanning.

    Returns the list of KOSPI and KOSDAQ stocks that can be scanned.
    Requires authentication.
    """
    universe = StockUniverse()
    kospi = universe.get_kospi_stocks()
    kosdaq = universe.get_kosdaq_stocks()

    return StockUniverseResponse(
        kospi=[StockInfo(code=s["code"], name=s["name"]) for s in kospi],
        kosdaq=[StockInfo(code=s["code"], name=s["name"]) for s in kosdaq],
        total=len(kospi) + len(kosdaq),
    )
