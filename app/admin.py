from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.orm import Session
import uuid
import os
from fastapi import Request
from app.db import SessionLocal
from app.models import (
    MenuItem,
    Business,
    User,
    Order,
    MenuSession
)
from app.dependencies import (
    get_current_business
)
from pydantic import BaseModel
from app.services.whatsapp import send_text
from datetime import datetime, timedelta
from app.services.cloudinary_service import upload_image


router = APIRouter(prefix="/admin", tags=["Admin"])

class PickupVerifyRequest(BaseModel):
    pickup_pin: str
  
# DB Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ✅ Add Item (with optional image)
@router.post("/menu")
def add_item(
    name: str = Form(...),

    price: float = Form(...),

    category: str = Form(None),

    description: str = Form(None),

    dietary_type: str = Form(None),

    file: UploadFile = File(None),

    db: Session = Depends(get_db),

    business: Business = Depends(
        get_current_business
    )
):

    # 🔥 CHECK EXISTING ITEM
    existing_item = db.query(MenuItem).filter(
        MenuItem.business_id == business.id,
        MenuItem.name.ilike(name)
    ).first()

    image_url = None

    if file:

        try:

            image_url = upload_image(file)

        except Exception as e:

            print("CLOUDINARY ERROR:", e)

            raise HTTPException(
                status_code=500,
                detail="Image upload failed"
            )

    # 🔥 RESTORE EXISTING ITEM
    if existing_item:

        existing_item.price = price

        existing_item.category = category

        existing_item.description = description

        existing_item.dietary_type = dietary_type

        existing_item.available = True

        existing_item.is_active = True

        if image_url:
            existing_item.image_url = image_url

        db.commit()

        db.refresh(existing_item)

        return existing_item

    # 🔥 CREATE NEW ITEM
    new_item = MenuItem(
        name=name,

        price=price,

        category=category,

        description=description,

        dietary_type=dietary_type,

        image_url=image_url,

        available=True,

        is_active=True,

        business_id=business.id
    )

    db.add(new_item)

    db.commit()

    db.refresh(new_item)

    return new_item

@router.get("/menu")
def get_menu(
    db: Session = Depends(get_db),

    business: Business = Depends(
        get_current_business
    )
):
    return db.query(MenuItem).filter(
        MenuItem.business_id == business.id,
        MenuItem.is_active == True
    ).all()

##Availability
@router.patch("/menu/{item_id}/toggle")
def toggle_item(
    item_id: int,

    db: Session = Depends(get_db),

    business: Business = Depends(
        get_current_business
    )
):
    item = db.query(MenuItem).filter(
        MenuItem.id == item_id,

        MenuItem.business_id == business.id
    ).first()

    if not item:
        raise HTTPException(
            404,
            "Item not found"
        )

    item.available = (
        not item.available
    )

    db.commit()

    return item

##delete item
@router.delete("/menu/{item_id}")
def delete_item(
    item_id: int,

    db: Session = Depends(get_db),

    business: Business = Depends(
        get_current_business
    )
):
    item = db.query(MenuItem).filter(
        MenuItem.id == item_id,

        MenuItem.business_id == business.id
    ).first()

    if not item:
        raise HTTPException(
            404,
            "Item not found"
        )

    # 🔥 SOFT DELETE
    item.is_active = False

    db.commit()

    return {
        "message": "Item deleted"
    }

@router.put("/menu/{item_id}")
def update_item(
    item_id: int,

    name: str = Form(None),

    price: int = Form(None),

    category: str = Form(None),

    dietary_type: str = Form(None),

    description: str = Form(""),

    file: UploadFile = File(None),

    db: Session = Depends(get_db),

    business: Business = Depends(
        get_current_business
    )
):
    item = db.query(MenuItem).filter(
        MenuItem.id == item_id,

        MenuItem.business_id == business.id
    ).first()

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Item not found"
        )

    # Update fields
    if name:
        item.name = name

    if price:
        item.price = price

    
    item.description = description

    item.category = category

    item.dietary_type = dietary_type

    # Update image
    if file:

        try:

            item.image_url = upload_image(file)

        except Exception as e:

            print("CLOUDINARY ERROR:", e)

            raise HTTPException(
                status_code=500,
                detail="Image upload failed"
            )

    db.commit()

    db.refresh(item)

    return item

