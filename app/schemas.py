from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional


class MenuItemResponse(BaseModel):
    id: int
    name: str
    price: int
    image_url: Optional[str] = None
    available: bool
    category: Optional[str] = None
    dietary_type: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class RegisterRequest(BaseModel):
    business_name: str
    owner_name: str
    email: EmailStr
    business_phone: str
    password: str
    business_type: str
    location_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    contact_number: Optional[str] = None

class LoginRequest(BaseModel):
    identifier: str
    password: str

class BusinessSettingsResponse(
    BaseModel
):
    pickup_verification_enabled: bool
    status: str
    logo_url: str | None = None
    banner_url: str | None = None
    name: str | None = None
    location_name: str | None = None



class BusinessSettingsUpdate(
    BaseModel
):
    pickup_verification_enabled: bool
    status: str
    logo_url: str | None = None
    banner_url: str | None = None

class ForgotPasswordRequest(BaseModel):
    phone: str

class VerifyResetOTPRequest(BaseModel):
    phone: str
    otp: str

class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str