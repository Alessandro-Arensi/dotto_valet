"""
Dottò - Events API
"""
import math
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.event import Event
from app.models.token import Token
from app.models.checkin import Checkin
from app.models.rack import Rack
from app.models.operator import Operator

SLOTS_PER_RACK = 12


def _slugify(name: str) -> str:
    """Lowercase, ASCII, hyphen-separated slug."""
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return slug or "evento"


async def _unique_slug(db: AsyncSession, base: str) -> str:
    candidate = base
    counter = 2
    while True:
        existing = await db.execute(select(Event).where(Event.slug == candidate))
        if not existing.scalar_one_or_none():
            return candidate
        candidate = f"{base}-{counter}"
        counter += 1
from app.schemas.event import (
    EventCreate, EventUpdate, EventRead, EventStats, EventAvailability,
    EventPublicInfo, AvailabilityInfo
)
from app.services.auth import get_current_operator, get_current_admin

router = APIRouter()


@router.get("", response_model=List[EventRead])
async def list_events(
    active_only: bool = True,
    operator: Operator = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
):
    """List all events (requires authentication)."""
    query = select(Event).order_by(Event.start_date.desc())
    if active_only:
        query = query.where(Event.is_active == True)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: UUID,
    operator: Operator = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
):
    """Get event by ID."""
    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
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
    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Count tokens by status
    token_counts = await db.execute(
        select(
            func.count(Token.id).filter(Token.status == "reserved").label("reserved"),
            func.count(Token.id).filter(Token.status == "checked_in").label("checked_in"),
        ).where(Token.event_id == event_id)
    )
    counts = token_counts.one()
    reserved = counts.reserved or 0
    checked_in = counts.checked_in or 0
    
    # Count checkins in last 5 minutes
    five_min_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
    recent_result = await db.execute(
        select(func.count(Checkin.id)).where(
            Checkin.event_id == event_id,
            Checkin.checked_in_at >= five_min_ago,
        )
    )
    checkins_last_5min = recent_result.scalar() or 0
    
    occupied = reserved + checked_in
    available = max(0, event.total_capacity - occupied)
    occupancy_percent = (occupied / event.total_capacity * 100) if event.total_capacity > 0 else 0
    
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
    result = await db.execute(
        select(Event).where(Event.slug == slug, Event.is_active == True)
    )
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
    now = datetime.now(timezone.utc)
    can_reserve = available > 0 and (not event.end_date or event.end_date > now)
    
    message = None
    if available == 0:
        message = "Sold out"
    elif event.checkin_opens_at and event.checkin_opens_at > now:
        message = f"Check-in apre il {event.checkin_opens_at.strftime('%d/%m alle %H:%M')}"
    
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


# =============================================
# Public reservation
# =============================================
class ReservationRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, min_length=5, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    newsletter_opt_in: bool = False


class ReservationResponse(BaseModel):
    success: bool
    token: dict
    reservation: dict


