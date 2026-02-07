"""
Dottò - Events API
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.checkin import Checkin
from app.models.event import Event
from app.models.operator import Operator
from app.models.rack import Rack
from app.models.token import Token
from app.schemas.event import (
    AvailabilityInfo,
    EventAvailability,
    EventPublicInfo,
    EventRead,
    EventStats,
)
from app.services.auth import get_current_operator

router = APIRouter()


@router.get("", response_model=list[EventRead])
async def list_events(
    active_only: bool = True,
    operator: Operator = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
):
    """List all events (requires authentication)."""
    query = select(Event).order_by(Event.start_date.desc())
    if active_only:
        query = query.where(Event.is_active)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: UUID,
    operator: Operator = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
):
    """Get event by ID."""
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.get("/{event_id}/stats", response_model=EventStats)
async def get_event_stats(
    event_id: UUID,
    operator: Operator = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
):
    """Get real-time event statistics."""
    # Get event
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Count tokens by status
    token_counts = await db.execute(
        select(
            func.count(Token.id).filter(Token.status == "reserved").label("reserved"),
            func.count(Token.id)
            .filter(Token.status == "checked_in")
            .label("checked_in"),
        ).where(Token.event_id == event_id)
    )
    counts = token_counts.one()
    reserved = counts.reserved or 0
    checked_in = counts.checked_in or 0

    # Count checkins in last 5 minutes
    five_min_ago = datetime.now(UTC) - timedelta(minutes=5)
    recent_result = await db.execute(
        select(func.count(Checkin.id)).where(
            Checkin.event_id == event_id,
            Checkin.checked_in_at >= five_min_ago,
        )
    )
    checkins_last_5min = recent_result.scalar() or 0

    occupied = reserved + checked_in
    available = max(0, event.total_capacity - occupied)
    occupancy_percent = (
        (occupied / event.total_capacity * 100) if event.total_capacity > 0 else 0
    )

    return EventStats(
        event_id=event_id,
        total_capacity=event.total_capacity,
        checked_in=checked_in,
        reserved=reserved,
        available=available,
        occupancy_percent=round(occupancy_percent, 1),
        checkins_last_5min=checkins_last_5min,
        suggest_fast_mode=occupancy_percent >= event.fast_mode_threshold,
    )


@router.get("/{event_id}/next-slot")
async def get_next_available_slot(
    event_id: UUID,
    operator: Operator = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
):
    """Get the next available slot for an event."""
    # Get all racks for the event
    result = await db.execute(
        select(Rack).where(Rack.event_id == event_id).order_by(Rack.rack_number)
    )
    racks = result.scalars().all()

    if not racks:
        raise HTTPException(status_code=404, detail="No racks found for this event")

    # Find first available slot
    for rack in racks:
        # Get occupied slots for this rack
        occupied_result = await db.execute(
            select(Checkin.slot_number).where(
                Checkin.rack_id == rack.id,
                Checkin.checked_out_at.is_(None),
            )
        )
        occupied_slots = {row[0] for row in occupied_result.all()}

        # Find first free slot
        for slot in range(1, rack.slots + 1):
            if slot not in occupied_slots:
                return {
                    "rack_id": rack.id,
                    "rack_number": rack.rack_number,
                    "slot_number": slot,
                    "rack_label": rack.label,
                }

    raise HTTPException(status_code=404, detail="No available slots")


# Public endpoint (no auth required)
@router.get("/{slug}/availability", response_model=EventAvailability)
async def get_event_availability(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Get public availability info for an event (by slug)."""
    result = await db.execute(select(Event).where(Event.slug == slug, Event.is_active))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Count occupied tokens
    token_result = await db.execute(
        select(func.count(Token.id)).where(
            Token.event_id == event.id,
            Token.status.in_(["reserved", "checked_in"]),
        )
    )
    occupied = token_result.scalar() or 0
    available = max(0, event.total_capacity - occupied)
    percent = (occupied / event.total_capacity * 100) if event.total_capacity > 0 else 0

    # Check if can reserve
    now = datetime.now(UTC)
    can_reserve = available > 0 and (not event.end_date or event.end_date > now)

    message = None
    if available == 0:
        message = "Sold out"
    elif event.checkin_opens_at and event.checkin_opens_at > now:
        message = (
            f"Check-in apre il {event.checkin_opens_at.strftime('%d/%m alle %H:%M')}"
        )

    return EventAvailability(
        event=EventPublicInfo(
            name=event.name,
            slug=event.slug,
            location=event.location,
            start_date=event.start_date,
            checkin_opens_at=event.checkin_opens_at,
        ),
        availability=AvailabilityInfo(
            total=event.total_capacity,
            available=available,
            occupied=occupied,
            percent=round(percent, 1),
        ),
        can_reserve=can_reserve,
        message=message,
    )


# Public reservation endpoint
class ReservationRequest(BaseModel):
    phone: str
    email: str | None = None
    newsletter_opt_in: bool = False


class ReservationResponse(BaseModel):
    success: bool
    token: dict
    reservation: dict
    message_sent: bool


@router.post("/{slug}/reserve", response_model=ReservationResponse)
async def create_reservation(
    slug: str,
    data: ReservationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a public reservation for an event.
    No authentication required.
    """
    from app.config import get_settings
    from app.services.token_service import (
        get_or_create_customer,
        get_unique_token_code,
    )

    settings = get_settings()

    # Find event
    result = await db.execute(select(Event).where(Event.slug == slug, Event.is_active))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Check availability
    token_result = await db.execute(
        select(func.count(Token.id)).where(
            Token.event_id == event.id,
            Token.status.in_(["reserved", "checked_in"]),
        )
    )
    occupied = token_result.scalar() or 0
    if occupied >= event.total_capacity:
        raise HTTPException(status_code=400, detail="Event is sold out")

    # Get or create customer
    customer = await get_or_create_customer(
        db,
        phone=data.phone,
        email=data.email,
        newsletter_opt_in=data.newsletter_opt_in,
    )

    # Check if customer already has a reservation for this event
    existing = await db.execute(
        select(Token).where(
            Token.customer_id == customer.id,
            Token.event_id == event.id,
            Token.status.in_(["reserved", "checked_in"]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail="You already have a reservation for this event"
        )

    # Create token
    code = await get_unique_token_code(db)
    token = Token(
        code=code,
        type="digital",
        status="reserved",
        event_id=event.id,
        customer_id=customer.id,
        reserved_at=datetime.now(UTC),
        expires_at=event.end_date,
    )
    db.add(token)
    await db.flush()

    # TODO: Send SMS via Twilio
    message_sent = False

    return ReservationResponse(
        success=True,
        token={
            "code": token.code,
            "qr_url": f"{settings.app_url}/t/{token.code}",
            "wallet_url": f"{settings.app_url}/wallet/{token.code}",
        },
        reservation={
            "expires_at": event.end_date.isoformat() if event.end_date else None,
            "checkin_opens_at": (
                event.checkin_opens_at.isoformat() if event.checkin_opens_at else None
            ),
        },
        message_sent=message_sent,
    )
