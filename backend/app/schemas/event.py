"""
Dottò - Event Schemas
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class EventBase(BaseModel):
    """Base event schema."""
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = None
    location: Optional[str] = Field(None, max_length=255)
    start_date: datetime
    end_date: Optional[datetime] = None
    checkin_opens_at: Optional[datetime] = None
    total_capacity: int = Field(..., gt=0)
    fast_mode_threshold: int = Field(default=80, ge=0, le=100)


class EventCreate(EventBase):
    """Schema for creating an event."""
    pass


class EventRead(EventBase):
    """Schema for reading an event."""
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class EventStats(BaseModel):
    """Real-time event statistics."""
    event_id: UUID
    total_capacity: int
    checked_in: int
    reserved: int
    available: int
    occupancy_percent: float
    checkins_last_5min: int = 0
    suggest_fast_mode: bool = False


class EventAvailability(BaseModel):
    """Public availability info for an event."""
    event: "EventPublicInfo"
    availability: "AvailabilityInfo"
    can_reserve: bool
    message: Optional[str] = None


class EventPublicInfo(BaseModel):
    """Public event info (no sensitive data)."""
    name: str
    slug: str
    location: Optional[str]
    start_date: datetime
    checkin_opens_at: Optional[datetime]


class AvailabilityInfo(BaseModel):
    """Availability numbers."""
    total: int
    available: int
    occupied: int
    percent: float


# Update forward refs
EventAvailability.model_rebuild()

