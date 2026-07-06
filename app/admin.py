from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import (
    AsyncSession
)
from sqlalchemy import select
from app.db import get_db
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
from app.services.whatsapp import (
    send_text,
    send_customer_order_ready
)
from datetime import datetime, timedelta
from app.services.cloudinary_service import upload_image
from app.services.whatsapp import (
    send_customer_thank_you
)


router = APIRouter(prefix="/api/admin", tags=["Admin"])

class PickupVerifyRequest(BaseModel):
    pickup_pin: str
  

# ✅ Add Item (with optional image)
@router.post("/menu")
async def add_item(
    name: str = Form(...),

    price: float = Form(...),

    category: str = Form(None),

    description: str = Form(None),

    dietary_type: str = Form(None),

    file: UploadFile = File(None),

    db: AsyncSession = Depends(get_db),

    business: Business = Depends(
        get_current_business
    )
):

    # CHECK EXISTING ITEM
    result = await db.execute(
        select(MenuItem).where(
            MenuItem.business_id
            == business.id,

            MenuItem.name.ilike(name)
        )
    )

    existing_item = (
        result.scalar_one_or_none()
    )

    image_url = None

    if file:

        try:

            image_url = upload_image(
                file
            )

        except Exception as e:

            print(
                "CLOUDINARY ERROR:",
                e
            )

            raise HTTPException(
                status_code=500,
                detail="Image upload failed"
            )

    # RESTORE EXISTING ITEM
    if existing_item:

        existing_item.price = price

        existing_item.category = (
            category
        )

        existing_item.description = (
            description
        )

        existing_item.dietary_type = (
            dietary_type
        )

        existing_item.available = True
        existing_item.is_active = True

        if image_url:
            existing_item.image_url = (
                image_url
            )

        await db.commit()

        await db.refresh(
            existing_item
        )

        return existing_item

    # CREATE NEW ITEM
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

    await db.commit()

    await db.refresh(new_item)

    return new_item

@router.get("/menu")
async def get_menu(
    db: AsyncSession = Depends(get_db),

    business: Business = Depends(
        get_current_business
    )
):
    result = await db.execute(
        select(MenuItem).where(
            MenuItem.business_id
            == business.id,

            MenuItem.is_active
            == True
        )
    )

    menu_items = (
        result.scalars().all()
    )

    return menu_items

##Availability
@router.patch("/menu/{item_id}/toggle")
async def toggle_item(
    item_id: int,

    db: AsyncSession = Depends(get_db),

    business: Business = Depends(
        get_current_business
    )
):
    result = await db.execute(
        select(MenuItem).where(
            MenuItem.id == item_id,
            MenuItem.business_id
            == business.id
        )
    )

    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            404,
            "Item not found"
        )

    item.available = (
        not item.available
    )

    await db.commit()

    return item

##delete item
@router.delete("/menu/{item_id}")
async def delete_item(
    item_id: int,

    db: AsyncSession = Depends(get_db),

    business: Business = Depends(
        get_current_business
    )
):
    result = await db.execute(
        select(MenuItem).where(
            MenuItem.id == item_id,
            MenuItem.business_id
            == business.id
        )
    )

    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            404,
            "Item not found"
        )

    item.is_active = False

    await db.commit()

    return {
        "message": "Item deleted"
    }

@router.put("/menu/{item_id}")
async def update_item(
    item_id: int,

    name: str = Form(None),

    price: int = Form(None),

    category: str = Form(None),

    dietary_type: str = Form(None),

    description: str = Form(""),

    available: bool = Form(True),

    file: UploadFile = File(None),

    db: AsyncSession = Depends(get_db),

    business: Business = Depends(
        get_current_business
    )
):
    result = await db.execute(
        select(MenuItem).where(
            MenuItem.id == item_id,
            MenuItem.business_id
            == business.id
        )
    )

    item = result.scalar_one_or_none()

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
            item.image_url = (
                upload_image(file)
            )

        except Exception as e:

            print(
                "CLOUDINARY ERROR:",
                e
            )

            raise HTTPException(
                status_code=500,
                detail="Image upload failed"
            )

    item.available = available

    await db.commit()

    await db.refresh(item)

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
        "logo_url": business.logo_url,
        "role": business.role
    }

