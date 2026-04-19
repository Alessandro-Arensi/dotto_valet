"""
Dottò - Token Service
"""
import random
import string
from typing import Optional
from uuid import UUID

import phonenumbers
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.token import Token
from app.models.customer import Customer


# Characters for token code (excluding confusing ones: 0/O, 1/I/L)
TOKEN_CHARS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generate_token_code() -> str:
    """Generate a unique token code like DOT-XXXX."""
    suffix = "".join(random.choices(TOKEN_CHARS, k=4))
    return f"DOT-{suffix}"


async def get_unique_token_code(db: AsyncSession) -> str:
    """Generate a token code that doesn't exist in the database."""
    for _ in range(10):  # Max 10 attempts
        code = generate_token_code()
        result = await db.execute(
            select(Token).where(Token.code == code)
        )
        if not result.scalar_one_or_none():
            return code
    raise ValueError("Unable to generate unique token code after 10 attempts")


def normalize_phone(phone: str, default_region: str = "IT") -> str:
    """Normalize phone number to E.164 format."""
    try:
        parsed = phonenumbers.parse(phone, default_region)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        pass
    # Fallback: return cleaned number
    return "".join(c for c in phone if c.isdigit() or c == "+")


def mask_phone(phone: Optional[str]) -> Optional[str]:
    """Mask phone number for privacy. Returns None if input is None."""
    if not phone:
        return None
    if len(phone) < 6:
        return phone
    return f"{phone[:4]}****{phone[-3:]}"


async def create_customer(
    db: AsyncSession,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    newsletter_opt_in: bool = False,
) -> Customer:
    """Create a new customer record. MVP does not de-dup; future work may merge duplicates.

    Raises ValueError if neither name nor phone is provided (at least one identifier required).
    """
    if not (first_name or last_name or phone):
        raise ValueError("Customer needs at least a name or a phone")

    phone_normalized = normalize_phone(phone) if phone else None

    customer = Customer(
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        phone_normalized=phone_normalized,
        email=email,
        newsletter_opt_in=newsletter_opt_in,
    )
    db.add(customer)
    await db.flush()
    return customer


async def get_or_create_customer(
    db: AsyncSession,
    phone: str,
    email: Optional[str] = None,
    newsletter_opt_in: bool = False,
) -> Customer:
    """Legacy helper: phone-first identification.

    Kept for operator walk-in flow (CheckinPage) where the operator keys by phone.
    Public reservation + walkin flows use create_customer() directly with name.
    """
    phone_normalized = normalize_phone(phone)

    result = await db.execute(
        select(Customer).where(Customer.phone_normalized == phone_normalized)
    )
    customer = result.scalar_one_or_none()

    if customer:
        if email and not customer.email:
            customer.email = email
            customer.newsletter_opt_in = newsletter_opt_in
        return customer

    customer = Customer(
        phone=phone,
        phone_normalized=phone_normalized,
        email=email,
        newsletter_opt_in=newsletter_opt_in,
    )
    db.add(customer)
    await db.flush()
    return customer


