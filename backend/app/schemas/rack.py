"""
Dottò - Rack Schemas
"""
from datetime import datetime
from typing import List, Optional, Literal
from uuid import UUID
from pydantic import BaseModel, Field


class RackCreate(BaseModel):
    rack_number: int = Field(..., ge=1)
    slots: int = Field(default=12, ge=1, le=100)
    label: Optional[str] = Field(None, max_length=50)


class RackUpdate(BaseModel):
    rack_number: Optional[int] = Field(None, ge=1)
    slots: Optional[int] = Field(None, ge=1, le=100)
    label: Optional[str] = Field(None, max_length=50)


class RackRead(BaseModel):
    id: UUID
    event_id: UUID
    rack_number: int
    slots: int
    label: Optional[str]

    class Config:
        from_attributes = True


SlotStatus = Literal["free", "checked_in", "blocked"]


class SlotState(BaseModel):
    slot_number: int
    status: SlotStatus
    token_code: Optional[str] = None
    block_reason: Optional[str] = None


class RackDetail(BaseModel):
    id: UUID
    event_id: UUID
    rack_number: int
    label: Optional[str]
    slots: int
    states: List[SlotState]


class SlotBlockCreate(BaseModel):
    slot_number: int = Field(..., ge=1)
    reason: Optional[str] = Field(None, max_length=500)


class SlotBlockRead(BaseModel):
    id: UUID
    rack_id: UUID
    slot_number: int
    reason: Optional[str]
    created_at: datetime
    released_at: Optional[datetime]

    class Config:
        from_attributes = True