@router.get("/me")
def get_me(
    business: Business = Depends(
        get_current_business
    )
):
    return {
        "id": business.id,
        "business_name": business.name,
        "email": business.email,
        "logo_url": business.logo_url
    }

##Admin orders page.
@router.get("/orders")
def get_orders(

    range: str = "today",

    db: Session = Depends(get_db),

    business: Business = Depends(
        get_current_business
    )
):

    orders = db.query(Order).filter(
        Order.business_id == business.id
    ).order_by(
        Order.created_at.desc()
    ).all()

    return orders


##Update Status API
@router.patch("/orders/{order_id}")
def update_order_status(

    order_id: int,

    status: str = Form(...),

    db: Session = Depends(get_db),

    business: Business = Depends(
        get_current_business
    )
):

    order = db.query(Order).filter(
        Order.id == order_id,

        Order.business_id == business.id
    ).first()

    if not order:

        raise HTTPException(
            404,
            "Order not found"
        )

    # ✅ Prevent changing locked orders

    if order.status in ["ready", "completed"]:

        raise HTTPException(
            status_code=400,
            detail="Order status is locked"
        )

    # ✅ Valid transitions

    if status not in [
        "preparing",
        "ready"
    ]:
        raise HTTPException(
            status_code=400,
            detail="Invalid status"
        )

    allowed_transitions = {

        "pending": ["preparing"],

        "preparing": ["ready"],

        "ready": [],

        "completed": []
    }

    current_status = order.status

    # ✅ Check transition validity

    if status not in allowed_transitions[current_status]:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot change status from "
                f"{current_status} to {status}"
            )
        )

    # ✅ Update status

    order.status = status

    db.commit()

    db.commit()

    # ✅ Send WhatsApp when READY

    if status == "ready":

        send_text(

            order.phone,

            f"✅ Your order is ready for pickup!\n\n"
            f"Pickup PIN: {order.pickup_pin}\n\n"
            f"Please show this PIN while collecting your order 🍽️"
        )

    db.commit()

    db.refresh(order)

    return order

@router.post("/verify-pickup")
def verify_pickup(
    data: PickupVerifyRequest,
    db: Session = Depends(get_db)
):

    order = db.query(Order).filter(

        Order.pickup_pin == data.pickup_pin,

        Order.status == "ready"

    ).order_by(

        Order.created_at.desc()

    ).first()

    if not order:

        raise HTTPException(
            status_code=404,
            detail="Invalid pickup PIN"
        )

    order.status = "completed"

    business = db.query(Business).filter(
        Business.id == order.business_id
    ).first()

    menu_session = db.query(
        MenuSession
    ).filter(

        MenuSession.phone == order.phone,

        MenuSession.business_id
            == business.id,

        MenuSession.is_active == True

    ).order_by(

        MenuSession.created_at.desc()

    ).first()

    if menu_session:

        menu_session.is_active = False

    db.commit()

    db.refresh(order)

    customer_name = (
        order.customer_name
        if order.customer_name
        else "Customer"
    )

    send_text(

        order.phone,

        f"🙏 Thank you {customer_name} for ordering from "
        f"{business.name}!\n\n"
        f"Please visit again ❤️"
    )

    return {

        "id": order.id,

        "customer_name":
            order.customer_name,

        "items":
            order.items
    }

@router.get("/analytics")
def get_analytics(

    date: str,

    db: Session = Depends(get_db),

    business: Business = Depends(
        get_current_business
    )
):

    selected_date = datetime.strptime(
        date,
        "%Y-%m-%d"
    )

    start = datetime(
        selected_date.year,
        selected_date.month,
        selected_date.day
    )

    end = start + timedelta(days=1)

    orders = db.query(Order).filter(

        Order.business_id == business.id,

        Order.created_at >= start,

        Order.created_at < end,

        Order.payment_status == "paid"

    ).all()

    total_sales = sum(
        float(order.total_price)
        for order in orders
    )

    total_orders = len(orders)

    return {

        "date": date,

        "total_sales": total_sales,

        "total_orders": total_orders
    }