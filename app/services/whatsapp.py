from app.config import PHONE_NUMBER_ID, ACCESS_TOKEN
from app.models import User
import requests
from app.db import get_db_context
from sqlalchemy import select


def send_template(
    phone: str,
    template_name: str,
    body_params: list = None,
    button_params: list = None,
    language: str = "en",
    button_subtype: str = "url",
):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    components = []

    # body variables
    if body_params:
        components.append(
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": str(param)} for param in body_params
                ],
            }
        )

    # buttons
    if button_params:
        for index, params in enumerate(button_params):
            components.append(
                {
                    "type": "button",
                    "sub_type": button_subtype,
                    "index": str(index),
                    "parameters": [
                        {"type": "text", "text": str(param)} for param in params
                    ],
                }
            )

    data = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language},
            "components": components,
        },
    }

    print("TEMPLATE:", template_name)
    print("LANG:", language)
    print("DATA:", data)

    response = requests.post(url, headers=headers, json=data, timeout=10)

    print("TEMPLATE RESPONSE:", response.status_code, response.text)

    return response.json()


def send_menu_template(phone: str, link):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    data = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {
            "name": "test_menu",  # 👈 your new template name
            "language": {"code": "en"},
            "components": [
                {
                    "type": "button",
                    "sub_type": "url",
                    "index": "0",
                    "parameters": [{"type": "text", "text": link}],
                }
            ],
        },
    }

    response = requests.post(url, headers=headers, json=data, timeout=10)
    print("MENU RESPONSE:", response.status_code, response.text)

    return response.json()


# def send_menu_template(phone: str):
#     url = (
#         f"https://graph.facebook.com/v19.0/"
#         f"{PHONE_NUMBER_ID}/messages"
#     )

#     headers = {
#         "Authorization":
#             f"Bearer {ACCESS_TOKEN}",

#         "Content-Type":
#             "application/json"
#     }

#     data = {
#         "messaging_product":
#             "whatsapp",

#         "to":
#             phone,

#         "type":
#             "template",

#         "template": {
#             "name":
#                 "hello_world",

#             "language": {
#                 "code":
#                     "en_US"
#             }
#         }
#     }

#     response = requests.post(
#         url,
#         headers=headers,
#         json=data,
#         timeout=10
#     )

#     print(
#         "MENU RESPONSE:",
#         response.status_code,
#         response.text
#     )

#     return response.json()


async def send_menu_link(phone, link):

    async with get_db_context() as db:
        result = await db.execute(select(User).where(User.phone == phone))

        user = result.scalar_one_or_none()

        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"

        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

        data = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {
                "body": (
                    f"Hi {user.customer_name}, here is the menu:\n{link}"
                    if user and user.customer_name
                    else f"Hi, here is the menu:\n{link}"
                )
            },
        }

        response = requests.post(url, headers=headers, json=data, timeout=10)

        print("MENU RESPONSE:", response.status_code, response.text)

        return response.json()


def send_text(phone, message):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    data = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": message},
    }

    requests.post(url, headers=headers, json=data, timeout=10)


def send_customer_order_confirmation(
    phone: str,
    customer_name: str,
    business_name: str,
    order_number: str,
    amount: float,
    order_token: str,
):

    send_template(
        phone=phone,
        template_name="order_confirmed_v2",
        body_params=[customer_name, business_name, order_number, amount],
        button_params=[[f"?{order_token}"]],
    )


def send_merchant_new_order(
    phone: str,
    customer_name: str,
    order_number: str,
    amount: float,
    items_text: str,
):
    send_template(
        phone=phone,
        template_name="new_order_alert_v2",
        body_params=[
            customer_name,
            order_number,
            amount,
            items_text
        ]
    )


def send_customer_order_ready(
    phone: str,
    customer_name: str,
    business_name: str,
    order_number: str,
    order_token: str,
    latitude: float,
    longitude: float,
):

    send_template(
        phone=phone,
        template_name="order_ready_pickup_v2",
        body_params=[customer_name, business_name, order_number],
        button_params=[[f"?{order_token}"], [f"={latitude},{longitude}"]],
    )


def send_customer_thank_you(phone: str, customer_name: str, business_name: str):

    send_template(
        phone=phone,
        template_name="thank_you_visit_again",
        body_params=[customer_name, business_name],
    )

def send_password_reset_otp(phone: str, otp: str):
    cleaned_phone = phone.replace("+", "")
    
    # 1. Try sending with sub_type="copy_code" (standard for authentication templates with copy code buttons)
    print(f"Attempting to send OTP template message to {cleaned_phone} with button_subtype='copy_code'...")
    res = send_template(
        phone=cleaned_phone,
        template_name="reset_password_otp",
        body_params=[otp],
        button_params=[[otp]],
        button_subtype="copy_code"
    )
    
    # 2. Check if it failed because the active template requires a URL button instead
    if isinstance(res, dict) and "error" in res:
        error_msg = res["error"].get("message", "")
        error_data = res["error"].get("error_data", {})
        details = error_data.get("details", "") if isinstance(error_data, dict) else ""
        
        if "type Url" in details or "type Url" in error_msg:
            print("Detected URL button requirement. Retrying with button_subtype='url'...")
            res = send_template(
                phone=cleaned_phone,
                template_name="reset_password_otp",
                body_params=[otp],
                button_params=[[otp]],
                button_subtype="url"
            )
            
    return res
