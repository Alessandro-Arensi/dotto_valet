"""
Dottò - Operators Admin API
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.operator import Operator
from app.schemas.operator import OperatorCreate, OperatorUpdate, OperatorRead
from app.services.auth import get_current_admin, hash_pin
from app.services.token_service import normalize_phone

router = APIRouter()


@router.get("", response_model=List[OperatorRead])
async def admin_list_operators(
    admin: Operator = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all operators (admin only)."""
    result = await db.execute(select(Operator).order_by(Operator.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=OperatorRead, status_code=status.HTTP_201_CREATED)
async def admin_create_operator(
    data: OperatorCreate,
    admin: Operator = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create an operator (admin only)."""
    normalized = normalize_phone(data.phone)

    existing = await db.execute(select(Operator).where(Operator.phone == normalized))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail="Phone already registered to an operator"
        )

    op = Operator(
        name=data.name,
        phone=normalized,
        email=data.email,
        pin_hash=hash_pin(data.pin),
        is_admin=data.is_admin,
        is_active=data.is_active,
    )
    db.add(op)
    await db.flush()
    await db.refresh(op)
    return op


@router.patch("/{operator_id}", response_model=OperatorRead)
async def admin_update_operator(
    operator_id: UUID,
    data: OperatorUpdate,
    admin: Operator = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update operator (admin only). Supports PIN reset, role & status toggle."""
    result = await db.execute(select(Operator).where(Operator.id == operator_id))
    op = result.scalar_one_or_none()
    if not op:
        raise HTTPException(status_code=404, detail="Operator not found")

    updates = data.model_dump(exclude_unset=True)

    if "phone" in updates and updates["phone"]:
        updates["phone"] = normalize_phone(updates["phone"])
        clash = await db.execute(
            select(Operator).where(
                Operator.phone == updates["phone"], Operator.id != operator_id
            )
        )
        if clash.scalar_one_or_none():
            raise HTTPException(
                status_code=400, detail="Phone already registered to another operator"
            )

    if "pin" in updates and updates["pin"]:
        op.pin_hash = hash_pin(updates["pin"])
    updates.pop("pin", None)

    for key, value in updates.items():
        setattr(op, key, value)

    await db.flush()
    await db.refresh(op)
    return op


@router.delete("/{operator_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_operator(
    operator_id: UUID,
    admin: Operator = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete operator by deactivating (admin only). Prevents self-lockout."""
    if operator_id == admin.id:
        raise HTTPException(
            status_code=400, detail="Cannot deactivate your own account"
        )

    result = await db.execute(select(Operator).where(Operator.id == operator_id))
    op = result.scalar_one_or_none()
    if not op:
        raise HTTPException(status_code=404, detail="Operator not found")

    op.is_active = False
    await db.flush()
    return None
