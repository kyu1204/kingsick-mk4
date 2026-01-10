"""
Stocks API router for KingSick.

Provides endpoints for stock search and information.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.models import User

router = APIRouter(prefix="/stocks", tags=["Stocks"])


# Sample stock data for search (Korean KOSPI/KOSDAQ stocks)
# In production, this would be fetched from KIS API or stock master database
STOCK_DATABASE = [
    {"code": "005930", "name": "삼성전자", "market": "KOSPI"},
    {"code": "000660", "name": "SK하이닉스", "market": "KOSPI"},
    {"code": "373220", "name": "LG에너지솔루션", "market": "KOSPI"},
    {"code": "207940", "name": "삼성바이오로직스", "market": "KOSPI"},
    {"code": "005380", "name": "현대차", "market": "KOSPI"},
    {"code": "006400", "name": "삼성SDI", "market": "KOSPI"},
    {"code": "051910", "name": "LG화학", "market": "KOSPI"},
    {"code": "035420", "name": "NAVER", "market": "KOSPI"},
    {"code": "000270", "name": "기아", "market": "KOSPI"},
    {"code": "035720", "name": "카카오", "market": "KOSPI"},
    {"code": "005490", "name": "POSCO홀딩스", "market": "KOSPI"},
    {"code": "028260", "name": "삼성물산", "market": "KOSPI"},
    {"code": "105560", "name": "KB금융", "market": "KOSPI"},
    {"code": "055550", "name": "신한지주", "market": "KOSPI"},
    {"code": "066570", "name": "LG전자", "market": "KOSPI"},
    {"code": "003550", "name": "LG", "market": "KOSPI"},
    {"code": "096770", "name": "SK이노베이션", "market": "KOSPI"},
    {"code": "034730", "name": "SK", "market": "KOSPI"},
    {"code": "017670", "name": "SK텔레콤", "market": "KOSPI"},
    {"code": "012330", "name": "현대모비스", "market": "KOSPI"},
    {"code": "003670", "name": "포스코퓨처엠", "market": "KOSPI"},
    {"code": "086790", "name": "하나금융지주", "market": "KOSPI"},
    {"code": "033780", "name": "KT&G", "market": "KOSPI"},
    {"code": "009150", "name": "삼성전기", "market": "KOSPI"},
    {"code": "018260", "name": "삼성에스디에스", "market": "KOSPI"},
    {"code": "032830", "name": "삼성생명", "market": "KOSPI"},
    {"code": "010130", "name": "고려아연", "market": "KOSPI"},
    {"code": "030200", "name": "KT", "market": "KOSPI"},
    {"code": "011200", "name": "HMM", "market": "KOSPI"},
    {"code": "034020", "name": "두산에너빌리티", "market": "KOSPI"},
    # KOSDAQ stocks
    {"code": "247540", "name": "에코프로비엠", "market": "KOSDAQ"},
    {"code": "086520", "name": "에코프로", "market": "KOSDAQ"},
    {"code": "091990", "name": "셀트리온헬스케어", "market": "KOSDAQ"},
    {"code": "196170", "name": "알테오젠", "market": "KOSDAQ"},
    {"code": "263750", "name": "펄어비스", "market": "KOSDAQ"},
    {"code": "293490", "name": "카카오게임즈", "market": "KOSDAQ"},
    {"code": "035900", "name": "JYP Ent.", "market": "KOSDAQ"},
    {"code": "041510", "name": "에스엠", "market": "KOSDAQ"},
    {"code": "352820", "name": "하이브", "market": "KOSPI"},
    {"code": "112040", "name": "위메이드", "market": "KOSDAQ"},
]


# Response schemas


class StockInfo(BaseModel):
    """Stock information."""

    code: str
    name: str
    market: str


class StockSearchResponse(BaseModel):
    """Response for stock search."""

    stocks: list[StockInfo]
    total: int


# Endpoints


@router.get(
    "/search",
    response_model=StockSearchResponse,
)
async def search_stocks(
    current_user: Annotated[User, Depends(get_current_user)],
    q: str = Query(..., min_length=2, description="Search keyword (stock name or code)"),
    limit: int = Query(20, ge=1, le=50, description="Maximum number of results"),
):
    """
    Search for stocks by name or code.

    Returns stocks matching the search keyword.
    Requires authentication.
    """
    query = q.lower().strip()

    # Search by code or name
    results = []
    for stock in STOCK_DATABASE:
        # Match by code prefix or name contains
        if stock["code"].startswith(query) or query in stock["name"].lower():
            results.append(StockInfo(**stock))
            if len(results) >= limit:
                break

    return StockSearchResponse(stocks=results, total=len(results))


@router.get(
    "/{stock_code}",
    response_model=StockInfo,
)
async def get_stock_info(
    stock_code: str,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get stock information by code.

    Requires authentication.
    """
    for stock in STOCK_DATABASE:
        if stock["code"] == stock_code:
            return StockInfo(**stock)

    # Return a placeholder for unknown stocks
    return StockInfo(code=stock_code, name=f"종목 {stock_code}", market="UNKNOWN")
