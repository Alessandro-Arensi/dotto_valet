"""
Dottò - Customer Model
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Customer(Base):
    """Customer model - bike owners. Name is primary identifier; phone optional (future SMS)."""

    __tablename__ = "customers"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    phone_normalized: Mapped[Optional[str]] = mapped_column(String(20))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    newsletter_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    tokens = relationship("Token", back_populates="customer")

    def __repr__(self) -> str:
        label = f"{self.last_name} {self.first_name}" if self.last_name else self.phone_normalized
        return f"<Customer {label}>"
