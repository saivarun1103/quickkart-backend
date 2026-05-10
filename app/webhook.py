from fastapi import APIRouter, Request
from app.config import VERIFY_TOKEN
from app.services.whatsapp import send_templete, send_menu_template, send_menu_link, send_text
from app.services.orderParser import parse_order, calculate_total
from app.db import SessionLocal
from app.models import User, Order, MenuItem, Payment, MenuSession, Business
from sqlalchemy.orm import Session
from fastapi import Depends
from app.services.razorpay_service import (
    create_payment_link
)
from app.services.token_service import (
    create_menu_token
)
from datetime import datetime, timedelta, timezone



router  = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# def should_use_template(db, phone):
#     user = db.query(User).filter(User.phone == phone).first()

#     # ✅ First time user
#     if not user:
#         return True

#     # ✅ If no timestamp yet
#     if user.last_message_time is None:
#         return True

#     # ✅ Safe calculation
#     diff = datetime.now(timezone.utc) - user.last_message_time

#     return diff > timedelta(hours=24)


@router.get("/webhook")
async def verify(request: Request):
    params = request.query_params

    mode = params.get("hub.mode")
    challenge = params.get("hub.challenge")
    verify_token = params.get("hub.verify_token")

    if mode == "subscribe" and verify_token == VERIFY_TOKEN:
        return int(challenge)

    return "Verification failed"

@router.post("/webhook")
async def receive_message(request: Request, db: Session = Depends(get_db)):
    data = await request.json()

    try:
        entry = data.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages")

        if messages:
            message = messages[0]
            text = message.get("text", {}).get("body")
            phone = message.get("from")

            print("User:", phone)
            print("Text:", text)

            # ✅ Get or create user
            user = db.query(User).filter(User.phone == phone).first()

            if not user:
                
                user = User(
                    phone=phone
                )
                db.add(user)
                db.commit()
                db.refresh(user)

            if text:
                text = text.lower().strip()
                
                # -------------------------
                # ✅ NAME COLLECTION
                # -------------------------

                if user.state == "awaiting_name":

                    user.customer_name = text.title()

                    pending_order = user.pending_order

                    user.state = None

                    db.commit()

                    # ✅ Continue original order automatically
                    text = pending_order

                # -------------------------
                # ✅ HI / MENU FLOW
                # -------------------------
                if text in ["hi", "menu"]:
                    business_slug = "babai-hotel"

                    import secrets

                    business_slug = business_slug

                    business = db.query(Business).filter(
                        Business.slug == business_slug
                    ).first()

                    existing_sessions = db.query(
                        MenuSession
                    ).filter(
                        MenuSession.phone == phone,
                        MenuSession.business_id == business.id,
                        MenuSession.is_active == True
                    ).order_by(
                        MenuSession.created_at.desc()
                    ).all()

                    existing_session = None
                    now = datetime.now(timezone.utc)

                    for session in existing_sessions:
                        expires_at = session.expires_at

                        if expires_at.tzinfo is None:
                            expires_at = expires_at.replace(tzinfo=timezone.utc)

                        if expires_at > now:
                            existing_session = session
                            break

                    if existing_session:

                        existing_session.last_used_at = (
                            datetime.now(timezone.utc)
                        )

                        db.commit()

                        menu_link = (

                            f"https://quickkart-frontend-beta.vercel.app"

                            f"/{business.slug}/m/"
                            f"{existing_session.session_token}"
                        )

                        send_menu_link(
                            phone,
                            menu_link
                        )

                        return {"status": "ok"}

                    session_token = secrets.token_urlsafe(8)

                    expires_at = (
                        datetime.now(timezone.utc) +
                        timedelta(minutes=30)
                    )

                    menu_session = MenuSession(

                        session_token=session_token,

                        phone=phone,

                        business_id=business.id,

                        expires_at=expires_at,

                        is_active=True,

                        last_used_at=datetime.now(timezone.utc)
                    )
                    db.add(menu_session)

                    db.commit()

                    menu_link = (

                        f"https://quickkart-frontend-beta.vercel.app"  

                        f"/{business.slug}/m/{session_token}"
                    )

                    send_menu_link(
                        phone,
                        menu_link
                    )

                # -------------------------
                # ✅ ORDER PARSING
                # -------------------------
                elif text.startswith("order:"):
                    items = parse_order(text, db)

                    if not items:
                        send_text(phone, "❌ Couldn't understand your order.")
                        return {"status": "ok"}

                    total = 0
                    response_msg = ""

                    # ✅ Fetch menu once
                    menu_items = db.query(MenuItem).filter(
                        MenuItem.is_active == True
                    ).all()

                    menu_map = {
                        item.name.lower(): item
                        for item in menu_items
                    }

                    response_msg = "🧾 Your Order:\n\n"

                    for item_name, qty in items.items():
                        db_item = menu_map.get(item_name.lower())

                        if not db_item:
                            continue

                        if not db_item.available:
                            response_msg += f"{item_name} is unavailable ❌\n"
                            continue

                        cost = db_item.price * qty
                        total += cost
                        
                        response_msg += f"{db_item.name} x{qty} = ₹{cost}\n"
                    print("PARSED ITEMS:", items)

                    # ❌ If nothing valid
                    if total == 0:
                        send_text(phone, "❌ No valid items in order.")
                        return {"status": "ok"}
                    
                    # ✅ Ask customer name first

                    if not user.customer_name:

                        user.state = "awaiting_name"

                        user.pending_order = text

                        db.commit()

                        send_text(
                            phone,
                            "Before confirming your order, please enter your name 🙂"
                        )

                        return {"status": "ok"}

                    # ✅ Save temporary order only
                    import json

                    user.pending_order = json.dumps({
                        "items": items,
                        "total_price": int(total)
                    })

                    user.state = "awaiting_confirmation"

                    db.commit()

                    # ✅ Confirmation message
                    response_msg += f"\n💰 Total: ₹{total}\n\n"
                    response_msg += "Reply YES to confirm your order."

                    send_text(phone, response_msg)

                # -------------------------
                # ✅ CONFIRMATION FLOW
                # -------------------------
                elif text in ["yes", "no"]:

                    import json

                    if text == "yes":

                        if not user.pending_order:

                            send_text(
                                phone,
                                "⚠️ No pending order found."
                            )

                            return {"status": "ok"}

                        import json

                        pending_data = json.loads(
                            user.pending_order
                        )

                        payment_link = create_payment_link(

                            amount=
                                pending_data["total_price"],

                            phone=phone,

                            customer_name=
                                user.customer_name
                        )

                        payment_url = payment_link["short_url"]

                        send_text(

                            phone,

                            f"💳 Complete your payment:\n\n"
                            f"{payment_url}"
                        )

                        user.state = "awaiting_payment"

                        db.commit()

                        return {"status": "ok"}
                        
                    else:

                        user.pending_order = None
                        user.state = None

                        db.commit()

                        send_text(
                            phone,
                            "❌ Order cancelled."
                        )

                    user.state = None
                    db.commit()

                # -------------------------
                # ✅ UNKNOWN INPUT
                # -------------------------
                else:
                    send_text(phone, "Send 'menu' to start ordering 🍽️")

            # -------------------------
            # ✅ UPDATE LAST MESSAGE TIME
            # -------------------------
            user.last_message_time = datetime.now(timezone.utc)
            db.commit()

    except Exception as e:
        print("Error:", e)

    return {"status": "ok"}

