"""
Dottò - Authentication API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.operator import Operator
from app.schemas.operator import OperatorLogin, TokenResponse, OperatorBasicInfo
from app.services.auth import verify_pin, create_access_token, get_current_operator
from app.services.token_service import normalize_phone

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: OperatorLogin,
    db: AsyncSession = Depends(get_db),
):
    """
    Login operator with phone and PIN.
    Returns JWT access token.
    """
    phone_normalized = normalize_phone(credentials.phone)
    
    # Find operator by phone
    result = await db.execute(
        select(Operator).where(
            Operator.phone == phone_normalized,
            Operator.is_active == True,
        )
    )
    operator = result.scalar_one_or_none()
    
    # Also try with original phone format
    if not operator:
        result = await db.execute(
            select(Operator).where(
                Operator.phone == credentials.phone,
                Operator.is_active == True,
            )
        )
        operator = result.scalar_one_or_none()
    
    if not operator or not verify_pin(credentials.pin, operator.pin_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone or PIN",
        )
    
    # Create access token
    access_token = create_access_token(operator.id)
    
    return TokenResponse(
        access_token=access_token,
        operator=OperatorBasicInfo(
            id=operator.id,
            name=operator.name,
            is_admin=operator.is_admin,
        ),
    )


@router.get("/me", response_model=OperatorBasicInfo)
async def get_me(
    operator: Operator = Depends(get_current_operator),
):
    """Get current operator info."""
    return OperatorBasicInfo(
        id=operator.id,
        name=operator.name,
        is_admin=operator.is_admin,
    )


