"""
Dottò - Rack Model
"""
from typing import Optional
from uuid import UUID

from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Rack(Base):
    """Rack model - represents a bike rack at an event."""
    
    __tablename__ = "racks"
    __table_args__ = (
        UniqueConstraint("event_id", "rack_number", name="uq_rack_event_number"),
    )
    
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    rack_number: Mapped[int] = mapped_column(Integer, nullable=False)
    slots: Mapped[int] = mapped_column(Integer, default=12)
    label: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Relationships
    event = relationship("Event", back_populates="racks")
    checkins = relationship("Checkin", back_populates="rack")
    
    def __repr__(self) -> str:
        return f"<Rack {self.rack_number} @ Event {self.event_id}>"

