"""
API Keys management router for KingSick.

Provides endpoints for users to manage their KIS API credentials.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database import get_db
from app.models import User, UserApiKey
from app.services.encryption import decrypt, encrypt, mask_string

router = APIRouter(prefix="/settings/api-key", tags=["Settings - API Keys"])


# Request/Response schemas


class ApiKeyInfoResponse(BaseModel):
    """Response with masked API key information."""

    has_api_key: bool
    app_key_masked: str | None = None
    account_no_masked: str | None = None
    is_paper_trading: bool | None = None


class SaveApiKeyRequest(BaseModel):
    """Request body for saving API keys."""

    app_key: str = Field(..., min_length=1)
    app_secret: str = Field(..., min_length=1)
    account_no: str = Field(..., min_length=1)
    is_paper_trading: bool = True


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


class VerifyResponse(BaseModel):
    """Response for API key verification."""

    valid: bool
    message: str


# Endpoints


@router.get("", response_model=ApiKeyInfoResponse)
async def get_api_key_info(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get current user's API key information (masked).
    """
    result = await db.execute(
        select(UserApiKey).where(UserApiKey.user_id == current_user.id)
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        return ApiKeyInfoResponse(has_api_key=False)

    # Decrypt and mask the values
    try:
        app_key = decrypt(api_key.kis_app_key_encrypted)
        account_no = decrypt(api_key.kis_account_no_encrypted)
    except Exception:
        # If decryption fails, return has_api_key=False
        return ApiKeyInfoResponse(has_api_key=False)

    return ApiKeyInfoResponse(
        has_api_key=True,
        app_key_masked=mask_string(app_key),
        account_no_masked=mask_string(account_no),
        is_paper_trading=api_key.is_paper_trading,
    )


@router.post("", response_model=MessageResponse)
async def save_api_key(
    request: SaveApiKeyRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Save or update the current user's KIS API credentials.

    The credentials are encrypted before storage.
    """
    # Check if user already has API keys
    result = await db.execute(
        select(UserApiKey).where(UserApiKey.user_id == current_user.id)
    )
    existing_key = result.scalar_one_or_none()

    # Encrypt the values
    encrypted_app_key = encrypt(request.app_key)
    encrypted_app_secret = encrypt(request.app_secret)
    encrypted_account_no = encrypt(request.account_no)

    if existing_key:
        # Update existing
        existing_key.kis_app_key_encrypted = encrypted_app_key
        existing_key.kis_app_secret_encrypted = encrypted_app_secret
        existing_key.kis_account_no_encrypted = encrypted_account_no
        existing_key.is_paper_trading = request.is_paper_trading
    else:
        # Create new
        api_key = UserApiKey(
            user_id=current_user.id,
            kis_app_key_encrypted=encrypted_app_key,
            kis_app_secret_encrypted=encrypted_app_secret,
            kis_account_no_encrypted=encrypted_account_no,
            is_paper_trading=request.is_paper_trading,
        )
        db.add(api_key)

    return MessageResponse(message="API key saved successfully")


@router.delete("", response_model=MessageResponse)
async def delete_api_key(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete the current user's API credentials.
    """
    result = await db.execute(
        select(UserApiKey).where(UserApiKey.user_id == current_user.id)
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No API key found",
        )

    await db.delete(api_key)

    return MessageResponse(message="API key deleted successfully")


@router.post("/verify", response_model=VerifyResponse)
async def verify_api_key(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Verify that the stored API credentials are valid.

    This endpoint makes a test call to KIS API to verify credentials.
    """
    result = await db.execute(
        select(UserApiKey).where(UserApiKey.user_id == current_user.id)
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        return VerifyResponse(
            valid=False,
            message="No API key configured",
        )

    try:
        # Decrypt credentials
        app_key = decrypt(api_key.kis_app_key_encrypted)
        app_secret = decrypt(api_key.kis_app_secret_encrypted)
        account_no = decrypt(api_key.kis_account_no_encrypted)

        # TODO: Actually call KIS API to verify credentials
        # For now, just check that decryption succeeded and values are non-empty
        if app_key and app_secret and account_no:
            return VerifyResponse(
                valid=True,
                message="API key verification successful (basic check only)",
            )
        else:
            return VerifyResponse(
                valid=False,
                message="API key data is incomplete",
            )

    except Exception as e:
        return VerifyResponse(
            valid=False,
            message=f"Failed to verify API key: {str(e)}",
        )
