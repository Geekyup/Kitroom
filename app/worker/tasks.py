import logging

from app.db.models.drum_kit import KitStatus
from app.db.models.drum_kit_node import NodeType
from app.db.session import async_session_factory
from app.repositories.kit_repository import KitRepository
from app.repositories.node_repository import NodeRepository
from app.services.archive_service import ArchiveService
from app.core.exceptions import AppException

logger = logging.getLogger("kitroom.worker")


async def process_kit(ctx: dict, kit_id: int) -> None:
    logger.info("kit=%s process_kit СТАРТ", kit_id)
    async with async_session_factory() as db:
        kit_repo = KitRepository(db)
        node_repo = NodeRepository(db)

        kit = await kit_repo.get_by_id(kit_id)
        logger.info("kit=%s найден в БД, original_zip_path=%s", kit_id, kit.original_zip_path)
        await kit_repo.update_status(kit_id, KitStatus.PROCESSING)
        logger.info("kit=%s статус -> PROCESSING", kit_id)

        try:
            # Чистим ноды от возможной предыдущей незавершённой попытки —
            # делает ретрай (arq max_tries) идемпотентным.
            await node_repo.delete_by_kit(kit_id)

            archive_service = ArchiveService()
            nodes = await archive_service.extract_and_validate(
                zip_key=kit.original_zip_path,
                kit_id=kit_id,
            )
            await node_repo.bulk_insert(nodes)

            sound_count = sum(1 for n in nodes if n.node_type == NodeType.FILE)
            await kit_repo.update_sound_count(kit_id, sound_count)

            await kit_repo.update_status(kit_id, KitStatus.READY)

        except AppException as e:
            try:
                await kit_repo.update_status(kit_id, KitStatus.FAILED, error_message=e.detail)
            except Exception:
                # Если и запись статуса FAILED не проходит (например БД
                # всё ещё недоступна) — не глушим ошибку молча, пусть
                # arq увидит краш и сам ретраит по своей политике.
                raise

        except Exception as e:
            try:
                await kit_repo.update_status(
                    kit_id, KitStatus.FAILED, error_message=f"Unexpected error: {e}"
                )
            except Exception:
                raise