"""
Dottò - Operator Schemas
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class OperatorLogin(BaseModel):
    """Schema for operator login."""
    phone: str = Field(..., min_length=5, max_length=20)
    pin: str = Field(..., min_length=4, max_length=6)


class OperatorRead(BaseModel):
    """Schema for reading an operator."""
    id: UUID
    name: str
    phone: Optional[str]
    email: Optional[str]
    is_admin: bool
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    operator: "OperatorBasicInfo"


class OperatorBasicInfo(BaseModel):
    """Basic operator info."""
    id: UUID
    name: str
    is_admin: bool


# Update forward refs
TokenResponse.model_rebuild()

