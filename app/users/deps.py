from fastapi import Depends

from app.auth.deps import get_token_repository, get_user_repository
from app.auth.repository import RefreshTokenRepository, UserRepository
from app.storage.deps import get_storage
from app.storage.factory import StorageBackend
from app.users.service import UserService


def get_user_service(
    user_repo: UserRepository = Depends(get_user_repository),
    token_repo: RefreshTokenRepository = Depends(get_token_repository),
    storage: StorageBackend = Depends(get_storage),
) -> UserService:
    return UserService(user_repo, token_repo, storage)
