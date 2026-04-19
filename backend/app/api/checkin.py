"""
Dottò - Check-in/out API
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.event import Event
from app.models.token import Token
from app.models.checkin import Checkin
from app.models.rack import Rack
from app.models.operator import Operator
from app.models.slot_block import SlotBlock
from app.schemas.checkin import (
    CheckinCreate, CheckinResponse, CheckinTokenInfo, CheckinPositionInfo, 
    CheckinCustomerInfo, CheckoutRequest, CheckoutResponse, CheckoutCheckinInfo
)
from app.services.auth import get_current_operator
from app.services.token_service import (
    get_unique_token_code, get_or_create_customer, mask_phone
)
from app.services.sms import send_checkin_sms
from app.config import get_settings

router = APIRouter()


async def _pick_next_free_slot(db: AsyncSession, event_id):
    """Scan racks by rack_number, return first slot not checked-in nor blocked.

    Returns (rack, slot_number) or (None, None) if nothing free.
    """
    racks_result = await db.execute(
        select(Rack).where(Rack.event_id == event_id).order_by(Rack.rack_number)
    )
    for rack in racks_result.scalars().all():
        occ_result = await db.execute(
            select(Checkin.slot_number).where(
                Checkin.rack_id == rack.id,
                Checkin.checked_out_at.is_(None),
            )
        )
        occupied = {row[0] for row in occ_result.all()}
        blk_result = await db.execute(
            select(SlotBlock.slot_number).where(
                SlotBlock.rack_id == rack.id,
                SlotBlock.released_at.is_(None),
            )
        )
        blocked = {row[0] for row in blk_result.all()}
        for s in range(1, rack.slots + 1):
            if s not in occupied and s not in blocked:
                return rack, s
    return None, None


@router.post("/checkin", response_model=CheckinResponse)
async def create_checkin(
    data: CheckinCreate,
    operator: Operator = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
):
    """
    Check-in a bike.
    
    Supports:
    - Existing token (from reservation or physical token)
    - Creating new digital token on the spot
    """
    warnings = []
    token: Optional[Token] = None
    
    # Find or create token
    if data.create_token:
        # Create new digital token
        if not data.customer_phone:
            raise HTTPException(
                status_code=400,
                detail="Phone number required for new digital token"
            )
        
        # Get customer
        customer = await get_or_create_customer(
            db,
            phone=data.customer_phone,
            email=data.customer_email,
            newsletter_opt_in=data.newsletter_opt_in,
        )
        
        # Check for existing active token for this customer
        existing = await db.execute(
            select(Token).where(
                Token.customer_id == customer.id,
                Token.status.in_(["reserved", "checked_in"]),
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Customer already has an active token"
            )
        
        # Use supplied event_id or fall back to first active event.
        if data.event_id:
            event_result = await db.execute(
                select(Event).where(Event.id == data.event_id, Event.is_active == True)
            )
            event = event_result.scalar_one_or_none()
            if not event:
                raise HTTPException(status_code=404, detail="Event not found or inactive")
        else:
            event_result = await db.execute(
                select(Event).where(Event.is_active == True).limit(1)
            )
            event = event_result.scalar_one_or_none()
            if not event:
                raise HTTPException(status_code=400, detail="No active event")
        
        # Create token
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
        
    else:
        # Find existing token
        result = await db.execute(
            select(Token)
            .options(selectinload(Token.customer))
            .where(Token.code == data.token_code.upper())
        )
        token = result.scalar_one_or_none()
        
        if not token:
            raise HTTPException(status_code=404, detail="Token not found")
        
        if token.status == "checked_in":
            raise HTTPException(status_code=400, detail="Token already checked in")
        
        if token.status not in ["reserved", "available"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Token cannot be checked in (status: {token.status})"
            )
    
    if data.physical_token:
        token.type = "physical"
    
    # Get position
    rack: Optional[Rack] = None
    slot_number: int
    auto_assigned = False
    
    if data.auto_position:
        rack, slot_number = await _pick_next_free_slot(db, token.event_id)
        if not rack:
            raise HTTPException(status_code=400, detail="No available slots")
        auto_assigned = True
    else:
        # Manual position
        if not data.rack_id or not data.slot_number:
            raise HTTPException(
                status_code=400,
                detail="Rack and slot required when auto_position is false"
            )
        
        rack_result = await db.execute(
            select(Rack).where(Rack.id == data.rack_id)
        )
        rack = rack_result.scalar_one_or_none()
        if not rack:
            raise HTTPException(status_code=404, detail="Rack not found")
        
        # Check slot availability
        occupied = await db.execute(
            select(Checkin).where(
                Checkin.rack_id == rack.id,
                Checkin.slot_number == data.slot_number,
                Checkin.checked_out_at.is_(None),
            )
        )
        if occupied.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Slot is occupied")
        
        slot_number = data.slot_number
    
    checkin = Checkin(
        token_id=token.id,
        event_id=token.event_id,
        rack_id=rack.id,
        slot_number=slot_number,
        bike_description=data.bike_description,
        auto_positioned=auto_assigned,
        checked_in_by=operator.id,
    )
    db.add(checkin)

    token.status = "checked_in"

    await db.flush()

    # Eager load customer if not already loaded (e.g., when create_token=true path)
    if token.customer_id and not token.customer:
        cust_result = await db.execute(
            select(Token).options(selectinload(Token.customer)).where(Token.id == token.id)
        )
        reloaded = cust_result.scalar_one()
        token.customer = reloaded.customer

    settings = get_settings()
    position_str = f"Rastrelliera {rack.rack_number}, Slot {slot_number}"
    if rack.label:
        position_str = f"{rack.label}, Slot {slot_number}"

    message_sent = False
    if token.customer and token.customer.phone_normalized:
        message_sent = await send_checkin_sms(
            phone=token.customer.phone_normalized,
            token_code=token.code,
            position=position_str,
            qr_url=f"{settings.app_url}/t/{token.code}",
        )

    customer_info = None
    if token.customer:
        customer_info = CheckinCustomerInfo(
            phone_masked=mask_phone(token.customer.phone_normalized)
        )

    return CheckinResponse(
        success=True,
        checkin_id=checkin.id,
        token=CheckinTokenInfo(code=token.code, type=token.type),
        position=CheckinPositionInfo(
            rack_number=rack.rack_number,
            slot_number=slot_number,
            rack_label=rack.label,
            auto_assigned=auto_assigned,
        ),
        customer=customer_info,
        message_sent=message_sent,
        warnings=warnings,
    )


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    data: CheckoutRequest,
    operator: Operator = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
):
    """Check-out a bike."""
    # Find token with checkin
    result = await db.execute(
        select(Token)
        .options(
            selectinload(Token.checkin).selectinload(Checkin.rack),
            selectinload(Token.customer),
        )
        .where(Token.code == data.token_code.upper())
    )
    token = result.scalar_one_or_none()
    
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    
    if token.status != "checked_in":
        raise HTTPException(
            status_code=400,
            detail=f"Token is not checked in (status: {token.status})"
        )
    
    if not token.checkin:
        raise HTTPException(status_code=400, detail="No checkin record found")
    
    checkin = token.checkin
    
    # Update checkin
    checkin.checked_out_at = datetime.now(timezone.utc)
    checkin.checked_out_by = operator.id
    
    # Update token status
    if token.type == "physical":
        token.status = "available"  # Physical tokens can be reused
    else:
        token.status = "checked_out"
    
    # Prepare response
    position = f"Rastrelliera {checkin.rack.rack_number}"
    if checkin.rack.label:
        position = f"{checkin.rack.label}"
    position += f", Slot {checkin.slot_number}"
    
    customer_info = None
    if token.customer:
        customer_info = CheckinCustomerInfo(
            phone_masked=mask_phone(token.customer.phone_normalized)
        )
    
    return CheckoutResponse(
        success=True,
        checkin=CheckoutCheckinInfo(
            position=position,
            checked_in_at=checkin.checked_in_at,
            bike_description=checkin.bike_description,
        ),
        customer=customer_info,
        token_type=token.type,
    )


class ReassignResponse(BaseModel):
    success: bool
    checkin_id: UUID
    token_code: str
    position: CheckinPositionInfo


@router.post("/checkins/{checkin_id}/reassign", response_model=ReassignResponse)
async def reassign_checkin(
    checkin_id: UUID,
    operator: Operator = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
):
    """Reassign a checkin to a different slot + block the original one.

    Used when operator discovers the assigned slot is physically occupied
    by another bike (misparked, cargo) and needs to move the customer.
    """
    result = await db.execute(
        select(Checkin).options(selectinload(Checkin.token)).where(Checkin.id == checkin_id)
    )
    checkin = result.scalar_one_or_none()
    if not checkin:
        raise HTTPException(status_code=404, detail="Check-in not found")
    if checkin.checked_out_at is not None:
        raise HTTPException(status_code=400, detail="Check-in already closed")

    # Block the slot currently held by this checkin (so no one else gets it)
    block = SlotBlock(
        rack_id=checkin.rack_id,
        slot_number=checkin.slot_number,
        reason="Occupato da bici fuori posto (reassign automatico)",
        created_by=operator.id,
    )
    db.add(block)
    await db.flush()

    # Temporarily move this checkin off the blocked slot so _pick_next_free_slot
    # sees it as unavailable (the block itself handles that), and find a new spot.
    new_rack, new_slot = await _pick_next_free_slot(db, checkin.event_id)
    if not new_rack or new_slot is None:
        # Rollback the block since we can't reassign
        block.released_at = datetime.now(timezone.utc)
        block.released_by = operator.id
        await db.flush()
        raise HTTPException(status_code=400, detail="No other slots available")

    checkin.rack_id = new_rack.id
    checkin.slot_number = new_slot
    await db.flush()

    return ReassignResponse(
        success=True,
        checkin_id=checkin.id,
        token_code=checkin.token.code,
        position=CheckinPositionInfo(
            rack_number=new_rack.rack_number,
            slot_number=new_slot,
            rack_label=new_rack.label,
            auto_assigned=True,
        ),
    )


@router.get("/checkins/{event_id}")
async def list_checkins(
    event_id: UUID,
    status: str = "active",  # active | all
    operator: Operator = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
):
    """List checkins for an event."""
    query = (
        select(Checkin)
        .options(
            selectinload(Checkin.token).selectinload(Token.customer),
            selectinload(Checkin.rack),
        )
        .where(Checkin.event_id == event_id)
        .order_by(Checkin.checked_in_at.desc())
    )
    
    if status == "active":
        query = query.where(Checkin.checked_out_at.is_(None))
    
    result = await db.execute(query)
    checkins = result.scalars().all()
    
    return [
        {
            "id": c.id,
            "token_code": c.token.code,
            "token_type": c.token.type,
            "rack_number": c.rack.rack_number,
            "rack_label": c.rack.label,
            "slot_number": c.slot_number,
            "checked_in_at": c.checked_in_at,
            "checked_out_at": c.checked_out_at,
            "bike_description": c.bike_description,
            "customer_phone": mask_phone(c.token.customer.phone_normalized) if c.token.customer else None,
        }
        for c in checkins
    ]


