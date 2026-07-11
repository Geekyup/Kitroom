from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from app.api.deps import get_kit_service
from app.services.kit_service import KitService

router = APIRouter(prefix="/kits", tags=["kits"])


@router.get("/{slug}/download")
async def download_kit(
    slug: str,
    kit_service: KitService = Depends(get_kit_service),
) -> RedirectResponse:
    kit = await kit_service.get_kit_for_download(slug)
    url = await kit_service.storage.get_url(kit.original_zip_path, expires_in=300)

    return RedirectResponse(url=url, status_code=307)
