from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import (
    AsyncSession
)

from sqlalchemy import (
    select,
    or_
)

from app.db import get_db
from app.models import (
    Order,
    MenuItem,
    Business
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
                business.logo_url
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