@router.post("/razorpay-webhook")

async def razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db)
):

    print("RAZORPAY WEBHOOK HIT")

    payload = await request.json()

    print(payload)

    event = payload.get("event")

    print("EVENT:", event)

    if event not in [
        "payment.captured",
        "payment_link.paid"
    ]:
        return {"status": "ignored"}

    payment_entity = payload["payload"]["payment"]["entity"]

    razorpay_payment_id = payment_entity["id"]

    amount = payment_entity["amount"] // 100

    payment_method = payment_entity["method"]

    notes = payment_entity.get(
        "notes",
        {}
    )

    phone = notes.get("phone")

    if not phone:

        return {
            "status": "phone_missing"
        }

    try:

        user = db.query(User).filter(
            User.phone == phone
        ).first()

        if not user:

            return {
                "status": "user_not_found"
            }

        if not user.pending_order:

            return {
                "status": "no_pending_order"
            }

        import json, random

        pending_data = json.loads(
            user.pending_order
        )

        import random

        while True:

            generated_pin = str(
                random.randint(1000, 9999)
            )

            existing_order = db.query(Order).filter(

                Order.business_id == pending_data["business_id"],

                Order.pickup_pin == generated_pin,

                Order.status.in_([
                    "pending",
                    "preparing",
                    "ready"
                ])

            ).first()

            if not existing_order:

                break

        # -------------------------
        # CREATE ORDER
        # -------------------------

        new_order = Order(

            phone=phone,

            customer_name=
                user.customer_name,

            items=
                pending_data["items"],

            total_price=
                int(float(pending_data["total_price"])),

            pickup_pin=generated_pin,

            status="pending",

            business_id=pending_data["business_id"],

            payment_status="paid",

            payment_id=
                razorpay_payment_id
        )

        db.add(new_order)

        db.commit()

        db.refresh(new_order)

        # -------------------------
        # CREATE PAYMENT ROW
        # -------------------------

        payment = Payment(

            order_id=
                new_order.id,

            business_id=pending_data["business_id"],

            phone=phone,

            customer_name=
                user.customer_name,

            razorpay_payment_id=
                razorpay_payment_id,

            amount=amount,

            status="captured",

            payment_method=
                payment_method
        )

        db.add(payment)

        # -------------------------
        # CLEAR PENDING ORDER
        # -------------------------

        user.pending_order = None

        user.state = None

        db.commit()

        # -------------------------
        # SEND SUCCESS MESSAGE
        # -------------------------

        send_text(

            phone,

            f"✅ Payment successful!\n\n"

            f"🧾 Order #{new_order.id}\n"

            f"💰 Amount Paid: ₹{amount}\n\n"

            f"🔐 Pickup PIN: {generated_pin}\n\n"

            f"Use this PIN while picking up your order."
        )

        print("ORDER CREATED")

        return {
            "status": "success"
        }

    except Exception as e:

        print(
            "WEBHOOK ERROR:",
            e
        )

        return {
            "status": "error"
        }