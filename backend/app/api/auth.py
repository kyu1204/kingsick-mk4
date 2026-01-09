"""
Authentication API router for KingSick.

Provides endpoints for user registration, login, token refresh, and logout.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.auth import (
    AuthenticationError,
    TokenError,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    create_user,
    decode_token,
    get_user_by_id,
    get_user_id_from_token,
    validate_invitation,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


# Request/Response schemas


class RegisterRequest(BaseModel):
    """Request body for user registration."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    invitation_code: str = Field(..., min_length=1)


class RegisterResponse(BaseModel):
    """Response for successful registration."""

    message: str = "User created successfully"


class LoginRequest(BaseModel):
    """Request body for user login."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User information in responses."""

    id: str
    email: str
    is_admin: bool

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Response with access and refresh tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshRequest(BaseModel):
    """Request body for token refresh."""

    refresh_token: str


class RefreshResponse(BaseModel):
    """Response with new tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LogoutResponse(BaseModel):
    """Response for successful logout."""

    message: str = "Logged out successfully"


# Dependencies


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Dependency to get the current authenticated user.

    Raises:
        HTTPException: If token is invalid or user not found.
    """
    try:
        token = credentials.credentials
        payload = decode_token(token)

        # Check token type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        user_id = get_user_id_from_token(token)
        user = await get_user_by_id(db, user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive",
            )

        return user

    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from e


async def get_current_admin_user(
    current_user=Depends(get_current_user),
):
    """
    Dependency to get the current user and verify they are an admin.

    Raises:
        HTTPException: If user is not an admin.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# Endpoints


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Register a new user account.

    Requires a valid invitation code.
    """
    try:
        # Validate invitation
        invitation = await validate_invitation(db, request.invitation_code)

        # Create user
        await create_user(
            db,
            email=request.email,
            password=request.password,
            invitation=invitation,
        )

        return RegisterResponse()

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Authenticate user and return tokens.
    """
    try:
        user = await authenticate_user(db, request.email, request.password)

        access_token = create_access_token(user.id, is_admin=user.is_admin)
        refresh_token = create_refresh_token(user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse(
                id=str(user.id),
                email=user.email,
                is_admin=user.is_admin,
            ),
        )

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from e


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    request: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Refresh access token using refresh token.
    """
    try:
        payload = decode_token(request.refresh_token)

        # Check token type
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type",
            )

        user_id = get_user_id_from_token(request.refresh_token)
        user = await get_user_by_id(db, user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive",
            )

        # Generate new tokens
        access_token = create_access_token(user.id, is_admin=user.is_admin)
        new_refresh_token = create_refresh_token(user.id)

        return RefreshResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
        )

    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from e


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    _: Annotated[HTTPAuthorizationCredentials, Depends(security)],
):
    """
    Logout user.

    Note: JWT tokens are stateless, so this endpoint just returns success.
    The client should discard the tokens.
    For a more secure implementation, consider using a token blacklist.
    """
    return LogoutResponse()
