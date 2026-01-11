"""
Dottò - Event Model
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import String, Integer, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Event(Base):
    """Event model - represents a bike valet event."""
    
    __tablename__ = "events"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    location: Mapped[Optional[str]] = mapped_column(String(255))
    
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    checkin_opens_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    total_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    fast_mode_threshold: Mapped[int] = mapped_column(Integer, default=80)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    racks = relationship("Rack", back_populates="event", cascade="all, delete-orphan")
    tokens = relationship("Token", back_populates="event")
    checkins = relationship("Checkin", back_populates="event")
    
    def __repr__(self) -> str:
        return f"<Event {self.slug}>"


