import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.auth import get_current_user
from app.main import app
from app.models import User
from app.services.auth import create_access_token
from app.services.stock_scanner import ScanResult, ScanType


@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.is_admin = False
    user.is_active = True
    return user


@pytest.fixture
def auth_headers(mock_user):
    access_token = create_access_token(mock_user.id)
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def mock_scan_results():
    return [
        ScanResult(
            stock_code="005930",
            stock_name="삼성전자",
            signal="BUY",
            confidence=0.85,
            current_price=72500.0,
            rsi=25.0,
            volume_spike=True,
            reasoning=["RSI 과매도", "거래량 급증"],
        ),
        ScanResult(
            stock_code="000660",
            stock_name="SK하이닉스",
            signal="BUY",
            confidence=0.72,
            current_price=145000.0,
            rsi=28.0,
            volume_spike=False,
            reasoning=["RSI 과매도"],
        ),
    ]


@pytest.fixture
def mock_scanner(mock_scan_results):
    scanner = MagicMock()
    scanner.scan_market = AsyncMock(return_value=mock_scan_results)
    return scanner


class TestScanMarket:
    @pytest.mark.asyncio
    async def test_scan_market_buy_success(self, mock_user, auth_headers, mock_scanner):
        app.dependency_overrides[get_current_user] = lambda: mock_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            with pytest.MonkeyPatch.context() as mp:
                mp.setattr("app.api.scanner.get_scanner", lambda: mock_scanner)
                response = await client.get(
                    "/api/v1/scan?scan_type=BUY&min_confidence=0.5&limit=10",
                    headers=auth_headers,
                )

        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert data["total"] == 2
        assert data["scan_type"] == "BUY"
        assert data["min_confidence"] == 0.5
        assert data["results"][0]["stock_code"] == "005930"
        assert data["results"][0]["confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_scan_market_sell_success(self, mock_user, auth_headers):
        sell_results = [
            ScanResult(
                stock_code="035720",
                stock_name="카카오",
                signal="SELL",
                confidence=0.78,
                current_price=45000.0,
                rsi=75.0,
                volume_spike=True,
                reasoning=["RSI 과매수"],
            ),
        ]
        mock_scanner = MagicMock()
        mock_scanner.scan_market = AsyncMock(return_value=sell_results)

        app.dependency_overrides[get_current_user] = lambda: mock_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            with pytest.MonkeyPatch.context() as mp:
                mp.setattr("app.api.scanner.get_scanner", lambda: mock_scanner)
                response = await client.get(
                    "/api/v1/scan?scan_type=SELL",
                    headers=auth_headers,
                )

        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["scan_type"] == "SELL"
        assert data["results"][0]["signal"] == "SELL"

    @pytest.mark.asyncio
    async def test_scan_market_unauthorized(self):
        app.dependency_overrides.clear()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/scan")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_scan_market_with_custom_params(self, mock_user, auth_headers, mock_scanner):
        app.dependency_overrides[get_current_user] = lambda: mock_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            with pytest.MonkeyPatch.context() as mp:
                mp.setattr("app.api.scanner.get_scanner", lambda: mock_scanner)
                response = await client.get(
                    "/api/v1/scan?scan_type=BUY&min_confidence=0.7&limit=5",
                    headers=auth_headers,
                )

        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["min_confidence"] == 0.7

        mock_scanner.scan_market.assert_called_once()
        call_kwargs = mock_scanner.scan_market.call_args.kwargs
        assert call_kwargs["scan_type"] == ScanType.BUY
        assert call_kwargs["min_confidence"] == 0.7
        assert call_kwargs["limit"] == 5

    @pytest.mark.asyncio
    async def test_scan_market_invalid_confidence(self, mock_user, auth_headers):
        app.dependency_overrides[get_current_user] = lambda: mock_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/v1/scan?min_confidence=1.5",
                headers=auth_headers,
            )

        app.dependency_overrides.clear()
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_scan_market_invalid_limit(self, mock_user, auth_headers):
        app.dependency_overrides[get_current_user] = lambda: mock_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/v1/scan?limit=100",
                headers=auth_headers,
            )

        app.dependency_overrides.clear()
        assert response.status_code == 422


class TestGetStockUniverse:
    @pytest.mark.asyncio
    async def test_get_universe_success(self, mock_user, auth_headers):
        app.dependency_overrides[get_current_user] = lambda: mock_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/scan/universe", headers=auth_headers)

        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert "kospi" in data
        assert "kosdaq" in data
        assert "total" in data
        assert len(data["kospi"]) > 0
        assert len(data["kosdaq"]) > 0
        assert data["total"] == len(data["kospi"]) + len(data["kosdaq"])

        first_kospi = data["kospi"][0]
        assert "code" in first_kospi
        assert "name" in first_kospi

    @pytest.mark.asyncio
    async def test_get_universe_unauthorized(self):
        app.dependency_overrides.clear()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/scan/universe")
        assert response.status_code == 401
