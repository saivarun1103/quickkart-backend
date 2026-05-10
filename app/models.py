from app.db import Base
from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timedelta, timezone

class User(Base):
    __tablename__ = "users"

    phone = Column(String, primary_key=True, index=True)
    last_message_time = Column(DateTime)
    state = Column(String, default=None)
    created_at = Column(DateTime, default=datetime.now)
    customer_name = Column(String, default=None)
    pending_order = Column(Text)

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String)
    customer_name = Column(String)
    items = Column(JSONB)
    total_price = Column(Integer)
    pickup_pin = Column(String,unique=True)
    status = Column(String, default="pending")
    payment_status = Column(String, default="pending")
    payment_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    business_id = Column(
        Integer,
        ForeignKey("businesses.id"),
        nullable=False
    )

class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    price = Column(Integer)
    image_url = Column(String)
    available = Column(Boolean, default=True)   # ✅ NEW
    business_id = Column(
        Integer,
        ForeignKey("businesses.id")
    )
    category = Column(String(50))
    dietary_type = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(
        Boolean,
        default=True
    )

class Business(Base):
    __tablename__ = "businesses"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    business_phone = Column(String)
    business_type = Column(String)
    slug = Column(String, unique=True)
    logo_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    owner_name = Column(String)
    email = Column(String, unique=True)
    password_hash = Column(String)

class Payment(Base):
    __tablename__ = "payments"
    id = Column(
        Integer,
        primary_key=True,
        index=True
    )
    order_id = Column(
        Integer,
        ForeignKey("orders.id"),
        unique=True,
        nullable=True
    )
    business_id = Column(
        Integer,
        ForeignKey("businesses.id")
    )
    phone = Column(String)
    customer_name = Column(String)
    razorpay_payment_id = Column(
        String,
        unique=True
    )
    razorpay_payment_link_id = Column(
        String
    )
    amount = Column(Integer)
    currency = Column(
        String,
        default="INR"
    )
    status = Column(String)
    payment_method = Column(String)
    paid_at = Column(DateTime)
    created_at = Column(
        DateTime,
        default=datetime.now
    )

##MenuSessions
class MenuSession(Base):
    __tablename__ = "menu_sessions"
    id = Column(
        Integer,
        primary_key=True,
        index=True
    )
    session_token = Column(
        String,
        unique=True,
        nullable=False
    )
    phone = Column(
        String,
        nullable=False
    )
    business_id = Column(
        Integer,
        ForeignKey("businesses.id")
    )
    expires_at = Column(
        DateTime(timezone=True)
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda:
            datetime.now(timezone.utc)
    )
    is_active = Column(
        Boolean,
        default=True
    )
    last_used_at = Column(
        DateTime(timezone=True),
        default=lambda:
            datetime.now(timezone.utc)
    )