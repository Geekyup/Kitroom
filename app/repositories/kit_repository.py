from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import KitNotFound
from app.db.models.drum_kit import DrumKit, KitStatus


class KitRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        owner_id: int,
        title: str,
        slug: str,
        original_zip_path: str,
        size_bytes: int,
        genre: str,
        tags: list[str],
        description: str | None,
    ) -> DrumKit:
        kit = DrumKit(
            owner_id=owner_id,
            title=title,
            slug=slug,
            original_zip_path=original_zip_path,
            size_bytes=size_bytes,
            status=KitStatus.PENDING,
            genre=genre,
            tags=tags,
            description=description,
        )
        self.db.add(kit)
        await self.db.commit()
        await self.db.refresh(kit)
        return kit

    async def get_by_id(self, kit_id: int) -> DrumKit:
        kit = await self.db.get(DrumKit, kit_id)
        if kit is None:
            raise KitNotFound()
        return kit

    async def get_by_slug(self, slug: str) -> DrumKit:
        result = await self.db.execute(
            select(DrumKit).options(selectinload(DrumKit.owner)).where(DrumKit.slug == slug)
        )
        kit = result.scalar_one_or_none()
        if kit is None:
            raise KitNotFound()
        return kit

    async def list_ready(self, limit: int = 50, offset: int = 0) -> list[DrumKit]:
        result = await self.db.execute(
            select(DrumKit)
            .options(selectinload(DrumKit.owner))
            .where(DrumKit.status == KitStatus.READY)
            .order_by(DrumKit.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        kit_id: int,
        status: KitStatus,
        error_message: str | None = None,
    ) -> None:
        kit = await self.get_by_id(kit_id)
        kit.status = status
        kit.error_message = error_message
        await self.db.commit()

    async def update_sound_count(self, kit_id: int, count: int) -> None:
        kit = await self.get_by_id(kit_id)
        kit.sound_count = count
        await self.db.commit()

    async def update_cover(self, kit_id: int, cover_path: str) -> None:
        kit = await self.get_by_id(kit_id)
        kit.cover_path = cover_path
        await self.db.commit()

    async def update_fields(
        self,
        kit_id: int,
        title: str | None = None,
        genre: str | None = None,
        tags: list[str] | None = None,
        description: str | None = None,
    ) -> DrumKit:
        kit = await self.get_by_id(kit_id)
        if title is not None:
            kit.title = title
        if genre is not None:
            kit.genre = genre
        if tags is not None:
            kit.tags = tags
        if description is not None:
            kit.description = description
        await self.db.commit()
        await self.db.refresh(kit)
        return kit

    async def increment_downloads(self, kit_id: int) -> None:
        kit = await self.get_by_id(kit_id)
        kit.downloads_count += 1
        await self.db.commit()

    async def delete(self, kit_id: int) -> None:
        kit = await self.get_by_id(kit_id)
        await self.db.delete(kit)
        await self.db.commit()

    async def list_ready_by_owner(self, owner_id: int, limit: int = 50, offset: int = 0) -> list[DrumKit]:
        result = await self.db.execute(
            select(DrumKit)
            .options(selectinload(DrumKit.owner))
            .where(DrumKit.status == KitStatus.READY, DrumKit.owner_id == owner_id)
            .order_by(DrumKit.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def list_by_owner(self, owner_id: int, limit: int = 50, offset: int = 0) -> list[DrumKit]:
        result = await self.db.execute(
            select(DrumKit)
            .options(selectinload(DrumKit.owner))
            .where(DrumKit.owner_id == owner_id)
            .order_by(DrumKit.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())