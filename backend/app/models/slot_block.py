"""
Dottò - SlotBlock Model
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class SlotBlock(Base):
    """A slot temporarily marked as unavailable without a checkin row.

    Use cases:
    - Bike parked at wrong slot (operator blocks real occupied slot, reassigns target)
    - Cargo bike needing multiple slots
    - Rack maintenance
    """

    __tablename__ = "slot_blocks"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    rack_id: Mapped[UUID] = mapped_column(ForeignKey("racks.id", ondelete="CASCADE"), nullable=False)
    slot_number: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[Optional[UUID]] = mapped_column(ForeignKey("operators.id"))
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    released_by: Mapped[Optional[UUID]] = mapped_column(ForeignKey("operators.id"))

    rack = relationship("Rack")
