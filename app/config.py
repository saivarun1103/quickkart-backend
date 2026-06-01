import os
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
RAZORPAY_KEY_ID = os.getenv(
    "RAZORPAY_TEST_KEY_ID"
)

RAZORPAY_KEY_SECRET = os.getenv(
    "RAZORPAY_TEST_KEY_SECRET"
)

MAGIC_LINK_SECRET = os.getenv(
    "MAGIC_LINK_SECRET"
)

FRONTEND_URL = os.getenv(
    "FRONTEND_URL"
)