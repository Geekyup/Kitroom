from app.db.models.drum_kit import KitStatus
from app.db.models.drum_kit_node import NodeType
from app.db.session import async_session_factory
from app.repositories.kit_repository import KitRepository
from app.repositories.node_repository import NodeRepository
from app.services.archive_service import ArchiveService
from app.core.exceptions import AppException


async def process_kit(ctx: dict, kit_id: int) -> None:
    async with async_session_factory() as db:
        kit_repo = KitRepository(db)
        node_repo = NodeRepository(db)

        kit = await kit_repo.get_by_id(kit_id)
        await kit_repo.update_status(kit_id, KitStatus.PROCESSING)

        try:
            archive_service = ArchiveService()
            nodes = archive_service.extract_and_validate(
                zip_path=kit.original_zip_path,
                kit_id=kit_id,
            )
            await node_repo.bulk_insert(nodes)

            sound_count = sum(1 for n in nodes if n.node_type == NodeType.FILE)
            await kit_repo.update_sound_count(kit_id, sound_count)

            await kit_repo.update_status(kit_id, KitStatus.READY)

        except AppException as e:
            await kit_repo.update_status(kit_id, KitStatus.FAILED, error_message=e.detail)

        except Exception as e:
            await kit_repo.update_status(kit_id, KitStatus.FAILED, error_message=f"Unexpected error: {e}")