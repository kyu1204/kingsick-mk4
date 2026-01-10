"""
Integration tests for Telegram API endpoints.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import User
from app.models.telegram_link import TelegramLinkToken
from app.services.auth import create_access_token


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Create a mock user without Telegram linked."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.is_admin = False
    user.is_active = True
    user.telegram_chat_id = None
    user.telegram_linked_at = None
    return user


@pytest.fixture
def mock_linked_user():
    """Create a mock user with Telegram linked."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "linked@example.com"
    user.is_admin = False
    user.is_active = True
    user.telegram_chat_id = "123456789"
    user.telegram_linked_at = datetime.now(UTC)
    return user


@pytest.fixture
def auth_headers(mock_user):
    """Create authorization headers with valid token."""
    access_token = create_access_token(mock_user.id)
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def linked_auth_headers(mock_linked_user):
    """Create authorization headers for linked user."""
    access_token = create_access_token(mock_linked_user.id)
    return {"Authorization": f"Bearer {access_token}"}


class TestCreateLinkToken:
    """Tests for POST /api/v1/telegram/link."""

    def test_create_link_token_unauthorized(self, client):
        """Create link token without auth should return 401."""
        response = client.post("/api/v1/telegram/link")
        assert response.status_code == 401


class TestGetLinkStatus:
    """Tests for GET /api/v1/telegram/status."""

    def test_get_status_unauthorized(self, client):
        """Get status without auth should return 401."""
        response = client.get("/api/v1/telegram/status")
        assert response.status_code == 401


class TestUnlinkTelegram:
    """Tests for DELETE /api/v1/telegram/link."""

    def test_unlink_unauthorized(self, client):
        """Unlink without auth should return 401."""
        response = client.delete("/api/v1/telegram/link")
        assert response.status_code == 401


