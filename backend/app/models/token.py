"""
Dottò - Token Model
"""
from datetime import datetime
from typing import Optional, Literal
from uuid import UUID

from sqlalchemy import String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base

# Token types
TokenType = Literal["digital", "physical"]
TokenStatus = Literal["available", "reserved", "checked_in", "checked_out", "expired", "lost"]


class Token(Base):
    """Token model - QR code identifier for bikes."""
    
    __tablename__ = "tokens"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    
    type: Mapped[str] = mapped_column(
        Enum(
            "digital", "physical",
            name="token_type",
            native_enum=False,
            length=10,
        ),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Enum(
            "available", "reserved", "checked_in", "checked_out", "expired", "lost",
            name="token_status",
            native_enum=False,
            length=15,
        ),
        default="reserved",
    )
    
    event_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("events.id"))
    customer_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("customers.id"))
    
    reserved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    event = relationship("Event", back_populates="tokens")
    customer = relationship("Customer", back_populates="tokens")
    # Active checkin only (checked_out_at IS NULL). Physical tokens can have multiple historical rows.
    checkin = relationship(
        "Checkin",
        uselist=False,
        primaryjoin="and_(Token.id==Checkin.token_id, Checkin.checked_out_at.is_(None))",
        foreign_keys="Checkin.token_id",
        viewonly=True,
    )
    
    def __repr__(self) -> str:
        return f"<Token {self.code}>"


