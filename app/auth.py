from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext


# 🔐 SECRET KEY
SECRET_KEY = "super-secret-key"

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 10080


# 🔒 PASSWORD HASHING
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


# 🔑 HASH PASSWORD
def hash_password(password: str):
    return pwd_context.hash(password)


# 🔍 VERIFY PASSWORD
def verify_password(
    plain_password: str,
    hashed_password: str
):
    return pwd_context.verify(
        plain_password,
        hashed_password
    )


# 🎟️ CREATE JWT TOKEN
def create_access_token(data: dict):

    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({
        "exp": expire
    })

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return encoded_jwt

## normalizing phone number
def normalize_phone(phone: str):

    # remove spaces
    phone = phone.strip()

    # remove +
    phone = phone.replace("+", "")

    # India logic
    if phone.startswith("91") and len(phone) == 12:
        return f"+{phone}"

    # if 10-digit Indian number
    if len(phone) == 10:
        return f"+91{phone}"

    return f"+{phone}"

##decoding jwt token
def decode_token(token: str):

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        return payload

    except JWTError as e:

        print("JWT ERROR:", e)

        return None