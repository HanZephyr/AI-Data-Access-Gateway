from typing import Annotated

from fastapi import APIRouter, Depends

from adg.app.dependencies import AuthenticatedApiKey, require_admin_api_key
from adg.app.settings import get_settings

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/system")
def system(
    api_key: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
) -> dict[str, str]:
    return {
        "service": get_settings().service_name,
        "api_key_id": api_key.id,
    }
