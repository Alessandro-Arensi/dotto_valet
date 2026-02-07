"""
Dottò - Token Schemas
"""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel

TokenType = Literal["digital", "physical"]
TokenStatus = Literal[
    "available", "reserved", "checked_in", "checked_out", "expired", "lost"
]


class TokenBase(BaseModel):
    """Base token schema."""

    type: TokenType
    event_id: UUID


class TokenCreate(TokenBase):
    """Schema for creating a token."""

    customer_id: UUID | None = None


class TokenRead(BaseModel):
    """Schema for reading a token."""

    id: UUID
    code: str
    type: TokenType
    status: TokenStatus
    event_id: UUID | None
    customer_id: UUID | None
    reserved_at: datetime | None
    expires_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class TokenInfo(BaseModel):
    """Token info for QR page."""

    token: "TokenBasicInfo"
    event: Optional["TokenEventInfo"]
    checkin: Optional["TokenCheckinInfo"]


class TokenBasicInfo(BaseModel):
    """Basic token info."""

    code: str
    status: TokenStatus
    type: TokenType


class TokenEventInfo(BaseModel):
    """Event info for token."""

    name: str
    location: str | None
    date: datetime


class TokenCheckinInfo(BaseModel):
    """Checkin info for token."""

    position: str  # "Rastrelliera 3, Slot 7"
    checked_in_at: datetime
    photo_url: str | None


class TokenQR(BaseModel):
    """QR code response."""

    code: str
    qr_url: str
    wallet_url: str


# Update forward refs
TokenInfo.model_rebuild()
