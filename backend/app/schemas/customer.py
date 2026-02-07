"""
Dottò - Customer Schemas
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class CustomerBase(BaseModel):
    """Base customer schema."""

    phone: str = Field(..., min_length=5, max_length=20)
    email: EmailStr | None = None
    newsletter_opt_in: bool = False


class CustomerCreate(CustomerBase):
    """Schema for creating a customer."""

    pass


class CustomerRead(BaseModel):
    """Schema for reading a customer."""

    id: UUID
    phone: str
    phone_normalized: str
    email: str | None
    newsletter_opt_in: bool
    created_at: datetime

    class Config:
        from_attributes = True
