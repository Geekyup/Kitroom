from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.drum_kit_node import DrumKitNode


class NodeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def delete_by_kit(self, kit_id: int) -> None:
        await self.db.execute(delete(DrumKitNode).where(DrumKitNode.kit_id == kit_id))
        await self.db.commit()

    async def bulk_insert(self, nodes: list[DrumKitNode]) -> None:
        self.db.add_all(nodes)
        await self.db.commit()

    async def get_flat_nodes(self, kit_id: int) -> list[DrumKitNode]:
        result = await self.db.execute(
            select(DrumKitNode)
            .where(DrumKitNode.kit_id == kit_id)
            .order_by(DrumKitNode.order_index)
        )
        return list(result.scalars().all())