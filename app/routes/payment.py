from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Order, Payment
from app.services.razorpay_service import (
    create_razorpay_order
)
import hmac
import hashlib
from app.config import (
    RAZORPAY_KEY_ID,
    RAZORPAY_KEY_SECRET
)
from app.models import MenuSession, User
from app.services.whatsapp import send_text

router = APIRouter()


@router.post("/create-razorpay-order")
def create_payment_order(
    data: dict,
    db: Session = Depends(get_db)
):

    import random

    # -------------------------
    # GENERATE UNIQUE PIN
    # -------------------------

    while True:

        pin = str(
            random.randint(1000, 9999)
        )

        existing = db.query(Order).filter(
            Order.pickup_pin == pin
        ).first()

        if not existing:
            break

    session = db.query(MenuSession).filter(

        MenuSession.session_token == data["session_token"]

    ).first()

    if not session:

        return {
            "success": False,
            "message": "Invalid session"
        }

    customer_phone = session.phone

    # -------------------------
    # FETCH USER
    # -------------------------

    user = db.query(User).filter(

        User.phone == customer_phone

    ).first()

    customer_name = (

        user.customer_name

        if user and user.customer_name

        else "Customer"
)

    # -------------------------
    # CREATE ORDER FIRST
    # -------------------------

    order = Order(

        phone=customer_phone,

        customer_name=
            customer_name,

        items=data["items"],

        total_price=data["total"],

        pickup_pin=pin,

        status="payment_pending",

        payment_status="pending",

        business_id=data["business_id"],

        session_token=data["session_token"]
    )

    db.add(order)

    db.commit()

    db.refresh(order)

    # -------------------------
    # CREATE RAZORPAY ORDER
    # -------------------------

    razorpay_order = create_razorpay_order(

        amount=data["total"],

        receipt=f"order_{order.id}"
    )

    # -------------------------
    # RETURN DATA
    # -------------------------

    return {

        "success": True,

        "order_id":
            order.id,

        "pickup_pin":
            order.pickup_pin,

        "razorpay_order_id":
            razorpay_order["id"],

        "amount":
            razorpay_order["amount"],

        "key":
            RAZORPAY_KEY_ID
    }


@router.post("/verify-payment")
def verify_payment(
    data: dict,
    db: Session = Depends(get_db)
):

    order = db.query(Order).filter(

        Order.id == data["order_id"]

    ).first()

    if not order:

        return {

            "success": False,

            "message": "Order not found"
        }

    # -------------------------
    # VERIFY SIGNATURE
    # -------------------------

    generated_signature = hmac.new(

        bytes(
            RAZORPAY_KEY_SECRET,
            "utf-8"
        ),

        bytes(

            f"{data['razorpay_order_id']}|"
            f"{data['razorpay_payment_id']}",

            "utf-8"
        ),

        hashlib.sha256

    ).hexdigest()

    if generated_signature != data["razorpay_signature"]:

        return {

            "success": False,

            "message": "Invalid signature"
        }

    # -------------------------
    # UPDATE ORDER
    # -------------------------

    order.status = "pending"

    order.payment_status = "paid"

    # -------------------------
    # SAVE PAYMENT ROW
    # -------------------------

    payment = Payment(

        order_id=order.id,

        business_id=order.business_id,

        phone=order.phone,

        customer_name=order.customer_name,

        razorpay_payment_id=
            data["razorpay_payment_id"],

        amount=order.total_price,

        status="captured",

        payment_method="online"
    )

    db.add(payment)

    # -------------------------
    # End Session
    # -------------------------

    menu_session = db.query(MenuSession).filter(
        MenuSession.session_token == order.session_token
    ).first()

    if menu_session:
        menu_session.is_active = False

    # -------------------------
    # SEND WHATSAPP MESSAGE
    # -------------------------

    send_text(

        order.phone,

        f"✅ Payment successful!\n\n"

        f"🧾 Order #{order.id}\n"

        f"💰 Amount Paid: ₹{order.total_price}\n\n"

        f"🔐 Pickup PIN: {order.pickup_pin}\n\n"

        f"Use this PIN while picking up your order."
    )

    order.payment_id = data[
        "razorpay_payment_id"
    ]

    db.commit()

    return {

        "success": True
    }