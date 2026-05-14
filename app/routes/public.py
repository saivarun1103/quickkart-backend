from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Order, MenuItem

router = APIRouter()

@router.get("/public/order/{combined}")
def get_public_order(
    combined: str,
    db: Session = Depends(get_db)
):
    
    import re

    match = re.search(r'(\d+)$', combined)

    if not match:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )

    order_id = int(match.group(1))

    session_token = combined.replace(
        str(order_id),
        ""
    )

    order = db.query(Order).filter(
        Order.id == order_id,
        Order.session_token == session_token
    ).first()

    if (
        not order
        or order.session_token != session_token
    ):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
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