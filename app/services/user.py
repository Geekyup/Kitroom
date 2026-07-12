from fastapi import UploadFile

from app.core.exceptions import InvalidCredentials, SamePassword, UserAlreadyExists
from app.core.security import hash_password, verify_password
from app.db.models.user import User
from app.repositories.auth import RefreshTokenRepository, UserRepository
from app.storage.factory import StorageBackend, get_storage_backend


class UserService:
    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: RefreshTokenRepository,
        storage: StorageBackend | None = None,
    ):
        self.user_repo = user_repo
        self.token_repo = token_repo
        self.storage = storage or get_storage_backend()

    async def update_avatar(self, user: User, file: UploadFile) -> User:
        avatar_path = await self.storage.save_avatar(user.id, file)
        return await self.user_repo.update_avatar(user, avatar_path)

    async def update_email(self, user: User, new_email: str) -> User:
        existing = await self.user_repo.get_by_email(new_email)
        if existing and existing.id != user.id:
            raise UserAlreadyExists()
        return await self.user_repo.update_email(user, new_email)

    async def change_password(
        self, user: User, current_password: str, new_password: str
    ) -> None:
        if not verify_password(current_password, user.hashed_password):
            raise InvalidCredentials()
        if verify_password(new_password, user.hashed_password):
            raise SamePassword()

        await self.user_repo.update_password(user, hash_password(new_password))
        await self.token_repo.revoke_all_for_user(user.id)

    async def delete_account(self, user: User) -> None:
        await self.token_repo.revoke_all_for_user(user.id)
        await self.user_repo.delete(user)