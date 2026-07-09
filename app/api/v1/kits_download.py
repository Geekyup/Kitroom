from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.api.deps import get_kit_service
from app.services.kit_service import KitService

router = APIRouter(prefix="/kits", tags=["kits"])


@router.get("/{slug}/download")
async def download_kit(
    slug: str,
    kit_service: KitService = Depends(get_kit_service),
) -> FileResponse:
    kit = await kit_service.get_kit_for_download(slug)
    filename = f"{kit.title}.zip"

    return FileResponse(
        path=kit.original_zip_path,
        media_type="application/zip",
        filename=filename,
    )