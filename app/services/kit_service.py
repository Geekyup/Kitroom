import re
import uuid

from arq.connections import ArqRedis
from botocore.exceptions import ClientError
from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import ArchiveTooLarge, KitNotReady, NotKitOwner, UploadNotFound
from app.db.models.drum_kit import DrumKit, KitStatus
from app.db.models.drum_kit_node import DrumKitNode
from app.repositories.kit_repository import KitRepository
from app.repositories.node_repository import NodeRepository
from app.schemas.kit import (
    KitCatalogItemOut,
    KitOut,
    KitUploadInitOut,
)
from app.schemas.node import NodeOut
from app.storage.factory import StorageBackend


class KitService:
    def __init__(
        self,
        kit_repo: KitRepository,
        node_repo: NodeRepository,
        storage: StorageBackend,
        arq_pool: ArqRedis,
    ):
        self.kit_repo = kit_repo
        self.node_repo = node_repo
        self.storage = storage
        self.arq_pool = arq_pool

    async def create_kit(
        self,
        owner_id: int,
        title: str,
        genre: str,
        tags: list[str],
        description: str | None,
        file: UploadFile,
        cover: UploadFile | None = None,
    ) -> DrumKit:
        if file.size and file.size > settings.MAX_ZIP_SIZE_MB * 1024 * 1024:
            raise ArchiveTooLarge()

        path = await self.storage.save_upload(file)
        slug = self._generate_slug(title)

        kit = await self.kit_repo.create(
            owner_id=owner_id,
            title=title,
            slug=slug,
            original_zip_path=path,
            size_bytes=file.size or 0,
            genre=genre,
            tags=tags,
            description=description,
        )

        if cover is not None:
            cover_path = await self.storage.save_cover(kit.id, cover)
            await self.kit_repo.update_cover(kit.id, cover_path)

        await self.arq_pool.enqueue_job("process_kit", kit.id)
        return kit

    async def init_kit_upload(
        self,
        owner_id: int,
        title: str,
        genre: str,
        tags: list[str],
        description: str | None,
        content_type: str = "application/zip",
    ) -> KitUploadInitOut:
        object_key = self.storage.generate_upload_key()
        slug = self._generate_slug(title)

        kit = await self.kit_repo.create(
            owner_id=owner_id,
            title=title,
            slug=slug,
            original_zip_path=object_key,
            size_bytes=0,
            genre=genre,
            tags=tags,
            description=description,
        )

        upload_url = await self.storage.get_upload_url(
            key=object_key,
            content_type=content_type,
            expires_in=3600,
        )

        return KitUploadInitOut(
            kit_id=kit.id,
            slug=kit.slug,
            upload_url=upload_url,
            object_key=object_key,
        )

    async def confirm_kit_upload(self, kit_id: int, requester_id: int) -> DrumKit:
        kit = await self.kit_repo.get_by_id(kit_id)

        if kit.owner_id != requester_id:
            raise NotKitOwner()

        try:
            meta = await self.storage.head_object(kit.original_zip_path)
        except (ClientError, FileNotFoundError):
            raise UploadNotFound()

        size_bytes = meta.get("ContentLength", 0)
        if size_bytes > settings.MAX_ZIP_SIZE_MB * 1024 * 1024:
            await self.storage.delete_async(kit.original_zip_path)
            await self.kit_repo.mark_failed(kit.id, "Файл превышает максимальный размер")
            raise ArchiveTooLarge()

        await self.kit_repo.update_size(kit.id, size_bytes)
        await self.arq_pool.enqueue_job("process_kit", kit.id)

        return await self.kit_repo.get_by_id(kit.id)

    async def init_cover_upload(self, kit_id: int, requester_id: int, content_type: str = "image/jpeg"):
        """Presigned PUT для обложки — та же логика, отдельно от zip'а."""
        kit = await self.kit_repo.get_by_id(kit_id)
        if kit.owner_id != requester_id:
            raise NotKitOwner()

        extension = ".jpg" if "jpeg" in content_type else "." + content_type.split("/")[-1]
        object_key = f"kits/{kit_id}/cover{extension}"

        upload_url = await self.storage.get_upload_url(
            key=object_key, content_type=content_type, expires_in=3600
        )
        return object_key, upload_url

    async def confirm_cover_upload(self, kit_id: int, requester_id: int, object_key: str) -> None:
        kit = await self.kit_repo.get_by_id(kit_id)
        if kit.owner_id != requester_id:
            raise NotKitOwner()

        try:
            await self.storage.head_object(object_key)
        except (ClientError, FileNotFoundError):
            raise UploadNotFound()

        await self.kit_repo.update_cover(kit.id, object_key)

    async def get_kit_status(self, slug: str) -> DrumKit:
        return await self.kit_repo.get_by_slug(slug)

    async def get_kit_detail(self, slug: str) -> KitOut:
        kit = await self.kit_repo.get_by_slug(slug)
        out = KitOut.model_validate(kit)
        if kit.cover_path:
            out.cover_path = await self.storage.get_url(kit.cover_path)
        out.owner_id = kit.owner.id
        out.owner_username = kit.owner.username
        if kit.owner.avatar_path:
            out.owner_avatar_path = await self.storage.get_url(kit.owner.avatar_path)
        return out

    async def get_kit_tree(self, slug: str) -> tuple[DrumKit, list[NodeOut]]:
        kit = await self.kit_repo.get_by_slug(slug)

        if kit.status != KitStatus.READY:
            raise KitNotReady()

        flat_nodes = await self.node_repo.get_flat_nodes(kit.id)
        tree = await self._build_tree(flat_nodes)
        return kit, tree

    async def get_kit_for_download(self, slug: str) -> DrumKit:
        kit = await self.kit_repo.get_by_slug(slug)

        if kit.status != KitStatus.READY:
            raise KitNotReady()

        await self.kit_repo.increment_downloads(kit.id)
        return kit

    async def list_catalog(self, limit: int = 50, offset: int = 0) -> list[KitCatalogItemOut]:
        kits = await self.kit_repo.list_ready(limit=limit, offset=offset)
        return [
            KitCatalogItemOut(
                id=kit.id,
                title=kit.title,
                slug=kit.slug,
                author=kit.owner.username,
                owner_username=kit.owner.username,
                owner_avatar_path=(
                    await self.storage.get_url(kit.owner.avatar_path) if kit.owner.avatar_path else None
                ),
                genre=kit.genre,
                tags=kit.tags,
                cover_path=await self.storage.get_url(kit.cover_path) if kit.cover_path else None,
                sound_count=kit.sound_count,
                downloads_count=kit.downloads_count,
                size_bytes=kit.size_bytes,
                status=kit.status,
                error_message=kit.error_message,
            )
            for kit in kits
        ]

    async def list_my_kits(self, owner_id: int, limit: int = 50, offset: int = 0) -> list[KitCatalogItemOut]:
        kits = await self.kit_repo.list_by_owner(owner_id=owner_id, limit=limit, offset=offset)
        return [
            KitCatalogItemOut(
                id=kit.id,
                title=kit.title,
                slug=kit.slug,
                author=kit.owner.username,
                owner_username=kit.owner.username,
                owner_avatar_path=(
                    await self.storage.get_url(kit.owner.avatar_path) if kit.owner.avatar_path else None
                ),
                genre=kit.genre,
                tags=kit.tags,
                cover_path=await self.storage.get_url(kit.cover_path) if kit.cover_path else None,
                sound_count=kit.sound_count,
                downloads_count=kit.downloads_count,
                size_bytes=kit.size_bytes,
                status=kit.status,
                error_message=kit.error_message,
            )
            for kit in kits
        ]

    async def list_by_username(
        self, owner_id: int, limit: int = 50, offset: int = 0
    ) -> list[KitCatalogItemOut]:
        kits = await self.kit_repo.list_ready_by_owner(owner_id=owner_id, limit=limit, offset=offset)
        return [
            KitCatalogItemOut(
                id=kit.id,
                title=kit.title,
                slug=kit.slug,
                author=kit.owner.username,
                owner_username=kit.owner.username,
                owner_avatar_path=(
                    await self.storage.get_url(kit.owner.avatar_path) if kit.owner.avatar_path else None
                ),
                genre=kit.genre,
                tags=kit.tags,
                cover_path=await self.storage.get_url(kit.cover_path) if kit.cover_path else None,
                sound_count=kit.sound_count,
                downloads_count=kit.downloads_count,
                size_bytes=kit.size_bytes,
                status=kit.status,
                error_message=kit.error_message,
            )
            for kit in kits
        ]

    async def update_kit(
        self,
        slug: str,
        requester_id: int,
        title: str | None = None,
        genre: str | None = None,
        tags: list[str] | None = None,
        description: str | None = None,
    ) -> KitOut:
        kit = await self.kit_repo.get_by_slug(slug)

        if kit.owner_id != requester_id:
            raise NotKitOwner()

        updated = await self.kit_repo.update_fields(
            kit.id,
            title=title,
            genre=genre,
            tags=tags,
            description=description,
        )
        out = KitOut.model_validate(updated)
        if updated.cover_path:
            out.cover_path = await self.storage.get_url(updated.cover_path)
        out.owner_id = kit.owner.id
        out.owner_username = kit.owner.username
        if kit.owner.avatar_path:
            out.owner_avatar_path = await self.storage.get_url(kit.owner.avatar_path)
        return out

    async def delete_kit(self, slug: str, requester_id: int) -> None:
        kit = await self.kit_repo.get_by_slug(slug)

        if kit.owner_id != requester_id:
            raise NotKitOwner()

        await self.storage.delete_async(kit.original_zip_path)
        await self.storage.delete_prefix(f"kits/{kit.id}/")
        await self.kit_repo.delete(kit.id)

    def _generate_slug(self, title: str) -> str:
        base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        return f"{base}-{uuid.uuid4().hex[:8]}"

    async def _build_tree(self, nodes: list[DrumKitNode]) -> list[NodeOut]:
        by_id: dict[int, NodeOut] = {}
        for n in nodes:
            sound_url = (
                await self.storage.get_url(n.storage_path)
                if n.storage_path is not None
                else None
            )
            out = NodeOut(
                id=n.id,
                name=n.name,
                node_type=n.node_type,
                file_format=n.file_format,
                duration_ms=n.duration_ms,
                order_index=n.order_index,
                sound_url=sound_url,
                children=[],
            )
            by_id[n.id] = out

        roots: list[NodeOut] = []
        for node in nodes:
            out = by_id[node.id]
            if node.parent_id is None:
                roots.append(out)
            else:
                by_id[node.parent_id].children.append(out)

        return roots