from app.config import PHONE_NUMBER_ID,ACCESS_TOKEN
from app.models import User
import requests
from app.db import get_db_context
from sqlalchemy import select


# def send_templete(phone: str, name: str, menu: str):
#     url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    

#     headers = {
#         "Authorization": f"Bearer {ACCESS_TOKEN}",
#         "Content-Type": "application/json"
#     }

#     data = {
#         "messaging_product": "whatsapp",
#         "to": phone,
#         "type": "template",
#         "template": {
#             "name": "test_hi_templete",
#             "language": {"code": "en"},
#             "components": [
#                 {
#                     "type": "body",
#                     "parameters": [
#                         {"type": "text", "text": name},
#                         {"type": "text", "text": menu}
#                     ]
#                 }
#             ]
#         }
#     }
    
#     response = requests.post(url, headers=headers, json=data, timeout=10)
#     print("WHATSAPP RESPONSE:", response.status_code, response.text)

#     return response.json()

# def send_menu_template(phone: str, link,db: Session = Depends(get_db)):
#     url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"

#     headers = {
#         "Authorization": f"Bearer {ACCESS_TOKEN}",
#         "Content-Type": "application/json"
#     }

#     data = {
#         "messaging_product": "whatsapp",
#         "to": phone,
#         "type": "template",
#         "template": {
#             "name": "test_menu",   # 👈 your new template name
#             "language": {"code": "en_US"},
#             "components": [
#                 {
#                     "type": "button",
#                     "sub_type": "url",
#                     "index": "0",
#                     "parameters": [
#                         {
#                             "type": "text",
#                             "text": link
#                         }
#                     ]
#                 }
#             ]
#         }
#     }

#     response = requests.post(url, headers=headers, json=data, timeout=10)
#     print("MENU RESPONSE:", response.status_code, response.text)

#     return response.json()


async def send_menu_link(
    phone,
    link
):

    async with get_db_context() as db:

        result = await db.execute(
            select(User).where(
                User.phone == phone
            )
        )

        user = (
            result.scalar_one_or_none()
        )

        url = (
            f"https://graph.facebook.com/v19.0/"
            f"{PHONE_NUMBER_ID}/messages"
        )

        headers = {
            "Authorization":
                f"Bearer {ACCESS_TOKEN}",

            "Content-Type":
                "application/json"
        }

        data = {
            "messaging_product":
                "whatsapp",

            "to":
                phone,

            "type":
                "text",

            "text": {
                "body": (
                    f"Hi {user.customer_name}, "
                    f"here is the menu:\n{link}"

                    if user and
                    user.customer_name

                    else
                    f"Hi, here is the menu:\n{link}"
                )
            }
        }

        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=10
        )

        print(
            "MENU RESPONSE:",
            response.status_code,
            response.text
        )

        return response.json()


def send_text(phone, message):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {
            "body": message
        }
    }

    requests.post(url, headers=headers, json=data, timeout=10)


def send_customer_order_confirmation(
    phone: str,
    customer_name: str,
    business_name: str,
    order_number: str,
    amount: float,
    order_link: str
):

    message = f"""
✅ Order Confirmed

Hi {customer_name},

Your order has been confirmed at
{business_name}

🧾 Order No:
{order_number}

💰 Amount:
₹{amount}

Status:
Preparing

View Order:
{order_link}

We’ll notify you once it is ready for pickup.
""".strip()

    send_text(
        phone=phone,
        message=message
    )


def send_merchant_new_order(
    phone: str,
    business_name: str,
    order_number: str,
    amount: float,
    items_text: str,
    dashboard_link: str
):

    message = f"""
🔔 NEW ORDER #{order_number}

{business_name}

₹{amount} | PREPAID

{items_text}

Open Dashboard:
{dashboard_link}
""".strip()

    send_text(
        phone=phone,
        message=message
    )


def send_customer_order_ready(
    phone: str,
    customer_name: str,
    business_name: str,
    order_number: str,
    pickup_pin: str
):

    message = f"""
🍽️ Order Ready

Hi {customer_name},

Your order from
{business_name}
is ready for pickup.

Order No: {order_number}

🔐 Pickup PIN:
{pickup_pin}

Please show this PIN
while collecting your order.
""".strip()

    send_text(
        phone=phone,
        message=message
    )