##Admin orders page.
@router.get("/orders")
async def get_orders(

    range: str = "today",

    db: AsyncSession = Depends(get_db),

    business: Business = Depends(
        get_current_business
    )
):

    now = datetime.utcnow()

    stmt = select(Order).where(
        Order.business_id == business.id,
        Order.payment_status == "paid"
    )

    # TODAY
    if range == "today":

        start = datetime(
            now.year,
            now.month,
            now.day
        )

        stmt = stmt.where(
            Order.created_at >= start
        )

    # YESTERDAY
    elif range == "yesterday":

        today_start = datetime(
            now.year,
            now.month,
            now.day
        )

        yesterday_start = (
            today_start - timedelta(days=1)
        )

        stmt = stmt.where(
            Order.created_at >= yesterday_start,
            Order.created_at < today_start
        )

    # LAST 7 DAYS
    elif range == "week":

        week_start = now - timedelta(days=7)

        stmt = stmt.where(
            Order.created_at >= week_start
        )

    # LAST 30 DAYS
    elif range == "month":

        month_start = now - timedelta(days=30)

        stmt = stmt.where(
            Order.created_at >= month_start
        )

    stmt = stmt.order_by(
        Order.created_at.desc()
    )

    result = await db.execute(stmt)

    orders = result.scalars().all()

    response_orders = []

    for order in orders:

        enriched_items = []

        if order.items:

            menu_result = await db.execute(
                select(MenuItem).where(
                    MenuItem.business_id
                    == business.id
                )
            )

            menu_items = (
                menu_result.scalars().all()
            )

            menu_price_map = {
                item.name.lower(): item.price
                for item in menu_items
            }

            for (
                item_name,
                qty
            ) in order.items.items():

                unit_price = (
                    menu_price_map.get(
                        item_name.lower(),
                        0
                    )
                )

                enriched_items.append(
                    {
                        "name":
                            item_name,

                        "qty":
                            qty,

                        "price":
                            unit_price,

                        "subtotal":
                            unit_price * qty
                    }
                )

        response_orders.append(
            {
                "id":
                    order.id,

                "customer_name":
                    order.customer_name,

                "phone":
                    order.phone,

                "status":
                    order.status,

                "pickup_pin":
                    order.pickup_pin,

                "created_at":
                    order.created_at,

                "total_price":
                    order.total_price,

                "payment_status":
                    order.payment_status,

                "items":
                    enriched_items
            }
        )

    return response_orders


##Update Status API
@router.patch("/orders/{order_id}")
async def update_order_status(

    order_id: int,

    background_tasks: BackgroundTasks,

    status: str = Form(...),

    db: AsyncSession = Depends(get_db),

    business: Business = Depends(
        get_current_business
    )
):

    result = await db.execute(
        select(Order).where(
            Order.id == order_id,
            Order.business_id
            == business.id
        )
    )

    order = (
        result.scalars().first()
    )

    if not order:

        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    # completed orders cannot change
    if order.status == "completed":

        raise HTTPException(
            status_code=400,
            detail="Order already completed"
        )
    # valid statuses
    if status not in [
        "ready",
        "completed"
    ]:

        raise HTTPException(
            status_code=400,
            detail="Invalid status"
        )

    # transition rules
    allowed_transitions = {

        "pending": [
            "ready",
            "completed"
        ],

        "preparing": [
            "ready",
            "completed"
        ],

        "ready": [
            "completed"
        ],

        "completed": []
    }
    current_status = order.status

    if status not in (
        allowed_transitions[
            current_status
        ]
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot change "
                f"status from "
                f"{current_status} "
                f"to {status}"
            )
        )

    order.status = status

    await db.commit()

    # WhatsApp when READY
    if status == "ready":

        background_tasks.add_task(
            send_customer_order_ready,

            order.phone,

            order.customer_name
            or "Customer",

            business.name,

            f"{order.id}",

            order.access_token,

            business.latitude,

            business.longitude
        )

    await db.refresh(order)

    return order

@router.post("/verify-pickup")
async def verify_pickup(
    data: PickupVerifyRequest,

    db: AsyncSession = Depends(get_db),

    business: Business = Depends(
        get_current_business
    )
):

    allowed_statuses = [
        "ready",
        "pending",
        "preparing"
    ]

    result = await db.execute(
        select(Order)
        .where(
            Order.pickup_pin
            == data.pickup_pin,

            Order.business_id
            == business.id,

            Order.status.in_(
                allowed_statuses
            )
        )
        .order_by(
            Order.created_at
            .desc()
        )
    )

    order = (
        result.scalars().first()
    )

    if not order:

        raise HTTPException(
            status_code=404,
            detail="Invalid pickup PIN"
        )

    order.status = "completed"

    result = await db.execute(
        select(MenuSession)
        .where(
            MenuSession.phone
            == order.phone,

            MenuSession.business_id
            == business.id,

            MenuSession.is_active
            == True
        )
        .order_by(
            MenuSession.created_at
            .desc()
        )
    )

    menu_session = (
        result.scalars().first()
    )

    if menu_session:
        menu_session.is_active = False

    await db.commit()

    await db.refresh(order)

    customer_name = (
        order.customer_name
        if order.customer_name
        else "Customer"
    )

    send_customer_thank_you(
        order.phone,
        customer_name,
        business.name
    )

    return {
        "id": order.id,
        "customer_name":
            order.customer_name,
        "items":
            order.items
    }

