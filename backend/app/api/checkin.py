"""
Dottò - Check-in/out API
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.event import Event
from app.models.token import Token
from app.models.checkin import Checkin
from app.models.rack import Rack
from app.models.operator import Operator
from app.schemas.checkin import (
    CheckinCreate, CheckinResponse, CheckinTokenInfo, CheckinPositionInfo, 
    CheckinCustomerInfo, CheckoutRequest, CheckoutResponse, CheckoutCheckinInfo
)
from app.services.auth import get_current_operator
from app.services.token_service import (
    get_unique_token_code, get_or_create_customer, mask_phone
)

router = APIRouter()


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
        
        # Get active event (for now, get the first active one)
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
    
    # Validate physical token photo requirement
    if data.physical_token or token.type == "physical":
        if not data.bike_photo_base64:
            raise HTTPException(
                status_code=400,
                detail="Photo required for physical tokens"
            )
        token.type = "physical"
    
    # Get position
    rack: Optional[Rack] = None
    slot_number: int
    auto_assigned = False
    
    if data.auto_position:
        # Auto-assign position
        racks_result = await db.execute(
            select(Rack).where(Rack.event_id == token.event_id).order_by(Rack.rack_number)
        )
        racks = racks_result.scalars().all()
        
        for r in racks:
            occupied_result = await db.execute(
                select(Checkin.slot_number).where(
                    Checkin.rack_id == r.id,
                    Checkin.checked_out_at.is_(None),
                )
            )
            occupied_slots = {row[0] for row in occupied_result.all()}
            
            for s in range(1, r.slots + 1):
                if s not in occupied_slots:
                    rack = r
                    slot_number = s
                    auto_assigned = True
                    break
            if rack:
                break
        
        if not rack:
            raise HTTPException(status_code=400, detail="No available slots")
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
    
    # Handle photo upload (placeholder - will be implemented with Supabase Storage)
    bike_photo_url = None
    if data.bike_photo_base64:
        # TODO: Upload to Supabase Storage
        bike_photo_url = f"https://placeholder.com/photos/{token.code}.jpg"
        warnings.append("Photo upload not yet implemented")
    
    # Create checkin
    checkin = Checkin(
        token_id=token.id,
        event_id=token.event_id,
        rack_id=rack.id,
        slot_number=slot_number,
        bike_photo_url=bike_photo_url,
        auto_positioned=auto_assigned,
        checked_in_by=operator.id,
    )
    db.add(checkin)
    
    # Update token status
    token.status = "checked_in"
    
    await db.flush()
    
    # Prepare response
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
        message_sent=False,  # TODO: Implement SMS
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
            bike_photo_url=checkin.bike_photo_url,
        ),
        customer=customer_info,
        token_type=token.type,
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
            "bike_photo_url": c.bike_photo_url,
            "customer_phone": mask_phone(c.token.customer.phone_normalized) if c.token.customer else None,
        }
        for c in checkins
    ]


