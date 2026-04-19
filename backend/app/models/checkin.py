"""
Dottò - Checkin Model
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Checkin(Base):
    """Checkin model - a parked bike record."""
    
    __tablename__ = "checkins"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    token_id: Mapped[UUID] = mapped_column(ForeignKey("tokens.id"), nullable=False)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id"), nullable=False)

    rack_id: Mapped[UUID] = mapped_column(ForeignKey("racks.id"), nullable=False)
    slot_number: Mapped[int] = mapped_column(Integer, nullable=False)

    bike_description: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Flags
    auto_positioned: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    checked_in_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    checked_out_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Operators
    checked_in_by: Mapped[Optional[UUID]] = mapped_column(ForeignKey("operators.id"))
    checked_out_by: Mapped[Optional[UUID]] = mapped_column(ForeignKey("operators.id"))
    
    # Override (for lost token cases)
    manual_override: Mapped[bool] = mapped_column(Boolean, default=False)
    override_reason: Mapped[Optional[str]] = mapped_column(Text)
    
    # Relationships
    token = relationship("Token", foreign_keys=[token_id])
    event = relationship("Event", back_populates="checkins")
    rack = relationship("Rack", back_populates="checkins")
    
    def __repr__(self) -> str:
        return f"<Checkin {self.token_id} @ Rack {self.rack_id} Slot {self.slot_number}>"


