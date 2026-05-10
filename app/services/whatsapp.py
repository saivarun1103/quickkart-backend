from app.config import PHONE_NUMBER_ID,ACCESS_TOKEN
from app.models import User
from app.db import SessionLocal
import requests


def send_templete(phone: str, name: str, menu: str):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {
            "name": "test_hi_templete",
            "language": {"code": "en"},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": name},
                        {"type": "text", "text": menu}
                    ]
                }
            ]
        }
    }
    
    response = requests.post(url, headers=headers, json=data)
    print("WHATSAPP RESPONSE:", response.status_code, response.text)

    return response.json()

def send_menu_template(phone: str, link):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {
            "name": "test_menu",   # 👈 your new template name
            "language": {"code": "en_US"},
            "components": [
                {
                    "type": "button",
                    "sub_type": "url",
                    "index": "0",
                    "parameters": [
                        {
                            "type": "text",
                            "text": link
                        }
                    ]
                }
            ]
        }
    }

    response = requests.post(url, headers=headers, json=data)
    print("MENU RESPONSE:", response.status_code, response.text)

    return response.json()

def send_menu_link(phone, link):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    db = SessionLocal()
    user = db.query(User).filter(User.phone == phone).first()

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
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
        }
    }

    response = requests.post(url, headers=headers, json=data)
    print("MENU RESPONSE:", response.status_code, response.text)

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

    requests.post(url, headers=headers, json=data)
