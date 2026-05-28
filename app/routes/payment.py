from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import (
    AsyncSession
)

from sqlalchemy import select

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
from app.models import (
    MenuSession,
    User,
    Business
)
from app.services.whatsapp import send_text
import secrets

router = APIRouter()


@router.post(
    "/create-razorpay-order"
)
async def create_payment_order(
    data: dict,
    db: AsyncSession = Depends(
        get_db
    )
):

    import random

    # -------------------------
    # GENERATE UNIQUE PIN
    # -------------------------

    while True:

        pin = str(
            random.randint(
                1000,
                9999
            )
        )

        result = await db.execute(
            select(Order).where(
                Order.pickup_pin
                == pin
            )
        )

        existing = (
            result.scalars()
            .first()
        )

        if not existing:
            break

    # -------------------------
    # SESSION FLOW
    # -------------------------

    if data.get("session_token"):

        result = await db.execute(
            select(MenuSession).where(

                MenuSession.session_token
                == data["session_token"],

                MenuSession.is_active
                == True
            )
        )

        session = (
            result.scalar_one_or_none()
        )

        if not session:

            raise HTTPException(
                status_code=401,
                detail="Session expired"
            )

        customer_phone = (
            session.phone
        )

    # -------------------------
    # PUBLIC FLOW
    # -------------------------

    else:

        if not data.get("phone"):

            raise HTTPException(
                status_code=400,
                detail="Phone required"
            )

        customer_phone = (
            data["phone"]
        )

        # normalize
        customer_phone = (
            customer_phone
            .strip()
            .replace(" ", "")
        )

        if len(customer_phone) == 10:
            customer_phone = (
                "91" + customer_phone
            )

    # -------------------------
    # FETCH USER
    # -------------------------

    result = await db.execute(
        select(User).where(
            User.phone
            == customer_phone
        )
    )

    user = (
        result.scalar_one_or_none()
    )

    # -------------------------
    # CREATE NEW USER
    # -------------------------

    if not user:

        if not data.get(
            "customer_name"
        ):

            raise HTTPException(
                status_code=400,
                detail=
                "Customer name required"
            )

        user = User(

            phone=
                customer_phone,

            customer_name=
                data[
                    "customer_name"
                ]
        )

        db.add(user)

        await db.commit()

        await db.refresh(user)

    customer_name = (

        user.customer_name

        if user and
        user.customer_name

        else data.get(
            "customer_name",
            "Customer"
        )
    )

    # -------------------------
    # CHECK BUSINESS STATUS
    # -------------------------

    result = await db.execute(
        select(Business).where(
            Business.id
            == data["business_id"]
        )
    )

    business = (
        result.scalar_one_or_none()
    )

    if not business:

        raise HTTPException(
            status_code=404,
            detail="Business not found"
        )

    if business.status != "open":

        raise HTTPException(
            status_code=403,

            detail=(
                "Business is currently "
                f"{business.status}"
            )
        )

    # -------------------------
    # CREATE ORDER
    # -------------------------

    access_token = secrets.token_urlsafe(16)

    order = Order(

        phone=
            customer_phone,

        customer_name=
            customer_name,

        items=
            data["items"],

        total_price=
            data["total"],

        pickup_pin=
            pin,

        status=
            "payment_pending",

        payment_status=
            "pending",

        business_id=
            data[
                "business_id"
            ],

        session_token=
            data.get(
                "session_token"
            ),

        access_token=access_token
    )

    db.add(order)

    await db.commit()

    await db.refresh(
        order
    )

    # -------------------------
    # CREATE RAZORPAY ORDER
    # -------------------------

    razorpay_order = (
        create_razorpay_order(

            amount=
                data["total"],

            receipt=
                f"order_{order.id}"
        )
    )

    return {

        "success":
            True,

        "order_id":
            order.id,

        "pickup_pin":
            order.pickup_pin,

        "razorpay_order_id":
            razorpay_order["id"],

        "amount":
            razorpay_order[
                "amount"
            ],

        "key":
            RAZORPAY_KEY_ID
    }


@router.post(
    "/verify-payment"
)
async def verify_payment(
    data: dict,
    db: AsyncSession = Depends(
        get_db
    )
):

    result = await db.execute(
        select(Order).where(
            Order.id
            == data["order_id"]
        )
    )

    order = (
        result.scalar_one_or_none()
    )

    if not order:

        return {

            "success":
                False,

            "message":
                "Order not found"
        }

    # -------------------------
    # VERIFY SIGNATURE
    # -------------------------

    generated_signature = (
        hmac.new(

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
    )

    if (
        generated_signature
        !=
        data[
            "razorpay_signature"
        ]
    ):

        return {

            "success":
                False,

            "message":
                "Invalid signature"
        }

    # -------------------------
    # UPDATE ORDER
    # -------------------------

    order.status = "pending"

    order.payment_status = (
        "paid"
    )

    order.payment_id = data[
        "razorpay_payment_id"
    ]

    # -------------------------
    # SAVE PAYMENT
    # -------------------------

    payment = Payment(

        order_id=
            order.id,

        business_id=
            order.business_id,

        phone=
            order.phone,

        customer_name=
            order.customer_name,

        razorpay_payment_id=
            data[
                "razorpay_payment_id"
            ],

        amount=
            order.total_price,

        status=
            "captured",

        payment_method=
            "online"
    )

    db.add(payment)

    # -------------------------
    # END SESSION
    # -------------------------

    result = await db.execute(
        select(MenuSession).where(
            MenuSession.session_token
            == order.session_token
        )
    )

    menu_session = (
        result.scalar_one_or_none()
    )

    if menu_session:
        menu_session.is_active = False

    # -------------------------
    # SEND MESSAGE
    # -------------------------

    send_text(

        order.phone,

        f"✅ Payment successful!\n\n"

        f"🧾 Order "
        f"#{order.id}\n"

        f"💰 Amount Paid: "
        f"₹{order.total_price}\n\n"

        f"🔐 Pickup PIN: "
        f"{order.pickup_pin}\n\n"

        f"Use this PIN while "
        f"picking up your order."
    )

    await db.commit()

    return {

        "success": True,

        "access_token": order.access_token
    }