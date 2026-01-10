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
    """Customer model - bike owners with minimal data."""
    
    __tablename__ = "customers"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    phone_normalized: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255))
    newsletter_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    tokens = relationship("Token", back_populates="customer")
    
    def __repr__(self) -> str:
        return f"<Customer {self.phone_normalized}>"