@router.post("/{slug}/reserve", response_model=ReservationResponse)
async def create_reservation(
    slug: str,
    data: ReservationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Public reservation. No auth. Phone optional for MVP (future SMS)."""
    from app.services.token_service import get_unique_token_code, create_customer
    from app.config import get_settings

    settings = get_settings()

    result = await db.execute(
        select(Event).where(Event.slug == slug, Event.is_active == True)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    token_result = await db.execute(
        select(func.count(Token.id)).where(
            Token.event_id == event.id,
            Token.status.in_(["reserved", "checked_in"]),
        )
    )
    occupied = token_result.scalar() or 0
    if occupied >= event.total_capacity:
        raise HTTPException(status_code=400, detail="Event is sold out")

    customer = await create_customer(
        db,
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
        phone=data.phone,
        email=data.email,
        newsletter_opt_in=data.newsletter_opt_in,
    )

    code = await get_unique_token_code(db)
    token = Token(
        code=code,
        type="digital",
        status="reserved",
        event_id=event.id,
        customer_id=customer.id,
        reserved_at=datetime.now(timezone.utc),
        expires_at=event.end_date,
    )
    db.add(token)
    await db.flush()

    qr_url = f"{settings.app_url}/t/{token.code}"

    return ReservationResponse(
        success=True,
        token={
            "code": token.code,
            "qr_url": qr_url,
        },
        reservation={
            "expires_at": event.end_date.isoformat() if event.end_date else None,
            "checkin_opens_at": event.checkin_opens_at.isoformat() if event.checkin_opens_at else None,
            "customer_name": f"{customer.first_name} {customer.last_name}".strip(),
        },
    )


# =============================================
# Public walk-in self-service
# =============================================
class WalkinRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)


class WalkinPositionInfo(BaseModel):
    rack_id: UUID
    rack_number: int
    rack_label: Optional[str]
    slot_number: int


class WalkinResponse(BaseModel):
    success: bool
    token: dict
    position: WalkinPositionInfo
    customer_name: str


@router.post("/{slug}/walkin", response_model=WalkinResponse)
async def create_walkin(
    slug: str,
    data: WalkinRequest,
    db: AsyncSession = Depends(get_db),
):
    """Public walk-in self-service. No auth, no phone required.

    Creates customer by name, generates digital token (status=checked_in),
    auto-assigns the first free slot, creates the checkin row. Returns the
    token code and rack/slot for on-screen QR + screenshot.
    """
    from app.models.checkin import Checkin
    from app.services.token_service import get_unique_token_code, create_customer
    from app.config import get_settings

    settings = get_settings()

    result = await db.execute(
        select(Event).where(Event.slug == slug, Event.is_active == True)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    token_count = await db.execute(
        select(func.count(Token.id)).where(
            Token.event_id == event.id,
            Token.status.in_(["reserved", "checked_in"]),
        )
    )
    occupied = token_count.scalar() or 0
    if occupied >= event.total_capacity:
        raise HTTPException(status_code=400, detail="Event is sold out")

    from app.api.checkin import _pick_next_free_slot
    chosen_rack, chosen_slot = await _pick_next_free_slot(db, event.id)
    if not chosen_rack or chosen_slot is None:
        raise HTTPException(status_code=400, detail="No available slots")

    customer = await create_customer(
        db,
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
    )

    code = await get_unique_token_code(db)
    token = Token(
        code=code,
        type="digital",
        status="checked_in",
        event_id=event.id,
        customer_id=customer.id,
        reserved_at=datetime.now(timezone.utc),
    )
    db.add(token)
    await db.flush()

    checkin = Checkin(
        token_id=token.id,
        event_id=event.id,
        rack_id=chosen_rack.id,
        slot_number=chosen_slot,
        auto_positioned=True,
    )
    db.add(checkin)
    await db.flush()

    return WalkinResponse(
        success=True,
        token={
            "code": token.code,
            "qr_url": f"{settings.app_url}/t/{token.code}",
        },
        position=WalkinPositionInfo(
            rack_id=chosen_rack.id,
            rack_number=chosen_rack.rack_number,
            rack_label=chosen_rack.label,
            slot_number=chosen_slot,
        ),
        customer_name=f"{customer.first_name} {customer.last_name}".strip(),
    )


# =============================================
# Admin endpoints (require is_admin)
# =============================================

@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
async def admin_create_event(
    data: EventCreate,
    admin: Operator = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create an event (admin only).

    - If slug omitted, derive from name (unique, hyphen-separated).
    - Auto-seed ceil(total_capacity / SLOTS_PER_RACK) racks of SLOTS_PER_RACK slots each.
    """
    payload = data.model_dump(exclude_unset=True)

    slug = payload.pop("slug", None)
    if not slug:
        slug = await _unique_slug(db, _slugify(payload["name"]))
    else:
        clash = await db.execute(select(Event).where(Event.slug == slug))
        if clash.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Slug already in use")

    event = Event(slug=slug, **payload)
    db.add(event)
    await db.flush()

    rack_count = math.ceil(event.total_capacity / SLOTS_PER_RACK)
    for n in range(1, rack_count + 1):
        db.add(Rack(event_id=event.id, rack_number=n, slots=SLOTS_PER_RACK, label=f"Rastrelliera {n}"))

    await db.flush()
    await db.refresh(event)
    return event


@router.patch("/{event_id}", response_model=EventRead)
async def admin_update_event(
    event_id: UUID,
    data: EventUpdate,
    admin: Operator = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update event fields (admin only)."""
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    updates = data.model_dump(exclude_unset=True)
    if "slug" in updates and updates["slug"] != event.slug:
        clash = await db.execute(
            select(Event).where(Event.slug == updates["slug"], Event.id != event_id)
        )
        if clash.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Slug already in use")

    for key, value in updates.items():
        setattr(event, key, value)

    await db.flush()
    await db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_event(
    event_id: UUID,
    admin: Operator = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete event by marking inactive (admin only).

    Hard delete blocked when tokens or racks reference the event — operator
    should toggle is_active instead to preserve history.
    """
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    event.is_active = False
    await db.flush()
    return None

