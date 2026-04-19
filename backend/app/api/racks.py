"""
Dottò - Racks Admin API
"""
from typing import List
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.event import Event
from app.models.rack import Rack
from app.models.checkin import Checkin
from app.models.token import Token
from app.models.operator import Operator
from app.models.slot_block import SlotBlock
from app.schemas.rack import (
    RackCreate,
    RackUpdate,
    RackRead,
    RackDetail,
    SlotState,
    SlotBlockCreate,
    SlotBlockRead,
)
from app.services.auth import get_current_operator, get_current_admin

router = APIRouter()


async def _rack_states(db: AsyncSession, rack: Rack) -> List[SlotState]:
    """Compute per-slot status for a rack (free / checked_in / blocked)."""
    checkins_result = await db.execute(
        select(Checkin, Token.code)
        .join(Token, Token.id == Checkin.token_id)
        .where(Checkin.rack_id == rack.id, Checkin.checked_out_at.is_(None))
    )
    occupied = {row.Checkin.slot_number: row.code for row in checkins_result.all()}

    blocks_result = await db.execute(
        select(SlotBlock).where(
            SlotBlock.rack_id == rack.id, SlotBlock.released_at.is_(None)
        )
    )
    blocked = {b.slot_number: b.reason for b in blocks_result.scalars().all()}

    states: List[SlotState] = []
    for slot in range(1, rack.slots + 1):
        if slot in occupied:
            states.append(SlotState(slot_number=slot, status="checked_in", token_code=occupied[slot]))
        elif slot in blocked:
            states.append(SlotState(slot_number=slot, status="blocked", block_reason=blocked[slot]))
        else:
            states.append(SlotState(slot_number=slot, status="free"))
    return states


@router.get("/events/{event_id}/racks", response_model=List[RackRead])
async def list_event_racks(
    event_id: UUID,
    operator: Operator = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
):
    """List all racks for an event."""
    result = await db.execute(
        select(Rack).where(Rack.event_id == event_id).order_by(Rack.rack_number)
    )
    return result.scalars().all()


@router.get("/events/{event_id}/racks/detail", response_model=List[RackDetail])
async def list_event_racks_detail(
    event_id: UUID,
    operator: Operator = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
):
    """List racks with per-slot state (free / checked_in / blocked)."""
    result = await db.execute(
        select(Rack).where(Rack.event_id == event_id).order_by(Rack.rack_number)
    )
    racks = result.scalars().all()
    return [
        RackDetail(
            id=r.id,
            event_id=r.event_id,
            rack_number=r.rack_number,
            label=r.label,
            slots=r.slots,
            states=await _rack_states(db, r),
        )
        for r in racks
    ]


@router.post(
    "/events/{event_id}/racks",
    response_model=RackRead,
    status_code=status.HTTP_201_CREATED,
)
async def admin_create_rack(
    event_id: UUID,
    data: RackCreate,
    admin: Operator = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    event_result = await db.execute(select(Event).where(Event.id == event_id))
    if not event_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Event not found")

    clash = await db.execute(
        select(Rack).where(
            Rack.event_id == event_id, Rack.rack_number == data.rack_number
        )
    )
    if clash.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail="rack_number already used on this event"
        )

    rack = Rack(event_id=event_id, **data.model_dump())
    db.add(rack)
    await db.flush()
    await db.refresh(rack)
    return rack


@router.patch("/racks/{rack_id}", response_model=RackRead)
async def admin_update_rack(
    rack_id: UUID,
    data: RackUpdate,
    admin: Operator = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Rack).where(Rack.id == rack_id))
    rack = result.scalar_one_or_none()
    if not rack:
        raise HTTPException(status_code=404, detail="Rack not found")

    updates = data.model_dump(exclude_unset=True)
    if "rack_number" in updates and updates["rack_number"] != rack.rack_number:
        clash = await db.execute(
            select(Rack).where(
                Rack.event_id == rack.event_id,
                Rack.rack_number == updates["rack_number"],
                Rack.id != rack_id,
            )
        )
        if clash.scalar_one_or_none():
            raise HTTPException(
                status_code=400, detail="rack_number already used on this event"
            )

    for key, value in updates.items():
        setattr(rack, key, value)

    await db.flush()
    await db.refresh(rack)
    return rack


@router.delete("/racks/{rack_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_rack(
    rack_id: UUID,
    admin: Operator = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Rack).where(Rack.id == rack_id))
    rack = result.scalar_one_or_none()
    if not rack:
        raise HTTPException(status_code=404, detail="Rack not found")

    active = await db.execute(
        select(func.count(Checkin.id)).where(
            Checkin.rack_id == rack_id, Checkin.checked_out_at.is_(None)
        )
    )
    if (active.scalar() or 0) > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete rack with active check-ins",
        )

    await db.delete(rack)
    await db.flush()
    return None


# =============================================
# Slot blocks (any authenticated operator)
# =============================================

@router.post(
    "/racks/{rack_id}/blocks",
    response_model=SlotBlockRead,
    status_code=status.HTTP_201_CREATED,
)
async def block_slot(
    rack_id: UUID,
    data: SlotBlockCreate,
    operator: Operator = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
):
    """Mark a slot as unavailable (not tied to a checkin)."""
    rack_result = await db.execute(select(Rack).where(Rack.id == rack_id))
    rack = rack_result.scalar_one_or_none()
    if not rack:
        raise HTTPException(status_code=404, detail="Rack not found")
    if data.slot_number > rack.slots:
        raise HTTPException(status_code=400, detail="slot_number out of range")

    # Reject if already blocked or checked_in on same slot
    active_block = await db.execute(
        select(SlotBlock).where(
            SlotBlock.rack_id == rack_id,
            SlotBlock.slot_number == data.slot_number,
            SlotBlock.released_at.is_(None),
        )
    )
    if active_block.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Slot already blocked")

    active_checkin = await db.execute(
        select(Checkin).where(
            Checkin.rack_id == rack_id,
            Checkin.slot_number == data.slot_number,
            Checkin.checked_out_at.is_(None),
        )
    )
    if active_checkin.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail="Slot currently holds an active check-in"
        )

    block = SlotBlock(
        rack_id=rack_id,
        slot_number=data.slot_number,
        reason=data.reason,
        created_by=operator.id,
    )
    db.add(block)
    await db.flush()
    await db.refresh(block)
    return block


@router.delete(
    "/racks/{rack_id}/blocks/{slot_number}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def release_slot(
    rack_id: UUID,
    slot_number: int,
    operator: Operator = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
):
    """Release an active block on a slot."""
    result = await db.execute(
        select(SlotBlock).where(
            SlotBlock.rack_id == rack_id,
            SlotBlock.slot_number == slot_number,
            SlotBlock.released_at.is_(None),
        )
    )
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(status_code=404, detail="No active block for this slot")

    block.released_at = datetime.now(timezone.utc)
    block.released_by = operator.id
    await db.flush()
    return None
