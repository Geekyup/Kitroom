from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.deps import get_current_active_user, get_kit_service
from app.db.models.user import User
from app.schemas.kit import KitCatalogItemOut, KitOut, KitStatusOut, KitUpdate
from app.services.kit_service import KitService

router = APIRouter(prefix="/kits", tags=["kits"])


@router.post("", response_model=KitOut, status_code=201)
async def upload_kit(
    title: str = Form(...),
    genre: str = Form(...),
    tags: str = Form(""),
    description: str | None = Form(None),
    file: UploadFile = File(...),
    cover: UploadFile | None = File(None),
    current_user: User = Depends(get_current_active_user),
    kit_service: KitService = Depends(get_kit_service),
) -> KitOut:
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    kit = await kit_service.create_kit(
        owner_id=current_user.id,
        title=title,
        genre=genre,
        tags=tag_list,
        description=description,
        file=file,
        cover=cover,
    )
    return KitOut.model_validate(kit)


@router.get("", response_model=list[KitCatalogItemOut])
async def list_catalog(
    limit: int = 50,
    offset: int = 0,
    kit_service: KitService = Depends(get_kit_service),
) -> list[KitCatalogItemOut]:
    return await kit_service.list_catalog(limit=limit, offset=offset)


@router.get("/me", response_model=list[KitCatalogItemOut])
async def list_my_kits(
    current_user: User = Depends(get_current_active_user),
    kit_service: KitService = Depends(get_kit_service),
) -> list[KitCatalogItemOut]:
    return await kit_service.list_my_kits(owner_id=current_user.id)


@router.get("/{slug}", response_model=KitOut)
async def get_kit(
    slug: str,
    kit_service: KitService = Depends(get_kit_service),
) -> KitOut:
    return await kit_service.get_kit_detail(slug)


@router.get("/{slug}/status", response_model=KitStatusOut)
async def get_kit_status(
    slug: str,
    kit_service: KitService = Depends(get_kit_service),
) -> KitStatusOut:
    kit = await kit_service.get_kit_status(slug)
    return KitStatusOut.model_validate(kit)


@router.patch("/{slug}", response_model=KitOut)
async def update_kit(
    slug: str,
    payload: KitUpdate,
    current_user: User = Depends(get_current_active_user),
    kit_service: KitService = Depends(get_kit_service),
) -> KitOut:
    return await kit_service.update_kit(
        slug,
        requester_id=current_user.id,
        title=payload.title,
        genre=payload.genre,
        tags=payload.tags,
        description=payload.description,
    )


@router.delete("/{slug}", status_code=204)
async def delete_kit(
    slug: str,
    current_user: User = Depends(get_current_active_user),
    kit_service: KitService = Depends(get_kit_service),
) -> None:
    await kit_service.delete_kit(slug, requester_id=current_user.id)