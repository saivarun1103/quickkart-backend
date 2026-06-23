from fastapi import FastAPI, Request, HTTPException, Depends
from app.webhook import router
from app.routes import payment, public, business_settings, founder
from contextlib import asynccontextmanager
from app.db import engine, get_db
from app.models import Base, MenuItem, Business, User, MenuSession, PushToken
from fastapi.middleware.cors import CORSMiddleware
from app.admin import router as admin_router
from app.schemas import LoginRequest, RegisterRequest
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    normalize_phone,
)
from app.dependencies import get_current_business
from app.services.razorpay_service import create_payment_link
from pydantic import BaseModel
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text


# database
@asynccontextmanager
async def lifespan(app: FastAPI):

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS role VARCHAR NOT NULL DEFAULT 'MERCHANT'"))
        await conn.execute(text("UPDATE businesses SET role = 'FOUNDER' WHERE email = 'varun.1103@gmail.com'"))

    yield


app = FastAPI(lifespan=lifespan)
app.include_router(public.router)
app.include_router(router)
app.include_router(admin_router)
app.include_router(payment.router, prefix="/api")
app.include_router(business_settings.router)
app.include_router(founder.router)

origins = [
    # "http://localhost:5173",
    # "https://collins-powered-darleen.ngrok-free.dev",  # your frontend URL
    # "https://collins-powered-darleen.ngrok-free.dev",
    # "https://quickkart-3f8h.onrender.com/api/business",
    "http://localhost:5173",
    # "http://localhost:8000",
    # "http://192.168.0.106:5173",
    # "http://192.168.0.106:8000",
    # "https://quickkart-frontend-beta.vercel.app",
    "https://goskipdq.com",
    "https://www.goskipdq.com",
]

app.add_middleware(
    CORSMiddleware,
    # allow_origins=["https://quickkart-frontend-beta.vercel.app"],
    allow_origins=origins,
    # allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SaveCustomerNameRequest(BaseModel):
    session_token: str
    customer_name: str


class CheckPhoneRequest(BaseModel):
    phone: str


class CheckoutRequest(BaseModel):
    session_token: str | None = None
    business_slug: str | None = None
    phone: str | None = None
    customer_name: str | None = None
    items: dict


##Menu page
from sqlalchemy import select


@app.get("/api/menu/{slug}")
async def get_menu(slug: str, db: AsyncSession = Depends(get_db)):

    result = await db.execute(select(Business).where(Business.slug == slug))

    business = result.scalar_one_or_none()

    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    result = await db.execute(
        select(MenuItem).where(
            MenuItem.business_id == business.id, MenuItem.is_active == True
        )
    )

    items = result.scalars().all()

    return {
        "business": {
            "id": business.id,
            "name": business.name,
            "logo_url": business.logo_url,
            "banner_url": business.banner_url,
            "slug": business.slug,
            "status": business.status,
        },
        "items": [
            {
                "id": item.id,
                "name": item.name,
                "price": item.price,
                "image": item.image_url,
                "available": item.available,
                "category": item.category,
                "dietary_type": item.dietary_type,
                "description": item.description,
            }
            for item in items
        ],
    }


@app.get("/api/business")
def get_business(business: Business = Depends(get_current_business)):
    return {
        "id": business.id,
        "name": business.name,
        "logo_url": business.logo_url,
        "email": business.email,
        "business_phone": business.business_phone,
        "business_type": business.business_type,
        "slug": business.slug,
        "location_name": business.location_name,
        "role": business.role,
    }


# @app.get("/menu")
# def menu_page(request: Request, db: Session = Depends(get_db)):
#     items = db.query(MenuItem).filter(
#         MenuItem.is_active == True
#     ).all()

#     return templates.TemplateResponse(
#         request,
#         "menu.html",
#         {"request": request, "items": items}
#     )


##register endpoint
@app.post("/api/register")
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):

    result = await db.execute(select(Business).where(Business.email == data.email))

    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = hash_password(data.password)

    slug = data.business_name.lower().replace(" ", "-")

    role = "FOUNDER" if data.email.strip().lower() == "varun.1103@gmail.com" else "MERCHANT"

    business = Business(
        name=data.business_name,
        owner_name=data.owner_name,
        email=data.email,
        business_phone=normalize_phone(data.business_phone),
        business_type=data.business_type,
        password_hash=hashed_password,
        slug=slug,
        role=role,
        location_name=data.location_name,
        latitude=data.latitude,
        longitude=data.longitude,
        contact_number=normalize_phone(data.contact_number) if data.contact_number else None,
    )

    db.add(business)

    await db.commit()

    await db.refresh(business)

    return {"message": "Business registered successfully"}


@app.post("/api/login")
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):

    # 🔍 Get input
    identifier = data.identifier.strip()

    # 📞 Normalize phone
    normalized_phone = normalize_phone(identifier)

    # 🔍 Find business
    result = await db.execute(
        select(Business).where(
            (Business.email == identifier)
            | (Business.business_phone == normalized_phone)
        )
    )

    business = result.scalar_one_or_none()

    # ❌ Invalid user
    if not business:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 🔒 Verify password
    valid_password = verify_password(data.password, business.password_hash)

    if not valid_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 🎟️ Create JWT
    token = create_access_token({"business_id": business.id, "email": business.email})

    return {"access_token": token, "token_type": "bearer"}


