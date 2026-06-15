from app.config import PHONE_NUMBER_ID,ACCESS_TOKEN
from app.models import User
import requests
from app.db import get_db_context
from sqlalchemy import select


def send_template(
    phone: str,
    template_name: str,
    body_params: list = None,
    button_params: list = None,
    language: str = "en"
):
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

    components = []

    # body variables
    if body_params:
        components.append(
            {
                "type": "body",
                "parameters": [
                    {
                        "type": "text",
                        "text": str(param)
                    }
                    for param in body_params
                ]
            }
        )

    # buttons
    if button_params:
        for index, params in enumerate(button_params):

            components.append(
                {
                    "type": "button",
                    "sub_type": "url",
                    "index": str(index),
                    "parameters": [
                        {
                            "type": "text",
                            "text": str(param)
                        }
                        for param in params
                    ]
                }
            )

    data = {
        "messaging_product":
            "whatsapp",

        "to":
            phone,

        "type":
            "template",

        "template": {
            "name":
                template_name,

            "language": {
                "code":
                    language
            },

            "components":
                components
        }
    }

    response = requests.post(
        url,
        headers=headers,
        json=data,
        timeout=10
    )

    print(
        "TEMPLATE RESPONSE:",
        response.status_code,
        response.text
    )

    return response.json()

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
    order_token: str
):

    send_template(
        phone=phone,

        template_name=
            "order_confirmed",

        body_params=[
            customer_name,
            business_name,
            order_number,
            amount
        ],

        button_params=[
            [order_token]
        ]
    )


def send_merchant_new_order(
    phone: str,
    business_name: str,
    order_number: str,
    amount: float,
    items_text: str,
    order_id: int
):

    send_template(
        phone=phone,

        template_name=
            "new_order_alert",

        body_params=[
            business_name,
            order_number,
            amount,
            items_text
        ],

        button_params=[
            [order_id]
        ]
    )


def send_customer_order_ready(
    phone: str,
    customer_name: str,
    business_name: str,
    order_number: str,
    order_token: str,
    latitude: float,
    longitude: float
):

    send_template(
        phone=phone,

        template_name=
            "order_ready_pickup",

        body_params=[
            customer_name,
            business_name,
            order_number
        ],

        button_params=[

            # View Order
            [
                order_token
            ],

            # Directions
            [
                latitude,
                longitude
            ]
        ]
    )


def send_customer_thank_you(
    phone: str,
    customer_name: str,
    business_name: str
):

    send_template(
        phone=phone,

        template_name=
            "thank_you_visit_again",

        body_params=[
            customer_name,
            business_name
        ]
    )