import razorpay

from app.config import (
    RAZORPAY_KEY_ID,
    RAZORPAY_KEY_SECRET
)

client = razorpay.Client(
    auth=(
        RAZORPAY_KEY_ID,
        RAZORPAY_KEY_SECRET
    )
)


def create_payment_link(
    amount,
    phone,
    customer_name
):

    payment_link = client.payment_link.create({

        "amount": amount * 100,

        "currency": "INR",

        "accept_partial": False,

        "description":
            "Restaurant Order Payment",

        "customer": {

            "name": customer_name,

            "contact": phone
        },

        "notify": {

            "sms": True,

            "email": False
        },

        "reminder_enable": True,

        "callback_url":
            "https://project-gxnl5-jayxi2u1j-varun11n03-5162s-projects.vercel.app",

        "callback_method":
            "get",

        "notes": {

            "phone": phone
        },
    })

    return payment_link