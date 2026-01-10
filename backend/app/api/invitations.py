"""
Invitations API router for KingSick.

Provides endpoints for admin users to manage invitation links.
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_admin_user
from app.config import get_settings
from app.database import get_db
from app.models import Invitation, User
from app.services.auth import generate_invitation_code

router = APIRouter(prefix="/invitations", tags=["Invitations"])


# Request/Response schemas


class CreateInvitationRequest(BaseModel):
    """Request body for creating an invitation."""

    expires_in_days: int = Field(default=7, ge=1, le=30)


class InvitationResponse(BaseModel):
    """Response with invitation details."""

    id: str
    code: str
    invitation_url: str
    expires_at: str
    used: bool
    created_at: str

    class Config:
        from_attributes = True


class InvitationListResponse(BaseModel):
    """Response with list of invitations."""

    invitations: list[InvitationResponse]


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


def _build_invitation_url(code: str) -> str:
    """Build the full invitation URL."""
    settings = get_settings()
    # Use the first CORS origin as the frontend URL
    frontend_url = settings.cors_origins[0] if settings.cors_origins else "http://localhost:3000"
    return f"{frontend_url}/register?code={code}"


# Endpoints


@router.post(
    "",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invitation(
    request: CreateInvitationRequest,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new invitation link.

    Only admin users can create invitations.
    """
    code = generate_invitation_code()
    expires_at = datetime.now(UTC) + timedelta(days=request.expires_in_days)

    invitation = Invitation(
        code=code,
        created_by=current_user.id,
        expires_at=expires_at,
    )
    db.add(invitation)
    await db.flush()

    return InvitationResponse(
        id=str(invitation.id),
        code=invitation.code,
        invitation_url=_build_invitation_url(invitation.code),
        expires_at=invitation.expires_at.isoformat(),
        used=invitation.used_at is not None,
        created_at=invitation.created_at.isoformat(),
    )


@router.get("", response_model=InvitationListResponse)
async def list_invitations(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    List all invitations created by the current admin.
    """
    result = await db.execute(
        select(Invitation)
        .where(Invitation.created_by == current_user.id)
        .order_by(Invitation.created_at.desc())
    )
    invitations = result.scalars().all()

    return InvitationListResponse(
        invitations=[
            InvitationResponse(
                id=str(inv.id),
                code=inv.code,
                invitation_url=_build_invitation_url(inv.code),
                expires_at=inv.expires_at.isoformat(),
                used=inv.used_at is not None,
                created_at=inv.created_at.isoformat(),
            )
            for inv in invitations
        ]
    )


@router.delete("/{invitation_id}", response_model=MessageResponse)
async def delete_invitation(
    invitation_id: str,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete an invitation.

    Only the admin who created the invitation can delete it.
    """
    import uuid

    try:
        inv_uuid = uuid.UUID(invitation_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invitation ID",
        )

    result = await db.execute(
        select(Invitation).where(
            Invitation.id == inv_uuid,
            Invitation.created_by == current_user.id,
        )
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    await db.delete(invitation)

    return MessageResponse(message="Invitation deleted")
