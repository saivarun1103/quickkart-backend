from jose import jwt
from datetime import datetime, timedelta

from app.config import MAGIC_LINK_SECRET

ALGORITHM = "HS256"


def create_menu_token(
    phone,
    business_slug
):

    payload = {
        "phone": phone,
        "business_slug": business_slug,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }

    token = jwt.encode(
        payload,
        MAGIC_LINK_SECRET,
        algorithm=ALGORITHM
    )

    return token


def verify_menu_token(token):

    payload = jwt.decode(
        token,
        MAGIC_LINK_SECRET,
        algorithms=[ALGORITHM]
    )

    return payload