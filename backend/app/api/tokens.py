"""
Dottò - Tokens API
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import get_db
from app.models.token import Token
from app.models.customer import Customer
from app.models.checkin import Checkin
from app.models.event import Event
from app.schemas.token import TokenInfo, TokenBasicInfo, TokenEventInfo, TokenCheckinInfo
from app.services.token_service import normalize_phone, mask_phone
from app.services.sms import send_token_recovery_sms

settings = get_settings()
router = APIRouter()


# NOTE: /recover is declared BEFORE /{code} so it isn't shadowed by path param matching.
@router.get("/recover")
async def recover_token(
    phone: Optional[str] = Query(None, description="Customer phone (legacy / future SMS)"),
    first_name: Optional[str] = Query(None, description="Customer first name"),
    last_name: Optional[str] = Query(None, description="Customer last name"),
    event_id: Optional[UUID] = Query(None, description="Event ID (optional)"),
    db: AsyncSession = Depends(get_db),
):
    """Recover active digital tokens by phone OR by name.

    At least one of `phone`, `first_name`, `last_name` must be provided.
    Name matches are case-insensitive substring matches — operator picks
    the correct row from the returned list when multiple customers share a name.
    """
    if not any([phone, first_name, last_name]):
        raise HTTPException(
            status_code=400,
            detail="Provide phone, first_name or last_name",
        )

    query = (
        select(Token)
        .join(Token.customer)
        .options(
            selectinload(Token.event),
            selectinload(Token.customer),
            selectinload(Token.checkin).selectinload(Checkin.rack),
        )
        .where(
            Token.type == "digital",
            Token.status.in_(["reserved", "checked_in"]),
        )
    )

    if phone:
        phone_normalized = normalize_phone(phone)
        query = query.where(Token.customer.has(phone_normalized=phone_normalized))
    if first_name:
        query = query.where(Customer.first_name.ilike(f"%{first_name.strip()}%"))
    if last_name:
        query = query.where(Customer.last_name.ilike(f"%{last_name.strip()}%"))
    if event_id:
        query = query.where(Token.event_id == event_id)

    result = await db.execute(query)
    tokens = result.scalars().all()

    if not tokens:
        raise HTTPException(status_code=404, detail="No active token found")

    message_sent = False
    if phone and len(tokens) == 1:
        token = tokens[0]
        qr_url = f"{settings.app_url}/t/{token.code}"
        message_sent = await send_token_recovery_sms(
            phone=normalize_phone(phone),
            token_code=token.code,
            qr_url=qr_url,
        )

    def serialize(t: Token) -> dict:
        position = None
        checked_in_at = None
        if t.checkin:
            rack = t.checkin.rack
            label = rack.label or f"Rastrelliera {rack.rack_number}"
            position = {
                "rack_number": rack.rack_number,
                "rack_label": rack.label,
                "slot_number": t.checkin.slot_number,
                "display": f"{label}, Slot {t.checkin.slot_number}",
            }
            checked_in_at = t.checkin.checked_in_at.isoformat()

        customer_name = None
        phone_masked = None
        if t.customer:
            customer_name = (
                f"{t.customer.first_name or ''} {t.customer.last_name or ''}".strip()
                or None
            )
            phone_masked = mask_phone(t.customer.phone_normalized)

        return {
            "code": t.code,
            "qr_url": f"{settings.app_url}/t/{t.code}",
            "status": t.status,
            "event_name": t.event.name if t.event else None,
            "customer_name": customer_name,
            "phone_masked": phone_masked,
            "checked_in_at": checked_in_at,
            "position": position,
        }

    return {
        "success": True,
        "tokens": [serialize(t) for t in tokens],
        "message_sent": message_sent,
        "message": (
            "QR reinviato via SMS" if message_sent
            else f"Trovati {len(tokens)} token attivi"
        ),
    }


@router.get("/{code}", response_model=TokenInfo)
async def get_token_info(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get token info (public endpoint for QR page).
    """
    result = await db.execute(
        select(Token)
        .options(
            selectinload(Token.event),
            selectinload(Token.checkin).selectinload(Checkin.rack),
        )
        .where(Token.code == code.upper())
    )
    token = result.scalar_one_or_none()

    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    event_info = None
    if token.event:
        event_info = TokenEventInfo(
            name=token.event.name,
            location=token.event.location,
            date=token.event.start_date,
        )

    checkin_info = None
    if token.checkin:
        position = f"Rastrelliera {token.checkin.rack.rack_number}"
        if token.checkin.rack.label:
            position = token.checkin.rack.label
        position += f", Slot {token.checkin.slot_number}"

        checkin_info = TokenCheckinInfo(
            position=position,
            checked_in_at=token.checkin.checked_in_at,
            bike_description=token.checkin.bike_description,
        )

    return TokenInfo(
        token=TokenBasicInfo(
            code=token.code,
            status=token.status,
            type=token.type,
        ),
        event=event_info,
        checkin=checkin_info,
    )


@router.get("/{code}/wallet")
async def get_wallet_pass(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get Google Wallet pass URL for a token.
    """
    from app.services.wallet import generate_wallet_pass_url, get_wallet_instructions

    result = await db.execute(
        select(Token)
        .options(selectinload(Token.event))
        .where(Token.code == code.upper())
    )
    token = result.scalar_one_or_none()

    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    if not token.event:
        raise HTTPException(status_code=400, detail="Token not associated with an event")

    qr_url = f"{settings.app_url}/t/{token.code}"
    event_date = token.event.start_date.strftime("%d/%m/%Y")

    wallet_url = await generate_wallet_pass_url(
        token_code=token.code,
        event_name=token.event.name,
        event_location=token.event.location,
        event_date=event_date,
        qr_url=qr_url,
    )

    if wallet_url:
        return {
            "success": True,
            "wallet_url": wallet_url,
        }
    else:
        return {
            "success": False,
            "message": "Google Wallet integration not configured",
            "setup": get_wallet_instructions(),
        }
