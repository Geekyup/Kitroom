from fastapi import APIRouter, Depends, Query

from app.api.deps import get_kit_service, get_storage, get_user_repository
from app.core.exceptions import UserNotFound
from app.repositories.auth import UserRepository
from app.schemas.kit import KitCatalogItemOut
from app.schemas.user import UserPublicOut
from app.services.kit_service import KitService
from app.storage.factory import StorageBackend

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{username}", response_model=UserPublicOut)
async def get_public_profile(
    username: str,
    user_repo: UserRepository = Depends(get_user_repository),
    storage: StorageBackend = Depends(get_storage),
) -> UserPublicOut:
    """Публичный профиль автора — без email, доступен любому посетителю
    (используется страницей /profile/{username} и кликом по автору кита)."""
    user = await user_repo.get_by_username(username)
    if user is None:
        raise UserNotFound()
    # avatar_path в БД — это сырой object key ("avatars/1/avatar.jpg"), а не
    # готовый URL. Фронт (<img src=...>) ожидает либо presigned S3-ссылку,
    # либо путь на /static — оба резолвятся через storage.get_url(), как и
    # cover_path/owner_avatar_path в kit_service.py. Без этого шага браузер
    # пытался грузить путь как есть, относительно текущей страницы, и
    # получал 404 → битая иконка изображения вместо аватарки.
    avatar_url = await storage.get_url(user.avatar_path) if user.avatar_path else None
    return UserPublicOut(id=user.id, username=user.username, avatar_path=avatar_url)


@router.get("/{username}/kits", response_model=list[KitCatalogItemOut])
async def get_public_kits(
    username: str,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    user_repo: UserRepository = Depends(get_user_repository),
    kit_service: KitService = Depends(get_kit_service),
) -> list[KitCatalogItemOut]:
    """Только READY киты автора — PENDING/PROCESSING/FAILED это
    приватная информация, видимая только самому владельцу через /kits/me."""
    user = await user_repo.get_by_username(username)
    if user is None:
        raise UserNotFound()
    return await kit_service.list_by_username(owner_id=user.id, limit=limit, offset=offset)