"""
Dottò - ActivityLog Model
"""
from datetime import datetime
from typing import Optional, Any
from uuid import UUID

from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, INET
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class ActivityLog(Base):
    """ActivityLog model - audit trail for all operations."""
    
    __tablename__ = "activity_logs"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    operator_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("operators.id"))
    event_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("events.id"))
    
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50))
    entity_id: Mapped[Optional[UUID]] = mapped_column()
    
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column("metadata", JSONB)
    ip_address: Mapped[Optional[str]] = mapped_column(INET)
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self) -> str:
        return f"<ActivityLog {self.action} @ {self.created_at}>"


