from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database import get_db
from app.models import User
from app.services.slack_service import (
    InvalidWebhookUrlError,
    SlackSendError,
    get_slack_service,
)

router = APIRouter(prefix="/settings/slack", tags=["Settings - Slack"])


class SlackStatusResponse(BaseModel):
    configured: bool
    webhook_url_masked: str | None = None


class SlackWebhookRequest(BaseModel):
    webhook_url: str = Field(..., min_length=1)


class SlackMessageResponse(BaseModel):
    success: bool
    message: str


@router.get("", response_model=SlackStatusResponse)
async def get_slack_status(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SlackStatusResponse:
    await db.refresh(current_user)

    if not current_user.slack_webhook_url:
        return SlackStatusResponse(configured=False)

    slack_service = get_slack_service()
    masked_url = slack_service.mask_webhook_url(current_user.slack_webhook_url)

    return SlackStatusResponse(configured=True, webhook_url_masked=masked_url)


@router.post("", response_model=SlackMessageResponse)
async def save_slack_webhook(
    request: SlackWebhookRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SlackMessageResponse:
    slack_service = get_slack_service()

    if not slack_service.validate_webhook_url(request.webhook_url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Slack webhook URL format",
        )

    current_user.slack_webhook_url = request.webhook_url
    await db.commit()

    return SlackMessageResponse(success=True, message="Slack webhook configured successfully")


@router.post("/test", response_model=SlackMessageResponse)
async def test_slack_webhook(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SlackMessageResponse:
    await db.refresh(current_user)

    if not current_user.slack_webhook_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Slack webhook is not configured",
        )

    slack_service = get_slack_service()

    try:
        success = await slack_service.send_test_message(current_user.slack_webhook_url)
        if success:
            return SlackMessageResponse(success=True, message="Test message sent successfully")
        return SlackMessageResponse(success=False, message="Failed to send test message")
    except InvalidWebhookUrlError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except SlackSendError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        ) from e


@router.delete("", response_model=SlackMessageResponse)
async def delete_slack_webhook(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SlackMessageResponse:
    await db.refresh(current_user)

    if not current_user.slack_webhook_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slack webhook is not configured",
        )

    current_user.slack_webhook_url = None
    await db.commit()

    return SlackMessageResponse(success=True, message="Slack webhook deleted successfully")
