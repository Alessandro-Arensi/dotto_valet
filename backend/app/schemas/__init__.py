"""
Dottò - Pydantic Schemas
"""
from app.schemas.event import EventCreate, EventUpdate, EventRead, EventStats, EventAvailability
from app.schemas.token import TokenCreate, TokenRead, TokenInfo
from app.schemas.checkin import CheckinCreate, CheckinRead, CheckoutRequest
from app.schemas.operator import OperatorLogin, OperatorRead, OperatorCreate, OperatorUpdate, TokenResponse
from app.schemas.customer import CustomerRead
from app.schemas.rack import RackCreate, RackUpdate, RackRead

__all__ = [
    "EventCreate",
    "EventUpdate",
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
    "OperatorCreate",
    "OperatorUpdate",
    "TokenResponse",
    "CustomerRead",
    "RackCreate",
    "RackUpdate",
    "RackRead",
]


