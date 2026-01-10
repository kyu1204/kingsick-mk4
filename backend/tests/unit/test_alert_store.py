import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.alert_store import AlertStore, AlertData


class TestAlertData:
    def test_create_alert_data(self):
        alert = AlertData(
            alert_id="test-123",
            user_id="user-456",
            stock_code="005930",
            stock_name="삼성전자",
            signal_type="BUY",
            confidence=0.85,
            current_price=72500.0,
            suggested_quantity=10,
            reason="RSI oversold",
        )
        assert alert.alert_id == "test-123"
        assert alert.signal_type == "BUY"
        assert alert.confidence == 0.85

    def test_alert_data_to_dict(self):
        alert = AlertData(
            alert_id="test-123",
            user_id="user-456",
            stock_code="005930",
            stock_name="삼성전자",
            signal_type="BUY",
            confidence=0.85,
            current_price=72500.0,
            suggested_quantity=10,
            reason="RSI oversold",
        )
        data = alert.to_dict()
        assert data["alert_id"] == "test-123"
        assert data["stock_code"] == "005930"
        assert "created_at" in data

    def test_alert_data_from_dict(self):
        data = {
            "alert_id": "test-123",
            "user_id": "user-456",
            "stock_code": "005930",
            "stock_name": "삼성전자",
            "signal_type": "BUY",
            "confidence": 0.85,
            "current_price": 72500.0,
            "suggested_quantity": 10,
            "reason": "RSI oversold",
            "created_at": datetime.now(UTC).isoformat(),
        }
        alert = AlertData.from_dict(data)
        assert alert.alert_id == "test-123"
        assert alert.signal_type == "BUY"


