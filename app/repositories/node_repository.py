from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.drum_kit_node import DrumKitNode


class NodeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def delete_by_kit(self, kit_id: int) -> None:
        """
        Удаляет все ноды кита перед (ре)обработкой — делает process_kit
        идемпотентным на ретраях arq: если предыдущая попытка успела
        частично закоммитить ноды перед тем как задача зависла/упала
        (например при обрыве соединения к БД), повторный bulk_insert
        не словит дубликаты/ошибку уникальности.
        """
        await self.db.execute(delete(DrumKitNode).where(DrumKitNode.kit_id == kit_id))
        await self.db.commit()

    async def bulk_insert(self, nodes: list[DrumKitNode]) -> None:
        self.db.add_all(nodes)
        await self.db.commit()

    async def get_flat_nodes(self, kit_id: int) -> list[DrumKitNode]:
        """
        Забирает все узлы кита одним плоским запросом.
        Иерархия (parent_id -> children) собирается в сервисе, не в SQL —
        recursive CTE тут избыточен, т.к. без ограничения по глубине
        обычный WHERE kit_id = X и так возвращает всё дерево за один SELECT.
        """
        result = await self.db.execute(
            select(DrumKitNode)
            .where(DrumKitNode.kit_id == kit_id)
            .order_by(DrumKitNode.order_index)
        )
        return list(result.scalars().all())