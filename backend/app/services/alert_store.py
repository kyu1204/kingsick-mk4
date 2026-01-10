"""Alert Store service for persisting pending alerts in Redis or in-memory.

Provides temporary storage for alerts awaiting user approval in ALERT mode.
Alerts expire after 5 minutes (TTL = 300 seconds).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from redis.asyncio import Redis

ALERT_TTL_SECONDS = 300  # 5 minutes
ALERT_KEY_PREFIX = "alert:"
LOCK_KEY_PREFIX = "lock:alert:"
LOCK_TTL_SECONDS = 10  # Lock expires after 10 seconds to prevent deadlocks


@dataclass
class AlertData:
    """Data structure for a pending alert."""

    alert_id: str
    user_id: str
    stock_code: str
    stock_name: str
    signal_type: str  # "BUY" or "SELL"
    confidence: float
    current_price: float
    suggested_quantity: int
    reason: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "alert_id": self.alert_id,
            "user_id": self.user_id,
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "signal_type": self.signal_type,
            "confidence": self.confidence,
            "current_price": self.current_price,
            "suggested_quantity": self.suggested_quantity,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AlertData:
        """Create AlertData from dictionary."""
        created_at_str = data.get("created_at")
        if isinstance(created_at_str, str):
            created_at = datetime.fromisoformat(created_at_str)
        else:
            created_at = datetime.now(UTC)

        return cls(
            alert_id=data["alert_id"],
            user_id=data["user_id"],
            stock_code=data["stock_code"],
            stock_name=data["stock_name"],
            signal_type=data["signal_type"],
            confidence=data["confidence"],
            current_price=data["current_price"],
            suggested_quantity=data["suggested_quantity"],
            reason=data["reason"],
            created_at=created_at,
        )


class AlertStore:
    """Store for pending alerts with Redis or in-memory fallback.

    Uses Redis for distributed storage when available.
    Falls back to in-memory dict for testing or when Redis is unavailable.
    """

    def __init__(self, redis_client: Redis | None = None) -> None:
        """Initialize alert store.

        Args:
            redis_client: Async Redis client. If None, uses in-memory storage.
        """
        self._redis = redis_client
        self._memory_store: dict[str, AlertData] = {}

    def _key(self, alert_id: str) -> str:
        """Generate Redis key for alert."""
        return f"{ALERT_KEY_PREFIX}{alert_id}"

    async def save(self, alert: AlertData) -> None:
        """Save alert with TTL.

        Args:
            alert: AlertData to save.
        """
        if self._redis is not None:
            key = self._key(alert.alert_id)
            value = json.dumps(alert.to_dict())
            await self._redis.setex(key, ALERT_TTL_SECONDS, value)
        else:
            self._memory_store[alert.alert_id] = alert

    async def get(self, alert_id: str) -> AlertData | None:
        """Get alert by ID.

        Args:
            alert_id: Alert identifier.

        Returns:
            AlertData if found, None otherwise.
        """
        if self._redis is not None:
            key = self._key(alert_id)
            data = await self._redis.get(key)
            if data is None:
                return None
            return AlertData.from_dict(json.loads(data))
        else:
            return self._memory_store.get(alert_id)

    async def pop(self, alert_id: str) -> AlertData | None:
        """Get and remove alert by ID.

        Note: This method is NOT atomic in Redis without using pop_atomic().
        For concurrent access, use pop_atomic() instead.

        Args:
            alert_id: Alert identifier.

        Returns:
            AlertData if found and removed, None otherwise.
        """
        alert = await self.get(alert_id)
        if alert is not None:
            await self.delete(alert_id)
        return alert

    async def pop_atomic(self, alert_id: str) -> AlertData | None:
        """Atomically get and remove alert with distributed lock.

        Prevents race conditions when multiple requests try to pop the same alert.
        Uses Redis SETNX for distributed locking.

        Args:
            alert_id: Alert identifier.

        Returns:
            AlertData if successfully acquired and removed, None if not found or locked.
        """
        if self._redis is not None:
            lock_key = f"{LOCK_KEY_PREFIX}{alert_id}"
            acquired = await self._redis.set(
                lock_key, "1", nx=True, ex=LOCK_TTL_SECONDS
            )
            if not acquired:
                return None

            try:
                alert = await self.get(alert_id)
                if alert is not None:
                    await self.delete(alert_id)
                return alert
            finally:
                await self._redis.delete(lock_key)
        else:
            return await self.pop(alert_id)

    async def delete(self, alert_id: str) -> bool:
        """Delete alert by ID.

        Args:
            alert_id: Alert identifier.

        Returns:
            True if deleted, False otherwise.
        """
        if self._redis is not None:
            key = self._key(alert_id)
            result = await self._redis.delete(key)
            return result > 0
        else:
            if alert_id in self._memory_store:
                del self._memory_store[alert_id]
                return True
            return False

    async def get_all(self) -> list[AlertData]:
        """Get all pending alerts.

        Returns:
            List of all AlertData objects.
        """
        if self._redis is not None:
            keys = await self._redis.keys(f"{ALERT_KEY_PREFIX}*")
            alerts: list[AlertData] = []
            for key in keys:
                # Handle bytes keys from Redis
                key_str = key.decode() if isinstance(key, bytes) else key
                alert_id = key_str.replace(ALERT_KEY_PREFIX, "")
                alert = await self.get(alert_id)
                if alert is not None:
                    alerts.append(alert)
            return alerts
        else:
            return list(self._memory_store.values())
