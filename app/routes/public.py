from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import (
    AsyncSession
)

from sqlalchemy import (
    select,
    or_,
    func,
    cast,
    String
)

from app.db import get_db
from app.models import (
    Order,
    MenuItem,
    Business,
    User
)
from app.services.whatsapp import (
    send_customer_order_confirmation,
    send_merchant_new_order
)

router = APIRouter()

@router.get(
    "/public/order/{token}"
)
async def get_public_order(

    token: str,

    db: AsyncSession = Depends(
        get_db
    )
):

    # -------------------------
    # GET ORDER
    # -------------------------

    result = await db.execute(
        select(Order).where(

            Order.access_token
            == token
        )
    )

    order = (
        result.scalar_one_or_none()
    )

    if not order:

        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )
    
    # -------------------------
    # GET BUSINESS
    # -------------------------

    business_result = await db.execute(
        select(Business).where(
            Business.id == order.business_id
        )
    )

    business = (
        business_result
        .scalar_one_or_none()
    )

    detailed_items = []

    # -------------------------
    # BUILD ITEMS
    # -------------------------

    for item_name, quantity in (
        order.items.items()
    ):

        result = await db.execute(
            select(MenuItem).where(

                MenuItem.name
                == item_name,

                MenuItem.business_id
                == order.business_id
            )
        )

        menu_item = (
            result.scalar_one_or_none()
        )

        price = (
            menu_item.price
            if menu_item
            else 0
        )

        detailed_items.append({

            "name":
                item_name,

            "quantity":
                quantity,

            "price":
                price,

            "subtotal":
                price * quantity,

            "image_url":
                menu_item.image_url
                if menu_item
                else None
        })

    return {

        "success": True,

        "order": {

            "id":
                order.id,

            "customer_name":
                order.customer_name,

            "pin":
                order.pickup_pin,

            "status":
                order.status,

            "payment_status":
                order.payment_status,

            "total":
                order.total_price,

            "business_name":
                business.name,

            "location_name":
                business.location_name,

            "latitude":
                business.latitude,

            "longitude":
                business.longitude,

            "items":
                detailed_items,

            "created_at":
                order.created_at,

            "logo_url":
                business.logo_url,

            "pickup_verification_enabled":
                business.pickup_verification_enabled
        }
    }

@router.get(
    "/public/business/search"
)
async def search_businesses(

    q: str,

    db: AsyncSession = Depends(
        get_db
    )
):

    result = await db.execute(
        select(Business).where(
            Business.role != "FOUNDER",
            or_(
                Business.name.ilike(f"%{q}%"),
                Business.business_phone.ilike(f"%{q}%")
            )
        )
    )

    businesses = (
        result
        .scalars()
        .all()
    )

    return [

        {
            "id": business.id,
            "name": business.name,
            "business_phone":
                business.business_phone,
            "slug": business.slug,
            "logo_url":
                business.logo_url,
            "business_type":
                business.business_type,
            "address_name":
                business.location_name
        }

        for business in businesses
    ]

@router.get("/public/business/types")
async def get_business_types(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Business.business_type).distinct())
    types = result.scalars().all()
    types_list = sorted(list(set(t for t in types if t)))
    if not types_list:
        types_list = ["Tiffins", "Restaurant", "Cafe", "Fast Food", "Grocery", "Bakery"]
    return types_list

@router.get("/public/test")
async def public_test():
    return {
        "message": "public route working"
    }

@router.get(
    "/public/business/popular"
)
async def get_popular_businesses(

    db: AsyncSession = Depends(
        get_db
    )
):

    result = await db.execute(
        select(Business)
        .where(Business.role != "FOUNDER")
        .limit(10)
    )

    businesses = (
        result
        .scalars()
        .all()
    )

    return [

        {
            "id":
                business.id,

            "name":
                business.name,

            "business_phone":
                business.business_phone,

            "slug":
                business.slug,

            "logo_url":
                business.logo_url,

            "business_type":
                business.business_type,

            "address_name":
                business.location_name
        }

        for business in businesses
    ]

@router.get("/test-order-whatsapp")
async def test_order_whatsapp():

    send_customer_order_confirmation(
        phone="917702521639",
        customer_name="Varn",
        business_name="Babai Hotel",
        order_number="BK2931",
        amount=245
    )

    send_merchant_new_order(
        phone="917702521639",
        business_name="Babai Hotel",
        order_number="BK2931",
        amount=245,
        items_text=(
            "2x Idli\n"
            "1x Dosa\n"
            "1x Coke"
        ),
        dashboard_link=(
            "https://quickkart.app/admin"
        )
    )

    return {
        "message":
        "WhatsApp test sent"
    }


@router.get("/public/orders")
async def get_public_orders(
    phone: str,
    page: int = 1,
    limit: int = 10,
    query: str = None,
    db: AsyncSession = Depends(get_db)
):
    # Normalize phone number
    normalized_phone = phone.strip().replace(" ", "")
    if len(normalized_phone) == 10:
        normalized_phone = "91" + normalized_phone
    elif normalized_phone.startswith("+"):
        normalized_phone = normalized_phone.replace("+", "")
        
    # Get customer name
    user_res = await db.execute(select(User).where(User.phone == normalized_phone))
    user = user_res.scalar_one_or_none()
    customer_name = user.customer_name if user else "Customer"

    # Base stmt
    stmt = select(Order).where(
        Order.phone == normalized_phone,
        Order.payment_status == "paid"
    )
    
    count_stmt = select(func.count(Order.id)).where(
        Order.phone == normalized_phone,
        Order.payment_status == "paid"
    )
    
    if query:
        q = query.strip()
        stmt = stmt.join(Business, Business.id == Order.business_id).where(
            or_(
                cast(Order.id, String).ilike(f"%{q}%"),
                Business.name.ilike(f"%{q}%")
            )
        )
        count_stmt = count_stmt.join(Business, Business.id == Order.business_id).where(
            or_(
                cast(Order.id, String).ilike(f"%{q}%"),
                Business.name.ilike(f"%{q}%")
            )
        )

    # Calculate total count of paid orders matching filter
    total_result = await db.execute(count_stmt)
    total_count = total_result.scalar() or 0

    # Retrieve items for the current page
    offset = (page - 1) * limit
    result = await db.execute(
        stmt.order_by(Order.created_at.desc()).limit(limit).offset(offset)
    )
    orders = result.scalars().all()
    
    response_orders = []
    for order in orders:
        business_res = await db.execute(
            select(Business).where(Business.id == order.business_id)
        )
        business = business_res.scalar_one_or_none()
        
        response_orders.append({
            "id": order.id,
            "access_token": order.access_token,
            "status": order.status,
            "payment_status": order.payment_status,
            "total_price": order.total_price,
            "created_at": order.created_at,
            "business_name": business.name if business else "Unknown Business",
            "business_logo_url": business.logo_url if business else None
        })
        
    return {
        "success": True,
        "orders": response_orders,
        "total": total_count,
        "customer_name": customer_name
    }