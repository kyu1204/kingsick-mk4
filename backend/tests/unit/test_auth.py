"""
Unit tests for authentication service.
"""

import uuid
from datetime import timedelta

import pytest

from app.services.auth import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_invitation_code,
    get_user_id_from_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password_returns_hash(self):
        """hash_password should return a bcrypt hash."""
        password = "mysecretpassword"
        hashed = hash_password(password)
        assert hashed != password
        assert hashed.startswith("$2b$")

    def test_verify_password_correct(self):
        """verify_password should return True for correct password."""
        password = "mysecretpassword"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """verify_password should return False for incorrect password."""
        hashed = hash_password("correctpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_different_passwords_have_different_hashes(self):
        """Different passwords should produce different hashes."""
        hash1 = hash_password("password1")
        hash2 = hash_password("password2")
        assert hash1 != hash2

    def test_same_password_has_different_hash_each_time(self):
        """Same password should have different hash each time (salt)."""
        password = "samepassword"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWT:
    """Tests for JWT token functions."""

    def test_create_access_token(self):
        """create_access_token should return a valid JWT."""
        user_id = uuid.uuid4()
        token = create_access_token(user_id)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_admin(self):
        """create_access_token should include is_admin claim."""
        user_id = uuid.uuid4()
        token = create_access_token(user_id, is_admin=True)
        payload = decode_token(token)
        assert payload["is_admin"] is True

    def test_create_refresh_token(self):
        """create_refresh_token should return a valid JWT."""
        user_id = uuid.uuid4()
        token = create_refresh_token(user_id)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_token_valid(self):
        """decode_token should return payload for valid token."""
        user_id = uuid.uuid4()
        token = create_access_token(user_id)
        payload = decode_token(token)
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"

    def test_decode_token_invalid(self):
        """decode_token should raise TokenError for invalid token."""
        with pytest.raises(TokenError, match="Invalid token"):
            decode_token("invalid.token.here")

    def test_decode_token_expired(self):
        """decode_token should raise TokenError for expired token."""
        user_id = uuid.uuid4()
        # Create token that expires immediately
        token = create_access_token(user_id, expires_delta=timedelta(seconds=-1))
        with pytest.raises(TokenError, match="Invalid token"):
            decode_token(token)

    def test_get_user_id_from_token(self):
        """get_user_id_from_token should extract user ID."""
        user_id = uuid.uuid4()
        token = create_access_token(user_id)
        extracted_id = get_user_id_from_token(token)
        assert extracted_id == user_id

    def test_get_user_id_from_invalid_token(self):
        """get_user_id_from_token should raise TokenError for invalid token."""
        with pytest.raises(TokenError):
            get_user_id_from_token("invalid.token")

    def test_access_token_contains_type(self):
        """Access token should have type 'access'."""
        token = create_access_token(uuid.uuid4())
        payload = decode_token(token)
        assert payload["type"] == "access"

    def test_refresh_token_contains_type(self):
        """Refresh token should have type 'refresh'."""
        token = create_refresh_token(uuid.uuid4())
        payload = decode_token(token)
        assert payload["type"] == "refresh"


class TestInvitationCode:
    """Tests for invitation code generation."""

    def test_generate_invitation_code_length(self):
        """generate_invitation_code should return 32-char hex string."""
        code = generate_invitation_code()
        assert len(code) == 32
        # Should be valid hex
        int(code, 16)

    def test_generate_invitation_code_unique(self):
        """generate_invitation_code should produce unique codes."""
        codes = {generate_invitation_code() for _ in range(100)}
        assert len(codes) == 100
