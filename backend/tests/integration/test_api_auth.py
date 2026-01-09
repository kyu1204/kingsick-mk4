"""
Integration tests for authentication API endpoints.
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Invitation, User
from app.services.auth import create_access_token, create_refresh_token, hash_password


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.password_hash = hash_password("testpassword123")
    user.is_admin = False
    user.is_active = True
    return user


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "admin@example.com"
    user.password_hash = hash_password("adminpassword123")
    user.is_admin = True
    user.is_active = True
    return user


@pytest.fixture
def mock_invitation(mock_admin_user):
    """Create a mock invitation."""
    invitation = MagicMock(spec=Invitation)
    invitation.id = uuid.uuid4()
    invitation.code = "valid-invitation-code"
    invitation.created_by = mock_admin_user.id
    invitation.used_by = None
    invitation.used_at = None
    invitation.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    invitation.is_valid = True
    return invitation


class TestRegister:
    """Tests for POST /api/v1/auth/register."""

    @patch("app.api.auth.validate_invitation")
    @patch("app.api.auth.create_user")
    async def test_register_success(
        self, mock_create_user, mock_validate_invitation, client, mock_invitation
    ):
        """Successful registration should return 201."""
        mock_validate_invitation.return_value = mock_invitation
        mock_create_user.return_value = MagicMock(id=uuid.uuid4())

        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepassword123",
                "invitation_code": "valid-invitation-code",
            },
        )

        assert response.status_code == 201
        assert response.json()["message"] == "User created successfully"

    def test_register_invalid_email(self, client):
        """Invalid email should return 422."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",
                "password": "securepassword123",
                "invitation_code": "some-code",
            },
        )

        assert response.status_code == 422

    def test_register_short_password(self, client):
        """Short password should return 422."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "short",
                "invitation_code": "some-code",
            },
        )

        assert response.status_code == 422

    @patch("app.api.auth.validate_invitation")
    async def test_register_invalid_invitation(
        self, mock_validate_invitation, client
    ):
        """Invalid invitation code should return 400."""
        from app.services.auth import AuthenticationError

        mock_validate_invitation.side_effect = AuthenticationError(
            "Invalid invitation code"
        )

        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "securepassword123",
                "invitation_code": "invalid-code",
            },
        )

        assert response.status_code == 400
        assert "Invalid invitation code" in response.json()["detail"]


class TestLogin:
    """Tests for POST /api/v1/auth/login."""

    @patch("app.api.auth.authenticate_user")
    async def test_login_success(self, mock_authenticate, client, mock_user):
        """Successful login should return tokens."""
        mock_authenticate.return_value = mock_user

        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "test@example.com"

    @patch("app.api.auth.authenticate_user")
    async def test_login_invalid_credentials(self, mock_authenticate, client):
        """Invalid credentials should return 401."""
        from app.services.auth import AuthenticationError

        mock_authenticate.side_effect = AuthenticationError("Invalid email or password")

        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]


class TestRefresh:
    """Tests for POST /api/v1/auth/refresh."""

    @patch("app.api.auth.get_user_by_id")
    async def test_refresh_success(self, mock_get_user, client, mock_user):
        """Valid refresh token should return new tokens."""
        mock_get_user.return_value = mock_user
        refresh_token = create_refresh_token(mock_user.id)

        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_invalid_token(self, client):
        """Invalid refresh token should return 401."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )

        assert response.status_code == 401

    @patch("app.api.auth.get_user_by_id")
    async def test_refresh_with_access_token(self, mock_get_user, client, mock_user):
        """Using access token for refresh should return 400."""
        mock_get_user.return_value = mock_user
        access_token = create_access_token(mock_user.id)

        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )

        assert response.status_code == 400
        assert "Invalid token type" in response.json()["detail"]


class TestLogout:
    """Tests for POST /api/v1/auth/logout."""

    def test_logout_success(self, client, mock_user):
        """Logout with valid token should return success."""
        access_token = create_access_token(mock_user.id)

        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"

    def test_logout_without_token(self, client):
        """Logout without token should return 401."""
        response = client.post("/api/v1/auth/logout")

        # HTTPBearer returns 401 when no token is provided
        assert response.status_code == 401


class TestProtectedEndpoint:
    """Tests for protected endpoint access.

    Note: The logout endpoint is stateless and doesn't validate token content.
    It only requires a Bearer token to be present (per HTTPBearer).
    For testing actual token validation, we should test endpoints
    that use get_current_user dependency.
    """

    @patch("app.api.auth.get_user_by_id")
    async def test_access_with_valid_token(self, mock_get_user, client, mock_user):
        """Valid token should allow access."""
        mock_get_user.return_value = mock_user
        access_token = create_access_token(mock_user.id)

        # Logout is a protected endpoint (requires Bearer token)
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200

    def test_logout_accepts_any_bearer_token(self, client):
        """Logout is stateless - accepts any Bearer token format.

        This is by design: JWT logout is client-side token discard.
        The server just acknowledges the request.
        """
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer any.token.here"},
        )

        # Logout is stateless, so it accepts any Bearer token
        assert response.status_code == 200

    def test_access_without_bearer_prefix(self, client):
        """Request without Bearer prefix should fail."""
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "just-a-token"},
        )

        assert response.status_code == 401
