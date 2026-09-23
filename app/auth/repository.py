import hashlib
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import RefreshToken, User, VerificationCode


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.db.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def create(self, email: str, username: str, hashed_password: str) -> User:
        user = User(email=email, username=username, hashed_password=hashed_password)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_email(self, user: User, new_email: str) -> User:
        user.email = new_email
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_password(self, user: User, new_hashed_password: str) -> User:
        user.hashed_password = new_hashed_password
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        await self.db.delete(user)
        await self.db.commit()

    async def get_by_google_id(self, google_id: str) -> User | None:
        result = await self.db.execute(select(User).where(User.google_id == google_id))
        return result.scalar_one_or_none()

    async def create_oauth_user(self, email: str, username: str, google_id: str) -> User:
        user = User(email=email, username=username, google_id=google_id, hashed_password=None)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def link_google_id(self, user: User, google_id: str) -> User:
        user.google_id = google_id
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_avatar(self, user: User, avatar_path: str) -> User:
        user.avatar_path = avatar_path
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_username(self, user: User, new_username: str) -> User:
        user.username = new_username
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def mark_verified(self, user: User) -> User:
        user.is_verified = True
        await self.db.commit()
        await self.db.refresh(user)
        return user


class RefreshTokenRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: int, token_hash: str, expires_at: datetime) -> RefreshToken:
        token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.db.add(token)
        await self.db.commit()
        await self.db.refresh(token)
        return token

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke(self, token: RefreshToken) -> None:
        token.revoked = True
        await self.db.commit()

    async def revoke_all_for_user(self, user_id: int) -> None:
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
            .values(revoked=True)
        )
        await self.db.commit()


class VerificationCodeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self, user_id: int, code: str, purpose: str, expires_at: datetime
    ) -> VerificationCode:
        record = VerificationCode(
            user_id=user_id,
            code_hash=_hash_code(code),
            purpose=purpose,
            expires_at=expires_at,
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def get_valid_code(
        self, user_id: int, code: str, purpose: str
    ) -> VerificationCode | None:
        result = await self.db.execute(
            select(VerificationCode).where(
                VerificationCode.user_id == user_id,
                VerificationCode.code_hash == _hash_code(code),
                VerificationCode.purpose == purpose,
                VerificationCode.used.is_(False),
            )
        )
        record = result.scalar_one_or_none()
        if record and record.expires_at < datetime.now(timezone.utc):
            return None
        return record

    async def mark_used(self, record: VerificationCode) -> None:
        record.used = True
        await self.db.commit()
