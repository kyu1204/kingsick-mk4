"""KIS API dependency for FastAPI endpoints."""

from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database import get_db
from app.models import User, UserApiKey
from app.services.encryption import decrypt
from app.services.kis_api import KISApiClient, KISApiError
from app.services.kis_token_cache import get_authenticated_kis_client


async def get_kis_client_for_user(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KISApiClient:
    """Dependency to get authenticated KIS API client for the current user."""
    result = await db.execute(select(UserApiKey).where(UserApiKey.user_id == current_user.id))
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="KIS API credentials not configured. Please add your API key in Settings.",
        )

    try:
        app_key = decrypt(api_key.kis_app_key_encrypted)
        app_secret = decrypt(api_key.kis_app_secret_encrypted)
        account_no = decrypt(api_key.kis_account_no_encrypted)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to decrypt API credentials: {e}",
        )

    try:
        return await get_authenticated_kis_client(
            app_key=app_key,
            app_secret=app_secret,
            account_no=account_no,
            is_mock=api_key.is_paper_trading,
        )
    except KISApiError as e:
        raise HTTPException(status_code=502, detail=str(e))
