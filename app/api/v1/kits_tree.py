from fastapi import APIRouter, Depends

from app.api.deps import get_kit_service
from app.schemas.node import KitTreeOut
from app.services.kit_service import KitService

router = APIRouter(prefix="/kits", tags=["kits"])


@router.get("/{slug}/tree", response_model=KitTreeOut)
async def get_kit_tree(
    slug: str,
    kit_service: KitService = Depends(get_kit_service),
) -> KitTreeOut:
    kit, tree = await kit_service.get_kit_tree(slug)
    return KitTreeOut(kit_slug=kit.slug, kit_title=kit.title, root=tree)