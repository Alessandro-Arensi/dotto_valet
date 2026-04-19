"""
Dottò - Customer Schemas
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class CustomerRead(BaseModel):
    """Schema for reading a customer."""
    id: UUID
    first_name: Optional[str]
    last_name: Optional[str]
    phone: Optional[str]
    phone_normalized: Optional[str]
    email: Optional[str]
    newsletter_opt_in: bool
    created_at: datetime

    class Config:
        from_attributes = True
