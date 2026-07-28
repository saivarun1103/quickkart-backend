from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext


# 🔐 SECRET KEY
SECRET_KEY = "super-secret-key"

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_DAYS = 36500


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


# 🎟️ CREATE JWT TOKEN (Permanent token so admin stays logged in until manual logout)
def create_access_token(data: dict, expires_delta: timedelta | None = None):

    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=ACCESS_TOKEN_EXPIRE_DAYS
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

##decoding jwt token (verify_exp=False ensures inactive admin tokens never expire automatically)
def decode_token(token: str, verify_exp: bool = False):

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": verify_exp}
        )

        return payload

    except JWTError as e:

        print("JWT ERROR:", e)

        return None