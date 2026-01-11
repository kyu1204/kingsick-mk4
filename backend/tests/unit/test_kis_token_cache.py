"""Tests for KIS Token Cache Service."""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.services.kis_api import KISApiClient, KISApiError
from app.services.kis_token_cache import (
    CachedToken,
    KISTokenCache,
    get_authenticated_kis_client,
)


class TestCachedToken:
    def test_is_expired_when_expired(self) -> None:
        expired_token = CachedToken(
            access_token="test_token",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert expired_token.is_expired() is True

    def test_is_expired_when_valid(self) -> None:
        valid_token = CachedToken(
            access_token="test_token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=10),
        )
        assert valid_token.is_expired() is False

    def test_is_expired_within_buffer(self) -> None:
        near_expiry_token = CachedToken(
            access_token="test_token",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
        assert near_expiry_token.is_expired() is True


class TestKISTokenCache:
    def setup_method(self) -> None:
        KISTokenCache.reset()

    def test_singleton_pattern(self) -> None:
        cache1 = KISTokenCache.get_instance()
        cache2 = KISTokenCache.get_instance()
        assert cache1 is cache2

    def test_set_and_get_token(self) -> None:
        cache = KISTokenCache.get_instance()
        cache.set_token("app_key", "account_no", True, "test_token")

        result = cache.get_token("app_key", "account_no", True)
        assert result == "test_token"

    def test_get_token_returns_none_when_not_cached(self) -> None:
        cache = KISTokenCache.get_instance()

        result = cache.get_token("app_key", "account_no", True)
        assert result is None

    def test_get_token_removes_expired_token(self) -> None:
        cache = KISTokenCache.get_instance()
        cache._tokens[("app_key", "account_no", True)] = CachedToken(
            access_token="expired_token",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )

        result = cache.get_token("app_key", "account_no", True)
        assert result is None
        assert ("app_key", "account_no", True) not in cache._tokens

    def test_cache_key_differentiates_mock_and_real(self) -> None:
        cache = KISTokenCache.get_instance()
        cache.set_token("app_key", "account_no", True, "mock_token")
        cache.set_token("app_key", "account_no", False, "real_token")

        assert cache.get_token("app_key", "account_no", True) == "mock_token"
        assert cache.get_token("app_key", "account_no", False) == "real_token"

    def test_invalidate_token(self) -> None:
        cache = KISTokenCache.get_instance()
        cache.set_token("app_key", "account_no", True, "test_token")

        cache.invalidate("app_key", "account_no", True)

        assert cache.get_token("app_key", "account_no", True) is None

    def test_invalidate_nonexistent_token_does_not_raise(self) -> None:
        cache = KISTokenCache.get_instance()
        cache.invalidate("nonexistent", "account", True)

    def test_reset_clears_all_tokens(self) -> None:
        cache = KISTokenCache.get_instance()
        cache.set_token("app_key1", "account1", True, "token1")
        cache.set_token("app_key2", "account2", False, "token2")

        KISTokenCache.reset()

        assert cache.get_token("app_key1", "account1", True) is None
        assert cache.get_token("app_key2", "account2", False) is None


class TestGetAuthenticatedKISClient:
    def setup_method(self) -> None:
        KISTokenCache.reset()

    @pytest.mark.asyncio
    async def test_returns_client_with_cached_token(self) -> None:
        cache = KISTokenCache.get_instance()
        cache.set_token("app_key", "account_no", True, "cached_token")

        client = await get_authenticated_kis_client(
            app_key="app_key",
            app_secret="app_secret",
            account_no="account_no",
            is_mock=True,
        )

        assert client._access_token == "cached_token"
        await client.close()

    @pytest.mark.asyncio
    async def test_authenticates_and_caches_when_no_cached_token(self) -> None:
        async def mock_authenticate(client_self: KISApiClient) -> None:
            client_self._access_token = "new_token"

        with patch.object(KISApiClient, "authenticate", mock_authenticate):
            client = await get_authenticated_kis_client(
                app_key="app_key",
                app_secret="app_secret",
                account_no="account_no",
                is_mock=True,
            )

            assert client._access_token == "new_token"

            cache = KISTokenCache.get_instance()
            assert cache.get_token("app_key", "account_no", True) == "new_token"
            await client.close()

    @pytest.mark.asyncio
    async def test_raises_kis_api_error_on_auth_failure(self) -> None:
        with patch.object(
            KISApiClient, "authenticate", new_callable=AsyncMock
        ) as mock_auth:
            mock_auth.side_effect = KISApiError("Auth failed")

            with pytest.raises(KISApiError, match="Auth failed"):
                await get_authenticated_kis_client(
                    app_key="app_key",
                    app_secret="app_secret",
                    account_no="account_no",
                    is_mock=True,
                )

            cache = KISTokenCache.get_instance()
            assert cache.get_token("app_key", "account_no", True) is None

    @pytest.mark.asyncio
    async def test_concurrent_requests_only_authenticate_once(self) -> None:
        call_count = 0

        async def mock_authenticate(self: KISApiClient) -> None:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)
            self._access_token = f"token_{call_count}"

        with patch.object(
            KISApiClient, "authenticate", new=mock_authenticate
        ):
            clients = await asyncio.gather(
                get_authenticated_kis_client("app", "secret", "account", True),
                get_authenticated_kis_client("app", "secret", "account", True),
                get_authenticated_kis_client("app", "secret", "account", True),
            )

            assert call_count == 1
            for client in clients:
                assert client._access_token == "token_1"
                await client.close()
