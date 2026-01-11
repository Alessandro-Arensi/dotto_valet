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


def mask_phone(phone: str) -> str:
    """Mask phone number for privacy."""
    if len(phone) < 6:
        return phone
    # Show first 4 and last 3 digits
    return f"{phone[:4]}****{phone[-3:]}"


async def get_or_create_customer(
    db: AsyncSession,
    phone: str,
    email: Optional[str] = None,
    newsletter_opt_in: bool = False,
) -> Customer:
    """Get existing customer by phone or create new one."""
    phone_normalized = normalize_phone(phone)
    
    result = await db.execute(
        select(Customer).where(Customer.phone_normalized == phone_normalized)
    )
    customer = result.scalar_one_or_none()
    
    if customer:
        # Update email if provided and not set
        if email and not customer.email:
            customer.email = email
            customer.newsletter_opt_in = newsletter_opt_in
        return customer
    
    # Create new customer
    customer = Customer(
        phone=phone,
        phone_normalized=phone_normalized,
        email=email,
        newsletter_opt_in=newsletter_opt_in,
    )
    db.add(customer)
    await db.flush()
    return customer


