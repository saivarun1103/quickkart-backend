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
