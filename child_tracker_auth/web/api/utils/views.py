from typing import Literal

from fastapi import APIRouter
from fastapi.params import Depends

from child_tracker_auth.security.oauth2 import get_current_member
from child_tracker_auth.settings import settings

router = APIRouter(
    prefix="/utils",
    tags=["Utils"],
    dependencies=(
        [Depends(get_current_member)] if settings.environment == "prod" else None
    ),
)


@router.get("/regions/{locale}", response_model=list[str])
async def get_regions(locale: Literal["ru", "en"]):
    locale_regions = []
    for item in settings.regions:
        for k, v in item.items():
            if k == locale:
                locale_regions.append(v)
    return locale_regions
