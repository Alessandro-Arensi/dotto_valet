"""
Dottò - Checkin Schemas
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CheckinCreate(BaseModel):
    """Schema for creating a check-in."""

    token_code: str = Field(..., description="Token code from QR scan")

    # For new digital tokens (without reservation)
    create_token: bool = False
    customer_phone: str | None = None
    customer_email: str | None = None
    newsletter_opt_in: bool = False

    # For physical tokens
    physical_token: bool = False

    # Position
    auto_position: bool = True
    rack_id: UUID | None = None
    slot_number: int | None = Field(None, ge=1)

    # Photo (required for physical tokens)
    bike_photo_base64: str | None = None

    @field_validator("bike_photo_base64")
    @classmethod
    def validate_photo_for_physical(cls, v, info):
        """Photo is required for physical tokens."""
        # Validation happens at API level with full context
        return v


class CheckinRead(BaseModel):
    """Schema for reading a check-in."""

    id: UUID
    token_id: UUID
    event_id: UUID
    rack_id: UUID
    slot_number: int
    bike_photo_url: str | None
    auto_positioned: bool
    checked_in_at: datetime
    checked_out_at: datetime | None

    class Config:
        from_attributes = True


class CheckinResponse(BaseModel):
    """Response after successful check-in."""

    success: bool
    checkin_id: UUID
    token: "CheckinTokenInfo"
    position: "CheckinPositionInfo"
    customer: Optional["CheckinCustomerInfo"]
    message_sent: bool = False
    warnings: list[str] = []


class CheckinTokenInfo(BaseModel):
    """Token info in check-in response."""

    code: str
    type: str


class CheckinPositionInfo(BaseModel):
    """Position info in check-in response."""

    rack_number: int
    slot_number: int
    rack_label: str | None
    auto_assigned: bool


class CheckinCustomerInfo(BaseModel):
    """Customer info in check-in response (masked)."""

    phone_masked: str | None


class CheckoutRequest(BaseModel):
    """Schema for check-out request."""

    token_code: str


class CheckoutResponse(BaseModel):
    """Response after successful check-out."""

    success: bool
    checkin: "CheckoutCheckinInfo"
    customer: CheckinCustomerInfo | None
    token_type: str


class CheckoutCheckinInfo(BaseModel):
    """Checkin info for check-out."""

    position: str
    checked_in_at: datetime
    bike_photo_url: str | None


# Update forward refs
CheckinResponse.model_rebuild()
CheckoutResponse.model_rebuild()
