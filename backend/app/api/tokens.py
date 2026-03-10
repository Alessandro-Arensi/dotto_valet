"""
Dottò - Tokens API
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import get_db
from app.models.checkin import Checkin
from app.models.token import Token
from app.schemas.token import (
    TokenBasicInfo,
    TokenCheckinInfo,
    TokenEventInfo,
    TokenInfo,
)
from app.services.token_service import normalize_phone

settings = get_settings()
router = APIRouter()


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

    # Event info
    event_info = None
    if token.event:
        event_info = TokenEventInfo(
            name=token.event.name,
            location=token.event.location,
            date=token.event.start_date,
        )

    # Checkin info
    checkin_info = None
    if token.checkin:
        position = f"Rastrelliera {token.checkin.rack.rack_number}"
        if token.checkin.rack.label:
            position = token.checkin.rack.label
        position += f", Slot {token.checkin.slot_number}"

        checkin_info = TokenCheckinInfo(
            position=position,
            checked_in_at=token.checkin.checked_in_at,
            photo_url=token.checkin.bike_photo_url,
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


@router.get("/recover")
async def recover_token(
    phone: str = Query(..., description="Customer phone number"),
    event_id: UUID | None = Query(None, description="Event ID (optional)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Recover a digital token by phone number.
    Used when customer loses QR code.
    """
    phone_normalized = normalize_phone(phone)

    # Build query
    query = (
        select(Token)
        .join(Token.customer)
        .options(selectinload(Token.event))
        .where(
            Token.customer.has(phone_normalized=phone_normalized),
            Token.type == "digital",
            Token.status.in_(["reserved", "checked_in"]),
        )
    )

    if event_id:
        query = query.where(Token.event_id == event_id)

    result = await db.execute(query)
    tokens = result.scalars().all()

    if not tokens:
        raise HTTPException(
            status_code=404, detail="No active token found for this phone number"
        )

    # Return all active tokens (usually just one)
    return {
        "success": True,
        "tokens": [
            {
                "code": t.code,
                "qr_url": f"{settings.app_url}/t/{t.code}",
                "status": t.status,
                "event_name": t.event.name if t.event else None,
            }
            for t in tokens
        ],
        "message": (
            "QR reinviato via SMS"
            if len(tokens) == 1
            else f"Trovati {len(tokens)} token attivi"
        ),
    }


@router.get("/{code}/wallet")
async def get_wallet_pass(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get Google Wallet pass URL for a token.
    Il pass include il posto/rastrelliera se già assegnato (walk-in o dopo check-in).
    Riaprendo questo link dopo il check-in si ottiene la carta aggiornata con il posto.
    """
    from app.services.wallet import generate_wallet_pass_url, get_wallet_instructions

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

    if not token.event:
        raise HTTPException(
            status_code=400, detail="Token not associated with an event"
        )

    qr_url = f"{settings.app_url}/t/{token.code}"
    event_date = token.event.start_date.strftime("%d/%m/%Y")

    position = None
    if token.checkin and token.checkin.rack:
        r = token.checkin.rack
        position = (
            r.label or f"Rastrelliera {r.rack_number}"
        ) + f", Slot {token.checkin.slot_number}"

    wallet_url = await generate_wallet_pass_url(
        token_code=token.code,
        event_name=token.event.name,
        event_location=token.event.location,
        event_date=event_date,
        qr_url=qr_url,
        position=position,
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
