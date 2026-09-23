from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.exceptions import InactiveUser, InvalidToken, TokenExpired, WrongTokenType
from app.auth.models import User
from app.auth.repository import RefreshTokenRepository, UserRepository, VerificationCodeRepository
from app.auth.service import AuthService
from app.core.config import settings
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


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
