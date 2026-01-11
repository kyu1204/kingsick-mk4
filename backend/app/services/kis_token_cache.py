"""KIS API Token Cache Service.

Provides in-memory caching of KIS OAuth tokens per user to avoid
hitting the "1 request per minute" rate limit on token issuance.

Tokens are cached for 23 hours (KIS tokens expire after 24 hours).
"""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import ClassVar

from app.services.kis_api import KISApiClient


@dataclass
class CachedToken:
    """Cached token data."""

    access_token: str
    expires_at: datetime

    def is_expired(self) -> bool:
        """Check if token is expired or about to expire (1 hour buffer)."""
        return datetime.now(UTC) >= self.expires_at - timedelta(hours=1)


class KISTokenCache:
    """In-memory cache for KIS OAuth tokens.

    Thread-safe singleton that caches tokens per user/credential combination.
    Tokens are cached for 23 hours to avoid expiration issues.
    """

    _instance: ClassVar["KISTokenCache | None"] = None
    _lock: ClassVar[asyncio.Lock] = asyncio.Lock()

    _tokens: dict[tuple[str, str, bool], CachedToken]
    TOKEN_TTL_HOURS: ClassVar[int] = 23

    def __new__(cls) -> "KISTokenCache":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tokens = {}
        return cls._instance

    @classmethod
    def get_instance(cls) -> "KISTokenCache":
        """Get the singleton instance."""
        return cls()

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (for testing)."""
        if cls._instance is not None:
            cls._instance._tokens = {}

    def _cache_key(
        self,
        app_key: str,
        account_no: str,
        is_mock: bool,
    ) -> tuple[str, str, bool]:
        """Generate cache key for token lookup."""
        return (app_key, account_no, is_mock)

    def get_token(
        self,
        app_key: str,
        account_no: str,
        is_mock: bool,
    ) -> str | None:
        """Get cached token if valid.

        Args:
            app_key: KIS API app key
            account_no: Account number
            is_mock: Whether using mock/paper trading

        Returns:
            Access token if cached and valid, None otherwise
        """
        key = self._cache_key(app_key, account_no, is_mock)
        cached = self._tokens.get(key)

        if cached is None:
            return None

        if cached.is_expired():
            del self._tokens[key]
            return None

        return cached.access_token

    def set_token(
        self,
        app_key: str,
        account_no: str,
        is_mock: bool,
        access_token: str,
    ) -> None:
        """Cache a new token.

        Args:
            app_key: KIS API app key
            account_no: Account number
            is_mock: Whether using mock/paper trading
            access_token: The OAuth access token to cache
        """
        key = self._cache_key(app_key, account_no, is_mock)
        expires_at = datetime.now(UTC) + timedelta(hours=self.TOKEN_TTL_HOURS)
        self._tokens[key] = CachedToken(access_token=access_token, expires_at=expires_at)

    def invalidate(
        self,
        app_key: str,
        account_no: str,
        is_mock: bool,
    ) -> None:
        """Invalidate a cached token.

        Args:
            app_key: KIS API app key
            account_no: Account number
            is_mock: Whether using mock/paper trading
        """
        key = self._cache_key(app_key, account_no, is_mock)
        self._tokens.pop(key, None)


async def get_authenticated_kis_client(
    app_key: str,
    app_secret: str,
    account_no: str,
    is_mock: bool = True,
) -> KISApiClient:
    """Get an authenticated KIS API client with cached token.

    This function handles token caching automatically:
    1. Check if a valid cached token exists
    2. If yes, create client and set the token directly
    3. If no, authenticate and cache the new token

    Args:
        app_key: KIS API app key
        app_secret: KIS API app secret
        account_no: Account number
        is_mock: Whether using mock/paper trading

    Returns:
        Authenticated KISApiClient ready for API calls

    Raises:
        KISApiError: If authentication fails
    """
    cache = KISTokenCache.get_instance()
    client = KISApiClient(
        app_key=app_key,
        app_secret=app_secret,
        account_no=account_no,
        is_mock=is_mock,
    )

    cached_token = cache.get_token(app_key, account_no, is_mock)
    if cached_token:
        client._access_token = cached_token
        return client

    async with KISTokenCache._lock:
        cached_token = cache.get_token(app_key, account_no, is_mock)
        if cached_token:
            client._access_token = cached_token
            return client

        await client.authenticate()
        if client._access_token:
            cache.set_token(app_key, account_no, is_mock, client._access_token)
        return client
