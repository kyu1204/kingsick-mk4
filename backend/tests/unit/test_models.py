"""
Unit tests for SQLAlchemy models.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models import Invitation, User, UserApiKey


class TestUserModel:
    """Tests for User model."""

    def test_user_creation(self):
        """User model should have correct attributes."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            is_admin=False,
            is_active=True,
        )
        assert user.email == "test@example.com"
        assert user.password_hash == "hashed_password"
        assert user.is_admin is False
        assert user.is_active is True

    def test_user_admin_flag(self):
        """User can be created as admin."""
        admin = User(
            email="admin@example.com",
            password_hash="hashed_password",
            is_admin=True,
        )
        assert admin.is_admin is True

    def test_user_repr(self):
        """User __repr__ should return readable string."""
        user = User(email="test@example.com", password_hash="hash")
        assert repr(user) == "<User test@example.com>"


class TestInvitationModel:
    """Tests for Invitation model."""

    def test_invitation_creation(self):
        """Invitation model should have correct attributes."""
        user_id = uuid.uuid4()
        expires = datetime.now(timezone.utc) + timedelta(days=7)

        invitation = Invitation(
            code="test-invitation-code",
            created_by=user_id,
            expires_at=expires,
        )
        assert invitation.code == "test-invitation-code"
        assert invitation.created_by == user_id
        assert invitation.used_by is None
        assert invitation.used_at is None

    def test_invitation_is_valid_not_used(self):
        """Unused invitation before expiry should be valid."""
        expires = datetime.now(timezone.utc) + timedelta(days=7)
        invitation = Invitation(
            code="valid-code",
            created_by=uuid.uuid4(),
            expires_at=expires,
        )
        assert invitation.is_valid is True

    def test_invitation_is_invalid_when_used(self):
        """Used invitation should be invalid."""
        expires = datetime.now(timezone.utc) + timedelta(days=7)
        invitation = Invitation(
            code="used-code",
            created_by=uuid.uuid4(),
            expires_at=expires,
            used_at=datetime.now(timezone.utc),
            used_by=uuid.uuid4(),
        )
        assert invitation.is_valid is False

    def test_invitation_is_invalid_when_expired(self):
        """Expired invitation should be invalid."""
        expires = datetime.now(timezone.utc) - timedelta(days=1)
        invitation = Invitation(
            code="expired-code",
            created_by=uuid.uuid4(),
            expires_at=expires,
        )
        assert invitation.is_valid is False

    def test_invitation_repr(self):
        """Invitation __repr__ should show truncated code."""
        invitation = Invitation(
            code="long-invitation-code-12345",
            created_by=uuid.uuid4(),
            expires_at=datetime.now(timezone.utc),
        )
        assert "long-inv" in repr(invitation)


class TestUserApiKeyModel:
    """Tests for UserApiKey model."""

    def test_user_api_key_creation(self):
        """UserApiKey model should have correct attributes."""
        user_id = uuid.uuid4()
        api_key = UserApiKey(
            user_id=user_id,
            kis_app_key_encrypted="encrypted_key",
            kis_app_secret_encrypted="encrypted_secret",
            kis_account_no_encrypted="encrypted_account",
            is_paper_trading=True,
        )
        assert api_key.user_id == user_id
        assert api_key.kis_app_key_encrypted == "encrypted_key"
        assert api_key.is_paper_trading is True

    def test_user_api_key_production_mode(self):
        """UserApiKey can be set to production mode."""
        api_key = UserApiKey(
            user_id=uuid.uuid4(),
            kis_app_key_encrypted="key",
            kis_app_secret_encrypted="secret",
            kis_account_no_encrypted="account",
            is_paper_trading=False,
        )
        assert api_key.is_paper_trading is False

    def test_user_api_key_repr(self):
        """UserApiKey __repr__ should show user_id."""
        user_id = uuid.uuid4()
        api_key = UserApiKey(
            user_id=user_id,
            kis_app_key_encrypted="key",
            kis_app_secret_encrypted="secret",
            kis_account_no_encrypted="account",
        )
        assert str(user_id) in repr(api_key)
