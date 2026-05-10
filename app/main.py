from fastapi import FastAPI, Request, HTTPException, Depends
from app.webhook import router

from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from app.db import engine, SessionLocal
from app.models import Base, MenuItem, Business, User, MenuSession
from fastapi.middleware.cors import CORSMiddleware
from app.admin import router as admin_router
from fastapi.responses import FileResponse
from app.schemas import LoginRequest, RegisterRequest
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    normalize_phone
)
from app.dependencies import get_current_business
from app.services.razorpay_service import create_payment_link
from pydantic import BaseModel
from datetime import datetime, timezone
from sqlalchemy.orm import Session
import os

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

#database
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ✅ Startup logic
    Base.metadata.create_all(bind=engine)
    yield
    # (optional) shutdown logic

app = FastAPI(lifespan=lifespan)

app.include_router(router)
app.include_router(admin_router) 
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# origins = [
#     # "http://localhost:5173",
#     # "https://collins-powered-darleen.ngrok-free.dev",  # your frontend URL
#     # "https://quickkart-3f8h.onrender.com/api/business",
# ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SaveCustomerNameRequest(BaseModel):
    session_token: str
    customer_name: str

class CheckoutRequest(BaseModel):
    session_token: str
    items: dict

##Menu page
@app.get("/api/menu/{slug}")
def get_menu(slug: str,db: Session = Depends(get_db)):
    business = db.query(Business).filter(
        Business.slug == slug
    ).first()

    if not business:
        raise HTTPException(
            status_code=404,
            detail="Business not found"
        )

    items = db.query(MenuItem).filter(
        MenuItem.business_id == business.id,
        MenuItem.is_active == True
    ).all()

    return {
        "business": {
            "name": business.name,
            "logo_url": business.logo_url,
            "slug": business.slug
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
        ]
    }

@app.get("/api/business")
def get_business(
    business: Business = Depends(
        get_current_business
    )
):
    return {
        "id": business.id,

        "name": business.name,

        "logo_url": business.logo_url,

        "email": business.email,

        "business_phone":
            business.business_phone,

        "business_type":
            business.business_type,

        "slug": business.slug
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
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    # 🔍 Check existing email
    existing = db.query(Business).filter(
        Business.email == data.email
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    # 🔒 Hash password
    hashed_password = hash_password(
        data.password
    )

    # 🔗 Create slug
    slug = data.business_name.lower().replace(" ", "-")

    # 🏪 Create business
    business = Business(
        name=data.business_name,
        owner_name=data.owner_name,
        email=data.email,
        business_phone=normalize_phone(
            data.business_phone
        ),
        business_type=data.business_type,
        password_hash=hashed_password,
        slug=slug
    )

    db.add(business)

    db.commit()

    db.refresh(business)

    return {
        "message": "Business registered successfully"
    }

@app.post("/api/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):

    # 🔍 Get input
    identifier = data.identifier.strip()

    # 📞 Normalize phone
    normalized_phone = normalize_phone(
        identifier
    )

    # 🔍 Find business
    business = db.query(Business).filter(
        (Business.email == identifier) |
        (Business.business_phone == normalized_phone)
    ).first()

    # ❌ Invalid user
    if not business:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    # 🔒 Verify password
    valid_password = verify_password(
        data.password,
        business.password_hash
    )

    

    if not valid_password:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    # 🎟️ Create JWT
    token = create_access_token({
        "business_id": business.id,
        "email": business.email
    })

    return {
        "access_token": token,
        "token_type": "bearer"
    }

# app.mount(
#     "/logos",
#     StaticFiles(directory="frontend/dist/logos"),
#     name="logos"
# )

# app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")

# @app.get("/")
# async def serve_root():
#     return FileResponse("frontend/dist/index.html")

@app.get("/api/session/{session_token}")
def get_session_data(
    session_token: str,
    db: Session = Depends(get_db)
):

    menu_session = db.query(MenuSession).filter(
        MenuSession.session_token == session_token
    ).first()

    if not menu_session:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    expires_at = menu_session.expires_at

    print("RAW EXPIRES:", expires_at)
    print("TYPE:", type(expires_at))

    # ✅ convert safely
    if expires_at is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid session expiry"
        )

    # ✅ make timezone aware if needed
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(
            tzinfo=timezone.utc
        )

    now = datetime.now(timezone.utc)

    print("NOW:", now)
    print("EXPIRES:", expires_at)

    # ✅ compare timestamps directly
    if expires_at.timestamp() < now.timestamp():

        menu_session.is_active = False
        db.commit()

        raise HTTPException(
            status_code=401,
            detail="Session expired"
        )

    business = db.query(Business).filter(
        Business.id == menu_session.business_id
    ).first()

    return {
        "business_slug": business.slug,
        "business_phone": business.business_phone
    }

@app.get("/test")
async def test():

    return {
        "message": "working"
    }

@app.post("/api/checkout")
def checkout(data: CheckoutRequest, db: Session = Depends(get_db)):

    menu_session = db.query(MenuSession).filter(

        MenuSession.session_token
        == data.session_token

    ).first()

    if not menu_session:

        raise HTTPException(
            status_code=404,
            detail="Invalid session"
        )

    now = datetime.now(timezone.utc)

    expires_at = menu_session.expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    else:
        expires_at = expires_at.astimezone(timezone.utc)

    if expires_at < now:
        raise HTTPException(
            status_code=400,
            detail="Session expired"
        )

    phone = menu_session.phone

    business = db.query(Business).filter(

        Business.id ==
        menu_session.business_id

    ).first()

    user = db.query(User).filter(
        User.phone == phone
    ).first()

    total = 0

    for item_name, qty in data.items.items():

        menu_item = db.query(MenuItem).filter(
            MenuItem.name == item_name,
            MenuItem.business_id == business.id
        ).first()

        if menu_item:
            total += float(menu_item.price) * qty

    import json

    user.pending_order = json.dumps({
        "items": data.items,
        "total_price": str(total),
        "business_id": int(business.id)
    })

    db.commit()

    payment_link = create_payment_link(
        amount=total,
        phone=phone,
        customer_name=user.customer_name
    )

    return {
        "payment_url": payment_link[
            "short_url"
        ]
    }

@app.get("/{business_slug}/m/{session_token}")
def menu_session_redirect(

    session_token: str
):

    return FileResponse(
        "frontend/dist/index.html"
    )

@app.get(
    "/api/check-customer/{session_token}"
)
def check_customer(
    session_token: str,
    db: Session = Depends(get_db)
):

    menu_session = db.query(MenuSession).filter(
        MenuSession.session_token == session_token
    ).first()

    if not menu_session:

        return {
            "has_name": False
        }

    user = db.query(User).filter(
        User.phone == menu_session.phone
    ).first()

    if not user:

        return {
            "has_name": False
        }

    return {
        "has_name": bool(user.customer_name)
    }

@app.post("/api/save-customer-name")
def save_customer_name(
    request: SaveCustomerNameRequest,
    db: Session = Depends(get_db)
):

    menu_session = db.query(MenuSession).filter(
        MenuSession.session_token
        == request.session_token
    ).first()

    if not menu_session:

        return {
            "success": False
        }

    user = db.query(User).filter(
        User.phone == menu_session.phone
    ).first()

    if not user:

        return {
            "success": False
        }

    user.customer_name = request.customer_name

    db.commit()

    return {
        "success": True
    }

# @app.get("/{full_path:path}")
# async def serve_react(full_path: str):

#     # only block API routes
#     if full_path.startswith("api"):
#         raise HTTPException(status_code=404)

#     return FileResponse("frontend/dist/index.html")