"""
Users API router for KingSick.

Provides endpoints for user profile management.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth import get_current_user
from app.database import get_db
from app.models import User
from app.models.user import UserApiKey
from app.services.auth import hash_password, verify_password

router = APIRouter(prefix="/users", tags=["Users"])


# Request/Response schemas


class UserProfileResponse(BaseModel):
    """Response with user profile information."""

    id: str
    email: str
    is_admin: bool
    is_active: bool
    has_api_key: bool
    created_at: str

    class Config:
        from_attributes = True


class UpdateProfileRequest(BaseModel):
    """Request body for profile update."""

    email: EmailStr | None = None


class ChangePasswordRequest(BaseModel):
    """Request body for password change."""

    current_password: str
    new_password: str


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


# Endpoints


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get the current user's profile.
    """
    # Check if user has API key using separate query to avoid lazy loading issues
    result = await db.execute(
        select(UserApiKey).where(UserApiKey.user_id == current_user.id)
    )
    has_api_key = result.scalar_one_or_none() is not None

    return UserProfileResponse(
        id=str(current_user.id),
        email=current_user.email,
        is_admin=current_user.is_admin,
        is_active=current_user.is_active,
        has_api_key=has_api_key,
        created_at=current_user.created_at.isoformat(),
    )


@router.put("/me", response_model=UserProfileResponse)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update the current user's profile.
    """
    if request.email and request.email != current_user.email:
        # Check if email is already taken
        result = await db.execute(select(User).where(User.email == request.email))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use",
            )
        current_user.email = request.email

    return UserProfileResponse(
        id=str(current_user.id),
        email=current_user.email,
        is_admin=current_user.is_admin,
        is_active=current_user.is_active,
        has_api_key=current_user.api_key is not None,
        created_at=current_user.created_at.isoformat(),
    )


@router.put("/me/password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Change the current user's password.
    """
    # Verify current password
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Validate new password length
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters",
        )

    # Update password
    current_user.password_hash = hash_password(request.new_password)

    return MessageResponse(message="Password updated successfully")