@app.get("/api/session/{session_token}")
async def get_session_data(session_token: str, db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(MenuSession).where(
            MenuSession.session_token == session_token, MenuSession.is_active == True
        )
    )

    menu_session = result.scalar_one_or_none()

    if not menu_session:
        raise HTTPException(status_code=404, detail="Session not found")

    expires_at = menu_session.expires_at

    if expires_at is None:
        raise HTTPException(status_code=400, detail="Invalid session expiry")

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)

    if expires_at.timestamp() < now.timestamp():
        menu_session.is_active = False

        await db.commit()

        raise HTTPException(status_code=401, detail="Session expired")

    result = await db.execute(
        select(Business).where(Business.id == menu_session.business_id)
    )

    business = result.scalar_one_or_none()

    return {"business_slug": business.slug, "business_phone": business.business_phone}


@app.get("/test")
async def test():

    return {"message": "working"}


@app.post("/api/checkout")
async def checkout(data: CheckoutRequest, db: AsyncSession = Depends(get_db)):

    # -------------------------
    # SESSION CHECKOUT
    # -------------------------

    if data.session_token:
        result = await db.execute(
            select(MenuSession).where(MenuSession.session_token == data.session_token)
        )

        menu_session = result.scalar_one_or_none()

        if not menu_session:
            raise HTTPException(status_code=404, detail="Invalid session")

        now = datetime.now(timezone.utc)

        expires_at = menu_session.expires_at

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < now:
            raise HTTPException(status_code=400, detail="Session expired")

        phone = menu_session.phone

        result = await db.execute(
            select(Business).where(Business.id == menu_session.business_id)
        )

        business = result.scalar_one_or_none()

        result = await db.execute(select(User).where(User.phone == phone))

        user = result.scalar_one_or_none()

    # -------------------------
    # PUBLIC CHECKOUT
    # -------------------------

    else:
        if not data.business_slug:
            raise HTTPException(status_code=400, detail="Business slug required")

        if not data.phone:
            raise HTTPException(status_code=400, detail="Phone required")

        # normalize phone
        phone = data.phone.strip()
        phone = phone.replace(" ", "")

        if len(phone) == 10:
            phone = "91" + phone

        result = await db.execute(
            select(Business).where(Business.slug == data.business_slug)
        )

        business = result.scalar_one_or_none()

        if not business:
            raise HTTPException(status_code=404, detail="Business not found")

        result = await db.execute(select(User).where(User.phone == phone))

        user = result.scalar_one_or_none()

        # create customer only if needed
        if not user:
            if not data.customer_name:
                raise HTTPException(status_code=400, detail="Customer name required")

            user = User(phone=phone, customer_name=data.customer_name)

            db.add(user)

            await db.commit()

            await db.refresh(user)

    total = 0

    for item_name, qty in data.items.items():
        result = await db.execute(
            select(MenuItem).where(
                MenuItem.name == item_name, MenuItem.business_id == business.id
            )
        )

        menu_item = result.scalar_one_or_none()

        if menu_item:
            total += float(menu_item.price) * qty

    import json

    user.pending_order = json.dumps(
        {
            "items": data.items,
            "total_price": str(total),
            "business_id": int(business.id),
        }
    )

    await db.commit()

    payment_link = create_payment_link(
        amount=total, phone=phone, customer_name=user.customer_name
    )

    return {"payment_url": payment_link["short_url"]}


@app.get("/api/check-customer/{session_token}")
async def check_customer(session_token: str, db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(MenuSession).where(MenuSession.session_token == session_token)
    )

    menu_session = result.scalar_one_or_none()

    if not menu_session:
        return {"has_name": False}

    result = await db.execute(select(User).where(User.phone == menu_session.phone))

    user = result.scalar_one_or_none()

    if not user:
        return {"has_name": False}

    return {"has_name": bool(user.customer_name)}


@app.post("/api/save-customer-name")
async def save_customer_name(
    request: SaveCustomerNameRequest, db: AsyncSession = Depends(get_db)
):

    result = await db.execute(
        select(MenuSession).where(MenuSession.session_token == request.session_token)
    )

    menu_session = result.scalar_one_or_none()

    if not menu_session:
        return {"success": False}

    result = await db.execute(select(User).where(User.phone == menu_session.phone))

    user = result.scalar_one_or_none()

    if not user:
        return {"success": False}

    user.customer_name = request.customer_name

    await db.commit()

    return {"success": True}


@app.post("/api/check-phone")
async def check_phone(data: CheckPhoneRequest, db: AsyncSession = Depends(get_db)):

    phone = data.phone.strip()
    phone = phone.replace(" ", "")

    if len(phone) == 10:
        phone = "91" + phone

    result = await db.execute(select(User).where(User.phone == phone))

    user = result.scalar_one_or_none()

    if user:
        return {"exists": True, "customer_name": user.customer_name}

    return {"exists": False}


class PushTokenRequest(BaseModel):
    token: str


@app.post("/api/admin/push-token")
async def register_push_token(
    data: PushTokenRequest,
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    result = await db.execute(select(PushToken).where(PushToken.token == data.token))
    existing_token = result.scalar_one_or_none()

    if existing_token:
        existing_token.business_id = business.id
    else:
        new_token = PushToken(business_id=business.id, token=data.token)
        db.add(new_token)

    await db.commit()
    return {"success": True, "message": "Push token registered successfully"}
