import hashlib
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import VerificationCode


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


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