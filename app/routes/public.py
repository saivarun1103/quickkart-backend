from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Order, MenuItem

router = APIRouter()

@router.get("/public/order/{order_id}")
def get_public_order(
    order_id: int,
    db: Session = Depends(get_db)
):

    order = (
        db.query(Order)
        .filter(Order.id == order_id)
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    detailed_items = []

    for item_name, quantity in order.items.items():

        menu_item = (
            db.query(MenuItem)
            .filter(
                MenuItem.name == item_name,
                MenuItem.business_id == order.business_id
            )
            .first()
        )

        price = menu_item.price if menu_item else 0

        detailed_items.append({
            "name": item_name,
            "quantity": quantity,
            "price": price,
            "subtotal": price * quantity
        })

    return {
        "success": True,
        "order": {
            "id": order.id,
            "customer_name": order.customer_name,
            "pin": order.pickup_pin,
            "status": order.status,
            "payment_status": order.payment_status,
            "total": order.total_price,
            "items": detailed_items,
            "created_at": order.created_at
        }
    }