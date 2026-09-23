from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.auth.deps import get_current_active_user, get_user_repository
from app.auth.exceptions import UserNotFound
from app.auth.models import User
from app.auth.repository import UserRepository
from app.kits.deps import get_kit_service
from app.kits.schemas import KitCatalogItemOut
from app.kits.service import KitService
from app.storage.deps import get_storage
from app.storage.factory import StorageBackend
from app.users.deps import get_user_service
from app.users.schemas import UserPublicOut, UserRead, UserUpdateUsername
from app.users.service import UserService

router = APIRouter()


@router.get("/me", response_model=UserRead)
async def get_me(
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
):
    return await _serialize_user(current_user, user_service)


@router.post("/me/avatar", response_model=UserRead)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
):
    updated = await user_service.update_avatar(current_user, file)
    return await _serialize_user(updated, user_service)


@router.patch("/me/username", response_model=UserRead)
async def update_username(
    data: UserUpdateUsername,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
):
    updated = await user_service.update_username(current_user, data.username)
    return await _serialize_user(updated, user_service)


async def _serialize_user(user: User, user_service: UserService) -> UserRead:
    out = UserRead.model_validate(user)
    if user.avatar_path:
        out.avatar_path = await user_service.storage.get_url(user.avatar_path)
    return out


public_router = APIRouter(prefix="/users", tags=["users"])


@public_router.get("/{username}", response_model=UserPublicOut)
async def get_public_profile(
    username: str,
    user_repo: UserRepository = Depends(get_user_repository),
    storage: StorageBackend = Depends(get_storage),
) -> UserPublicOut:
    user = await user_repo.get_by_username(username)
    if user is None:
        raise UserNotFound()
    avatar_url = await storage.get_url(user.avatar_path) if user.avatar_path else None
    return UserPublicOut(id=user.id, username=user.username, avatar_path=avatar_url)


@public_router.get("/{username}/kits", response_model=list[KitCatalogItemOut])
async def get_public_kits(
    username: str,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    user_repo: UserRepository = Depends(get_user_repository),
    kit_service: KitService = Depends(get_kit_service),
) -> list[KitCatalogItemOut]:
    user = await user_repo.get_by_username(username)
    if user is None:
        raise UserNotFound()
    return await kit_service.list_by_username(owner_id=user.id, limit=limit, offset=offset)
