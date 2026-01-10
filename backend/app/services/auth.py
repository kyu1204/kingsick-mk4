"""
Authentication service for KingSick.

Provides JWT token management and password hashing utilities.
"""

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Invitation, User


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    pass


class TokenError(Exception):
    """Raised when token validation fails."""

    pass


# Password utilities


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: The plain text password.

    Returns:
        str: The hashed password.
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: The plain text password to verify.
        hashed_password: The hashed password to compare against.

    Returns:
        bool: True if the password matches, False otherwise.
    """
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)


# JWT utilities


def create_access_token(
    user_id: uuid.UUID,
    is_admin: bool = False,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: The user's UUID.
        is_admin: Whether the user is an admin.
        expires_delta: Optional custom expiration time.

    Returns:
        str: The encoded JWT token.
    """
    settings = get_settings()

    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

    expire = datetime.now(UTC) + expires_delta

    to_encode: dict[str, Any] = {
        "sub": str(user_id),
        "is_admin": is_admin,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(UTC),
    }

    return jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(
    user_id: uuid.UUID,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT refresh token.

    Args:
        user_id: The user's UUID.
        expires_delta: Optional custom expiration time.

    Returns:
        str: The encoded JWT token.
    """
    settings = get_settings()

    if expires_delta is None:
        expires_delta = timedelta(days=settings.refresh_token_expire_days)

    expire = datetime.now(UTC) + expires_delta

    to_encode: dict[str, Any] = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(UTC),
    }

    return jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT token to decode.

    Returns:
        dict: The decoded token payload.

    Raises:
        TokenError: If the token is invalid or expired.
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as e:
        raise TokenError(f"Invalid token: {e}") from e


def get_user_id_from_token(token: str) -> uuid.UUID:
    """
    Extract user ID from a JWT token.

    Args:
        token: The JWT token.

    Returns:
        UUID: The user's UUID.

    Raises:
        TokenError: If the token is invalid or doesn't contain user ID.
    """
    payload = decode_token(token)
    user_id_str = payload.get("sub")

    if not user_id_str:
        raise TokenError("Token missing user ID")

    try:
        return uuid.UUID(user_id_str)
    except ValueError as e:
        raise TokenError(f"Invalid user ID in token: {e}") from e


# Invitation utilities


def generate_invitation_code() -> str:
    """
    Generate a secure random invitation code.

    Returns:
        str: A 32-character hex string.
    """
    return secrets.token_hex(16)


# Database operations


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """
    Get a user by their email address.

    Args:
        db: The database session.
        email: The user's email.

    Returns:
        User or None: The user if found, None otherwise.
    """
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    """
    Get a user by their ID.

    Args:
        db: The database session.
        user_id: The user's UUID.

    Returns:
        User or None: The user if found, None otherwise.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> User:
    """
    Authenticate a user with email and password.

    Args:
        db: The database session.
        email: The user's email.
        password: The plain text password.

    Returns:
        User: The authenticated user.

    Raises:
        AuthenticationError: If authentication fails.
    """
    user = await get_user_by_email(db, email)

    if not user:
        raise AuthenticationError("Invalid email or password")

    if not verify_password(password, user.password_hash):
        raise AuthenticationError("Invalid email or password")

    if not user.is_active:
        raise AuthenticationError("User account is inactive")

    return user


async def validate_invitation(db: AsyncSession, code: str) -> Invitation:
    """
    Validate an invitation code.

    Args:
        db: The database session.
        code: The invitation code.

    Returns:
        Invitation: The valid invitation.

    Raises:
        AuthenticationError: If the invitation is invalid, used, or expired.
    """
    result = await db.execute(select(Invitation).where(Invitation.code == code))
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise AuthenticationError("Invalid invitation code")

    if not invitation.is_valid:
        if invitation.used_at:
            raise AuthenticationError("Invitation has already been used")
        raise AuthenticationError("Invitation has expired")

    return invitation


async def create_user(
    db: AsyncSession,
    email: str,
    password: str,
    invitation: Invitation,
) -> User:
    """
    Create a new user account.

    Args:
        db: The database session.
        email: The user's email.
        password: The plain text password.
        invitation: The invitation used for registration.

    Returns:
        User: The created user.

    Raises:
        AuthenticationError: If the email is already registered.
    """
    # Check if email already exists
    existing_user = await get_user_by_email(db, email)
    if existing_user:
        raise AuthenticationError("Email already registered")

    # Create user
    user = User(
        email=email,
        password_hash=hash_password(password),
        is_admin=False,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    # Mark invitation as used
    invitation.used_by = user.id
    invitation.used_at = datetime.now(UTC)

    return user
