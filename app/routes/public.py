from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import (
    AsyncSession
)

from sqlalchemy import select

from app.db import get_db
from app.models import Order, MenuItem

router = APIRouter()

@router.get(
    "/public/order/{combined}"
)
async def get_public_order(

    combined: str,

    db: AsyncSession = Depends(
        get_db
    )
):

    if ":::" not in combined:

        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )

    session_token, order_id = (
        combined.rsplit(
            ":::",
            1
        )
    )

    order_id = int(order_id)

    # -------------------------
    # GET ORDER
    # -------------------------

    result = await db.execute(
        select(Order).where(

            Order.id
            == order_id,

            Order.session_token
            == session_token
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
                price * quantity
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

            "items":
                detailed_items,

            "created_at":
                order.created_at
        }
    }