class TestTelegramWebhook:
    """Tests for POST /api/v1/telegram/webhook."""

    def test_webhook_invalid_secret(self, client):
        """Webhook with invalid secret should return 401."""
        with patch("app.api.telegram.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.telegram_webhook_secret = "correct-secret"
            mock_get_settings.return_value = mock_settings

            response = client.post(
                "/api/v1/telegram/webhook",
                json={"message": {}},
                headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
            )

            assert response.status_code == 401

    def test_webhook_empty_update(self, client):
        """Webhook with empty update should return ok."""
        with patch("app.api.telegram.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.telegram_webhook_secret = None
            mock_get_settings.return_value = mock_settings

            response = client.post(
                "/api/v1/telegram/webhook",
                json={},
            )

            assert response.status_code == 200
            assert response.json()["ok"] is True

    def test_webhook_start_command_without_token(self, client):
        """Webhook bare /start should send instruction."""
        with (
            patch("app.api.telegram.get_settings") as mock_get_settings,
            patch("app.api.telegram.get_telegram_service") as mock_get_service,
        ):
            mock_settings = MagicMock()
            mock_settings.telegram_webhook_secret = None
            mock_get_settings.return_value = mock_settings

            mock_service = MagicMock()
            mock_service.is_enabled = True
            mock_service.send_error_message = AsyncMock()
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/v1/telegram/webhook",
                json={
                    "message": {
                        "text": "/start",
                        "chat": {"id": 123456789},
                    }
                },
            )

            assert response.status_code == 200
            mock_service.send_error_message.assert_called_once()


class TestHelperFunctions:
    """Tests for helper functions in telegram module."""

    @pytest.mark.anyio
    async def test_get_or_create_link_token(self):
        """get_or_create_link_token should create new token."""
        from app.api.telegram import get_or_create_link_token

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: []))
        )
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        user_id = str(uuid.uuid4())

        with patch.object(TelegramLinkToken, "create_token") as mock_create:
            mock_token = MagicMock()
            mock_create.return_value = mock_token

            result = await get_or_create_link_token(mock_db, user_id)

            assert result == mock_token
            mock_db.add.assert_called_once_with(mock_token)
            mock_db.commit.assert_called_once()

    @pytest.mark.anyio
    async def test_validate_and_use_token_valid(self):
        """validate_and_use_token should mark token as used."""
        from app.api.telegram import validate_and_use_token

        mock_token = MagicMock()
        mock_token.is_valid = True
        mock_token.used = False

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_token
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        result = await validate_and_use_token(mock_db, "valid-token")

        assert result == mock_token
        assert mock_token.used is True
        mock_db.commit.assert_called_once()

    @pytest.mark.anyio
    async def test_validate_and_use_token_invalid(self):
        """validate_and_use_token should return None for invalid token."""
        from app.api.telegram import validate_and_use_token

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await validate_and_use_token(mock_db, "invalid-token")

        assert result is None

    @pytest.mark.anyio
    async def test_validate_and_use_token_expired(self):
        """validate_and_use_token should return None for expired token."""
        from app.api.telegram import validate_and_use_token

        mock_token = MagicMock()
        mock_token.is_valid = False  # Expired or used

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_token
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await validate_and_use_token(mock_db, "expired-token")

        assert result is None

    @pytest.mark.anyio
    async def test_link_user_telegram(self):
        """link_user_telegram should update user's telegram_chat_id."""
        from app.api.telegram import link_user_telegram

        mock_user = MagicMock(spec=User)
        mock_user.telegram_chat_id = None
        mock_user.telegram_linked_at = None

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        user_id = str(uuid.uuid4())
        chat_id = "123456789"

        result = await link_user_telegram(mock_db, user_id, chat_id)

        assert result.telegram_chat_id == chat_id
        assert result.telegram_linked_at is not None
        mock_db.commit.assert_called_once()

    @pytest.mark.anyio
    async def test_unlink_user_telegram(self):
        """unlink_user_telegram should clear user's telegram_chat_id."""
        from app.api.telegram import unlink_user_telegram

        mock_user = MagicMock(spec=User)
        mock_user.telegram_chat_id = "123456789"
        mock_user.telegram_linked_at = datetime.now(UTC)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        user_id = str(uuid.uuid4())

        result = await unlink_user_telegram(mock_db, user_id)

        assert result.telegram_chat_id is None
        assert result.telegram_linked_at is None
        mock_db.commit.assert_called_once()

    @pytest.mark.anyio
    async def test_get_user_by_chat_id(self):
        """get_user_by_chat_id should find user by telegram_chat_id."""
        from app.api.telegram import get_user_by_chat_id

        mock_user = MagicMock(spec=User)
        mock_user.telegram_chat_id = "123456789"

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await get_user_by_chat_id(mock_db, "123456789")

        assert result == mock_user

    @pytest.mark.anyio
    async def test_get_user_by_chat_id_not_found(self):
        """get_user_by_chat_id should return None if not found."""
        from app.api.telegram import get_user_by_chat_id

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await get_user_by_chat_id(mock_db, "999999999")

        assert result is None


class TestTelegramLinkTokenModel:
    """Tests for TelegramLinkToken model."""

    def test_create_token_generates_valid_token(self):
        """create_token should generate a valid token with expiry."""
        user_id = uuid.uuid4()
        token = TelegramLinkToken.create_token(user_id)

        assert token.user_id == user_id
        assert len(token.token) > 0
        assert token.used is False
        assert token.expires_at > datetime.now(UTC)

    def test_is_valid_returns_true_for_valid_token(self):
        """is_valid should return True for unused, non-expired token."""
        user_id = uuid.uuid4()
        token = TelegramLinkToken.create_token(user_id)

        assert token.is_valid is True

    def test_is_valid_returns_false_for_used_token(self):
        """is_valid should return False for used token."""
        user_id = uuid.uuid4()
        token = TelegramLinkToken.create_token(user_id)
        token.used = True

        assert token.is_valid is False

    def test_is_valid_returns_false_for_expired_token(self):
        """is_valid should return False for expired token."""
        user_id = uuid.uuid4()
        token = TelegramLinkToken.create_token(user_id)
        token.expires_at = datetime.now(UTC) - timedelta(minutes=1)

        assert token.is_valid is False
