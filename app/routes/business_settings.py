from fastapi import (
    APIRouter,
    Depends
)
from sqlalchemy.ext.asyncio import (
    AsyncSession
)
from app.db import get_db
from app.dependencies import (
    get_current_business
)
from app.models import (
    Business
)
from app.schemas import (
    BusinessSettingsResponse,
    BusinessSettingsUpdate
)


router = APIRouter(
    prefix="/business/settings",
    tags=["Business Settings"]
)
from fastapi import UploadFile, File
from app.services.cloudinary_service import (
    upload_image
)


@router.get(
    "",
    response_model=
    BusinessSettingsResponse
)
async def get_settings(
    business: Business = Depends(
        get_current_business
    )
):

    return {
        "pickup_verification_enabled":
            business.pickup_verification_enabled,

        "status":
            business.status,

        "logo_url":
            business.logo_url,

        "banner_url":
            business.banner_url
    }


@router.patch("")
async def update_settings(
    data:
    BusinessSettingsUpdate,

    db: AsyncSession = Depends(
        get_db
    ),

    business: Business = Depends(
        get_current_business
    )
):

    business.pickup_verification_enabled = (
        data.pickup_verification_enabled
    )

    business.status = (
        data.status
    )

    await db.commit()

    await db.refresh(
        business
    )

    return {
        "message":
            "Settings updated",

        "pickup_verification_enabled":
            business.pickup_verification_enabled,

        "is_open":
            business.status
    }


@router.patch(
    "/business/branding"
)
async def update_branding(

    logo: UploadFile | None = File(
        default=None
    ),

    banner: UploadFile | None = File(
        default=None
    ),

    db: AsyncSession = Depends(
        get_db
    ),

    business: Business = Depends(
        get_current_business
    )
):

    if logo:

        logo_url = (
            upload_image(
                logo
            )
        )

        business.logo_url = (
            logo_url
        )

    if banner:

        banner_url = (
            upload_image(
                banner
            )
        )

        business.banner_url = (
            banner_url
        )

    await db.commit()

    await db.refresh(
        business
    )

    return {

        "message":
            "Branding updated",

        "logo_url":
            business.logo_url,

        "banner_url":
            business.banner_url
    }