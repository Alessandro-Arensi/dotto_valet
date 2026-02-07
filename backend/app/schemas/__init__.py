"""
Dottò - Pydantic Schemas
"""

from app.schemas.checkin import CheckinCreate, CheckinRead, CheckoutRequest
from app.schemas.customer import CustomerCreate, CustomerRead
from app.schemas.event import EventAvailability, EventCreate, EventRead, EventStats
from app.schemas.operator import OperatorLogin, OperatorRead, TokenResponse
from app.schemas.token import TokenCreate, TokenInfo, TokenRead

__all__ = [
    "EventCreate",
    "EventRead",
    "EventStats",
    "EventAvailability",
    "TokenCreate",
    "TokenRead",
    "TokenInfo",
    "CheckinCreate",
    "CheckinRead",
    "CheckoutRequest",
    "OperatorLogin",
    "OperatorRead",
    "TokenResponse",
    "CustomerCreate",
    "CustomerRead",
]
