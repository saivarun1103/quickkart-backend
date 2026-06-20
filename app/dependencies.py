from fastapi import (
    Header,
    HTTPException,
    Depends
)

from app.auth import decode_token
from app.db import get_db
from app.models import Business

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession
)


async def get_current_business(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db)
):

    # ❌ Missing header
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing authorization header"
        )

    # ❌ Invalid format
    if not authorization.startswith(
        "Bearer "
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization format"
        )

    # ✅ Extract token
    token = authorization.replace(
        "Bearer ",
        ""
    )

    # ✅ Decode JWT
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    business_id = payload.get(
        "business_id"
    )

    if not business_id:
        raise HTTPException(
            status_code=401,
            detail="Missing business_id"
        )

    result = await db.execute(
        select(Business).where(
            Business.id == business_id
        )
    )

    business = (
        result.scalar_one_or_none()
    )


    if not business:
        raise HTTPException(
            status_code=401,
            detail="Business not found"
        )

    return business


async def get_current_founder(
    business: Business = Depends(get_current_business)
):
    if business.role != "FOUNDER":
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )
    return business