from datetime import (
    date,
    datetime,
    timedelta
)

@router.get("/analytics")
async def get_analytics(
    startDate: date,
    endDate: date,

    db: AsyncSession = Depends(
        get_db
    ),

    business: Business = Depends(
        get_current_business
    )
):

    start = datetime.combine(
        startDate,
        datetime.min.time()
    )

    end = datetime.combine(
        endDate + timedelta(days=1),
        datetime.min.time()
    )

    result = await db.execute(
        select(Order).where(

            Order.business_id
            == business.id,

            Order.created_at >= start,

            Order.created_at < end,

            Order.payment_status
            == "paid"
        )
        .order_by(
            Order.created_at.desc()
        )
    )

    orders = (
        result.scalars().all()
    )

    total_sales = sum(
        float(order.total_price)
        for order in orders
    )

    total_orders = len(
        orders
    )

    response_orders = []

    # menu prices lookup
    menu_result = await db.execute(
        select(MenuItem).where(
            MenuItem.business_id
            == business.id
        )
    )

    menu_items = (
        menu_result.scalars().all()
    )

    menu_price_map = {
        item.name.lower():
        item.price
        for item
        in menu_items
    }

    for order in orders:

        enriched_items = []

        if order.items:

            for (
                item_name,
                qty
            ) in order.items.items():

                unit_price = (
                    menu_price_map.get(
                        item_name.lower(),
                        0
                    )
                )

                enriched_items.append(
                    {
                        "name":
                            item_name,

                        "qty":
                            qty,

                        "price":
                            unit_price,

                        "subtotal":
                            unit_price * qty
                    }
                )

        response_orders.append(
            {
                "id":
                    order.id,

                "customer_name":
                    order.customer_name,

                "phone":
                    order.phone,

                "status":
                    order.status,

                "pickup_pin":
                    order.pickup_pin,

                "created_at":
                    order.created_at.isoformat(),

                "total_price":
                    order.total_price,

                "payment_status":
                    order.payment_status,

                "order_number":
                    order.id,

                "items":
                    enriched_items
            }
        )

    # Calculate previous period dates
    days_diff = (endDate - startDate).days + 1
    prev_startDate = startDate - timedelta(days=days_diff)
    prev_endDate = endDate - timedelta(days=days_diff)

    prev_start = datetime.combine(prev_startDate, datetime.min.time())
    prev_end = datetime.combine(prev_endDate + timedelta(days=1), datetime.min.time())

    # Get previous period orders
    prev_result = await db.execute(
        select(Order).where(
            Order.business_id == business.id,
            Order.created_at >= prev_start,
            Order.created_at < prev_end,
            Order.payment_status == "paid"
        )
    )
    prev_orders = prev_result.scalars().all()

    prev_total_orders = len(prev_orders)
    prev_total_sales = sum(float(order.total_price) for order in prev_orders)
    prev_avg_order = prev_total_sales / prev_total_orders if prev_total_orders > 0 else 0
    prev_pickup_orders = len([o for o in prev_orders if o.status != "cancelled"])

    # Current period metrics
    avg_order = total_sales / total_orders if total_orders > 0 else 0
    pickup_orders = len([o for o in orders if o.status != "cancelled"])

    def get_percentage_change(current, previous):
        if previous == 0:
            if current == 0:
                return "0.0%", "neutral"
            else:
                return "+100.0%", "up"
        change = ((current - previous) / previous) * 100
        if change > 0:
            return f"+{change:.1f}%", "up"
        elif change < 0:
            return f"{change:.1f}%", "down"
        else:
            return "0.0%", "neutral"

    orders_change, orders_trend = get_percentage_change(total_orders, prev_total_orders)
    sales_change, sales_trend = get_percentage_change(total_sales, prev_total_sales)
    avg_order_change, avg_order_trend = get_percentage_change(avg_order, prev_avg_order)
    pickup_orders_change, pickup_orders_trend = get_percentage_change(pickup_orders, prev_pickup_orders)

    return {
        "startDate":
            str(startDate),

        "endDate":
            str(endDate),

        "total_sales":
            total_sales,

        "total_orders":
            total_orders,

        "avg_order":
            round(
                avg_order,
                2
            ),

        "orders":
            response_orders,

        "metrics_changes": {
            "total_orders": {"change": orders_change, "trend": orders_trend},
            "total_sales": {"change": sales_change, "trend": sales_trend},
            "pickup_orders": {"change": pickup_orders_change, "trend": pickup_orders_trend},
            "avg_order": {"change": avg_order_change, "trend": avg_order_trend}
        }
    }

