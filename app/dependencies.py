from fastapi import (
    Header,
    HTTPException,
    Depends
)

from app.auth import decode_token

from app.db import SessionLocal

from app.models import Business

from sqlalchemy.orm import Session

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_business(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
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

    business = db.query(Business).filter(
        Business.id == business_id
    ).first()

    if not business:
        raise HTTPException(
            status_code=401,
            detail="Business not found"
        )

    return business