class TestAlertStore:
    @pytest.fixture
    def mock_redis(self):
        mock = AsyncMock()
        mock.setex = AsyncMock(return_value=True)
        mock.get = AsyncMock(return_value=None)
        mock.delete = AsyncMock(return_value=1)
        mock.keys = AsyncMock(return_value=[])
        return mock

    @pytest.fixture
    def alert_store(self, mock_redis):
        return AlertStore(redis_client=mock_redis)

    @pytest.mark.asyncio
    async def test_save_alert(self, alert_store, mock_redis):
        alert = AlertData(
            alert_id="test-123",
            user_id="user-456",
            stock_code="005930",
            stock_name="삼성전자",
            signal_type="BUY",
            confidence=0.85,
            current_price=72500.0,
            suggested_quantity=10,
            reason="RSI oversold",
        )

        await alert_store.save(alert)

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "alert:test-123"
        assert call_args[0][1] == 300

    @pytest.mark.asyncio
    async def test_get_alert_found(self, alert_store, mock_redis):
        alert_data = {
            "alert_id": "test-123",
            "user_id": "user-456",
            "stock_code": "005930",
            "stock_name": "삼성전자",
            "signal_type": "BUY",
            "confidence": 0.85,
            "current_price": 72500.0,
            "suggested_quantity": 10,
            "reason": "RSI oversold",
            "created_at": datetime.now(UTC).isoformat(),
        }
        mock_redis.get.return_value = json.dumps(alert_data)

        result = await alert_store.get("test-123")

        assert result is not None
        assert result.alert_id == "test-123"
        mock_redis.get.assert_called_once_with("alert:test-123")

    @pytest.mark.asyncio
    async def test_get_alert_not_found(self, alert_store, mock_redis):
        mock_redis.get.return_value = None

        result = await alert_store.get("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_pop_alert(self, alert_store, mock_redis):
        alert_data = {
            "alert_id": "test-123",
            "user_id": "user-456",
            "stock_code": "005930",
            "stock_name": "삼성전자",
            "signal_type": "BUY",
            "confidence": 0.85,
            "current_price": 72500.0,
            "suggested_quantity": 10,
            "reason": "RSI oversold",
            "created_at": datetime.now(UTC).isoformat(),
        }
        mock_redis.get.return_value = json.dumps(alert_data)

        result = await alert_store.pop("test-123")

        assert result is not None
        assert result.alert_id == "test-123"
        mock_redis.delete.assert_called_once_with("alert:test-123")

    @pytest.mark.asyncio
    async def test_pop_alert_not_found(self, alert_store, mock_redis):
        mock_redis.get.return_value = None

        result = await alert_store.pop("nonexistent")

        assert result is None
        mock_redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_alert(self, alert_store, mock_redis):
        result = await alert_store.delete("test-123")

        assert result is True
        mock_redis.delete.assert_called_once_with("alert:test-123")

    @pytest.mark.asyncio
    async def test_get_all_alerts(self, alert_store, mock_redis):
        alert_data = {
            "alert_id": "test-123",
            "user_id": "user-456",
            "stock_code": "005930",
            "stock_name": "삼성전자",
            "signal_type": "BUY",
            "confidence": 0.85,
            "current_price": 72500.0,
            "suggested_quantity": 10,
            "reason": "RSI oversold",
            "created_at": datetime.now(UTC).isoformat(),
        }
        mock_redis.keys.return_value = [b"alert:test-123"]
        mock_redis.get.return_value = json.dumps(alert_data)

        results = await alert_store.get_all()

        assert len(results) == 1
        assert results[0].alert_id == "test-123"


class TestInMemoryAlertStore:
    @pytest.fixture
    def in_memory_store(self):
        return AlertStore(redis_client=None)

    @pytest.mark.asyncio
    async def test_save_and_get(self, in_memory_store):
        alert = AlertData(
            alert_id="test-123",
            user_id="user-456",
            stock_code="005930",
            stock_name="삼성전자",
            signal_type="BUY",
            confidence=0.85,
            current_price=72500.0,
            suggested_quantity=10,
            reason="RSI oversold",
        )

        await in_memory_store.save(alert)
        result = await in_memory_store.get("test-123")

        assert result is not None
        assert result.alert_id == "test-123"

    @pytest.mark.asyncio
    async def test_pop_removes_alert(self, in_memory_store):
        alert = AlertData(
            alert_id="test-123",
            user_id="user-456",
            stock_code="005930",
            stock_name="삼성전자",
            signal_type="BUY",
            confidence=0.85,
            current_price=72500.0,
            suggested_quantity=10,
            reason="RSI oversold",
        )

        await in_memory_store.save(alert)
        result = await in_memory_store.pop("test-123")
        second_get = await in_memory_store.get("test-123")

        assert result is not None
        assert second_get is None

    @pytest.mark.asyncio
    async def test_get_all_returns_list(self, in_memory_store):
        alert1 = AlertData(
            alert_id="test-1",
            user_id="user-456",
            stock_code="005930",
            stock_name="삼성전자",
            signal_type="BUY",
            confidence=0.85,
            current_price=72500.0,
            suggested_quantity=10,
            reason="RSI oversold",
        )
        alert2 = AlertData(
            alert_id="test-2",
            user_id="user-456",
            stock_code="000660",
            stock_name="SK하이닉스",
            signal_type="SELL",
            confidence=0.72,
            current_price=145000.0,
            suggested_quantity=5,
            reason="RSI overbought",
        )

        await in_memory_store.save(alert1)
        await in_memory_store.save(alert2)
        results = await in_memory_store.get_all()

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_pop_atomic_falls_back_to_pop(self, in_memory_store):
        alert = AlertData(
            alert_id="test-123",
            user_id="user-456",
            stock_code="005930",
            stock_name="삼성전자",
            signal_type="BUY",
            confidence=0.85,
            current_price=72500.0,
            suggested_quantity=10,
            reason="RSI oversold",
        )

        await in_memory_store.save(alert)
        result = await in_memory_store.pop_atomic("test-123")
        second_get = await in_memory_store.get("test-123")

        assert result is not None
        assert result.alert_id == "test-123"
        assert second_get is None


class TestPopAtomic:
    @pytest.fixture
    def mock_redis(self):
        mock = AsyncMock()
        mock.set = AsyncMock(return_value=True)
        mock.setex = AsyncMock(return_value=True)
        mock.get = AsyncMock(return_value=None)
        mock.delete = AsyncMock(return_value=1)
        return mock

    @pytest.fixture
    def alert_store(self, mock_redis):
        return AlertStore(redis_client=mock_redis)

    @pytest.mark.asyncio
    async def test_pop_atomic_acquires_lock_and_returns_alert(self, alert_store, mock_redis):
        alert_data = {
            "alert_id": "test-123",
            "user_id": "user-456",
            "stock_code": "005930",
            "stock_name": "삼성전자",
            "signal_type": "BUY",
            "confidence": 0.85,
            "current_price": 72500.0,
            "suggested_quantity": 10,
            "reason": "RSI oversold",
            "created_at": datetime.now(UTC).isoformat(),
        }
        mock_redis.get.return_value = json.dumps(alert_data)
        mock_redis.set.return_value = True

        result = await alert_store.pop_atomic("test-123")

        assert result is not None
        assert result.alert_id == "test-123"
        mock_redis.set.assert_called_once_with("lock:alert:test-123", "1", nx=True, ex=10)
        assert mock_redis.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_pop_atomic_returns_none_when_lock_not_acquired(
        self, alert_store, mock_redis
    ):
        mock_redis.set.return_value = False

        result = await alert_store.pop_atomic("test-123")

        assert result is None
        mock_redis.set.assert_called_once()
        mock_redis.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_pop_atomic_releases_lock_on_exception(self, alert_store, mock_redis):
        mock_redis.set.return_value = True
        mock_redis.get.side_effect = Exception("Redis error")

        with pytest.raises(Exception, match="Redis error"):
            await alert_store.pop_atomic("test-123")

        mock_redis.delete.assert_called_once_with("lock:alert:test-123")

    @pytest.mark.asyncio
    async def test_pop_atomic_returns_none_when_alert_not_found(
        self, alert_store, mock_redis
    ):
        mock_redis.set.return_value = True
        mock_redis.get.return_value = None

        result = await alert_store.pop_atomic("test-123")

        assert result is None
        mock_redis.delete.assert_called_once_with("lock:alert:test-123")
