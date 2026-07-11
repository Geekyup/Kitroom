from typing import Annotated

import jwt
from arq.connections import ArqRedis
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import InactiveUser, InvalidToken, TokenExpired, WrongTokenType
from app.db.models.user import User
from app.db.session import get_db
from app.repositories.auth import RefreshTokenRepository, UserRepository
from app.repositories.verification import VerificationCodeRepository
from app.repositories.kit_repository import KitRepository
from app.repositories.node_repository import NodeRepository
from app.services.auth import AuthService
from app.services.user import UserService
from app.services.kit_service import KitService
from app.storage.b2 import b2_storage, B2StorageBackend

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# --- Auth dependencies ---

def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_token_repository(db: AsyncSession = Depends(get_db)) -> RefreshTokenRepository:
    return RefreshTokenRepository(db)


def get_verification_repository(
    db: AsyncSession = Depends(get_db),
) -> VerificationCodeRepository:
    return VerificationCodeRepository(db)


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
    token_repo: RefreshTokenRepository = Depends(get_token_repository),
    verification_repo: VerificationCodeRepository = Depends(get_verification_repository),
) -> AuthService:
    return AuthService(user_repo, token_repo, verification_repo)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_repo: UserRepository = Depends(get_user_repository),
) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise TokenExpired()
    except jwt.InvalidTokenError:
        raise InvalidToken()

    if payload.get("type") != "access":
        raise WrongTokenType()

    user = await user_repo.get_by_id(int(payload["sub"]))
    if not user:
        raise InvalidToken()

    return user


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    if not user.is_active:
        raise InactiveUser()
    return user


def get_storage() -> B2StorageBackend:
    return b2_storage


def get_user_service(
    user_repo: UserRepository = Depends(get_user_repository),
    token_repo: RefreshTokenRepository = Depends(get_token_repository),
    storage: B2StorageBackend = Depends(get_storage),
) -> UserService:
    return UserService(user_repo, token_repo, storage)


# --- Drumkit dependencies ---

async def get_arq_pool(request: Request) -> ArqRedis:
    return request.app.state.arq_pool


async def get_kit_repository(db: AsyncSession = Depends(get_db)) -> KitRepository:
    return KitRepository(db)


async def get_node_repository(db: AsyncSession = Depends(get_db)) -> NodeRepository:
    return NodeRepository(db)


async def get_kit_service(
    kit_repo: KitRepository = Depends(get_kit_repository),
    node_repo: NodeRepository = Depends(get_node_repository),
    storage: B2StorageBackend = Depends(get_storage),
    arq_pool: ArqRedis = Depends(get_arq_pool),
) -> KitService:
    return KitService(kit_repo, node_repo, storage, arq_pool)