from arq.connections import ArqRedis
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.kits.repository import KitRepository, NodeRepository
from app.kits.service import KitService
from app.storage.deps import get_storage
from app.storage.factory import StorageBackend


async def get_kit_repository(db: AsyncSession = Depends(get_db)) -> KitRepository:
    return KitRepository(db)


async def get_node_repository(db: AsyncSession = Depends(get_db)) -> NodeRepository:
    return NodeRepository(db)


async def get_arq_pool(request: Request) -> ArqRedis:
    return request.app.state.arq_pool


async def get_kit_service(
    kit_repo: KitRepository = Depends(get_kit_repository),
    node_repo: NodeRepository = Depends(get_node_repository),
    storage: StorageBackend = Depends(get_storage),
    arq_pool: ArqRedis = Depends(get_arq_pool),
) -> KitService:
    return KitService(kit_repo, node_repo, storage, arq_pool)
