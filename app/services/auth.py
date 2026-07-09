import hashlib
import random
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings
from app.core.email import send_password_reset_email, send_verification_email
from app.core.exceptions import (
    EmailAlreadyVerified,
    EmailNotVerified,
    InactiveUser,
    InvalidCredentials,
    InvalidToken,
    InvalidVerificationCode,
    TokenExpired,
    TokenRevoked,
    UserAlreadyExists,
    UsernameAlreadyExists,
    WrongTokenType,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.repositories.auth import RefreshTokenRepository, UserRepository
from app.repositories.verification import VerificationCodeRepository
from app.schemas.token import TokenPair


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _generate_code() -> str:
    return f"{random.randint(0, 999999):06d}"


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: RefreshTokenRepository,
        verification_repo: VerificationCodeRepository,
    ):
        self.user_repo = user_repo
        self.token_repo = token_repo
        self.verification_repo = verification_repo

    async def register(self, email: str, username: str, password: str):
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise UserAlreadyExists()

        existing_username = await self.user_repo.get_by_username(username)
        if existing_username:
            raise UsernameAlreadyExists()

        user = await self.user_repo.create(
            email=email, username=username, hashed_password=hash_password(password)
        )
        await self._send_verification_code(user.id, email)
        return user

    async def login(self, email: str, password: str) -> TokenPair:
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise InvalidCredentials()
        if not user.is_active:
            raise InactiveUser()
        if not user.is_verified:
            raise EmailNotVerified()
        return await self._issue_token_pair(user.id)

    async def refresh(self, refresh_token: str) -> TokenPair:
        try:
            payload = jwt.decode(
                refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
        except jwt.ExpiredSignatureError:
            raise TokenExpired()
        except jwt.InvalidTokenError:
            raise InvalidToken()

        if payload.get("type") != "refresh":
            raise WrongTokenType()

        user_id = int(payload["sub"])
        token_hash = _hash_token(refresh_token)
        stored = await self.token_repo.get_by_hash(token_hash)

        if not stored or stored.revoked:
            await self.token_repo.revoke_all_for_user(user_id)
            raise TokenRevoked()

        if stored.expires_at < datetime.now(timezone.utc):
            raise TokenExpired()

        await self.token_repo.revoke(stored)
        return await self._issue_token_pair(user_id)

    async def logout(self, refresh_token: str) -> None:
        token_hash = _hash_token(refresh_token)
        stored = await self.token_repo.get_by_hash(token_hash)
        if stored and not stored.revoked:
            await self.token_repo.revoke(stored)

    async def login_with_google(self, google_id: str, email: str) -> TokenPair:
        user = await self.user_repo.get_by_google_id(google_id)

        if not user:
            existing_by_email = await self.user_repo.get_by_email(email)
            if existing_by_email:
                user = await self.user_repo.link_google_id(existing_by_email, google_id)
            else:
                username = await self._generate_unique_username(email)
                user = await self.user_repo.create_oauth_user(
                    email=email, username=username, google_id=google_id
                )
                await self.user_repo.mark_verified(user)

        if not user.is_active:
            raise InactiveUser()

        return await self._issue_token_pair(user.id)

    async def _generate_unique_username(self, email: str) -> str:
        base = email.split("@")[0]
        candidate = base
        suffix = 1
        while await self.user_repo.get_by_username(candidate):
            candidate = f"{base}{suffix}"
            suffix += 1
        return candidate

    async def _send_verification_code(self, user_id: int, email: str) -> None:
        code = _generate_code()
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.VERIFICATION_CODE_EXPIRE_MINUTES
        )
        await self.verification_repo.create(
            user_id=user_id, code=code, purpose="email_verification", expires_at=expires_at
        )
        send_verification_email(email, code)

    async def verify_email(self, email: str, code: str) -> None:
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise InvalidVerificationCode()

        record = await self.verification_repo.get_valid_code(
            user.id, code, purpose="email_verification"
        )
        if not record:
            raise InvalidVerificationCode()

        await self.verification_repo.mark_used(record)
        await self.user_repo.mark_verified(user)

    async def forgot_password(self, email: str) -> None:
        user = await self.user_repo.get_by_email(email)
        if not user:
            return

        code = _generate_code()
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.PASSWORD_RESET_CODE_EXPIRE_MINUTES
        )
        await self.verification_repo.create(
            user_id=user.id, code=code, purpose="password_reset", expires_at=expires_at
        )
        send_password_reset_email(email, code)

    async def reset_password(self, email: str, code: str, new_password: str) -> None:
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise InvalidVerificationCode()

        record = await self.verification_repo.get_valid_code(
            user.id, code, purpose="password_reset"
        )
        if not record:
            raise InvalidVerificationCode()

        await self.verification_repo.mark_used(record)
        await self.user_repo.update_password(user, hash_password(new_password))
        await self.token_repo.revoke_all_for_user(user.id)

    async def _issue_token_pair(self, user_id: int) -> TokenPair:
        access_token = create_access_token(subject=str(user_id))
        refresh_token = create_refresh_token(subject=str(user_id))

        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        await self.token_repo.create(
            user_id=user_id,
            token_hash=_hash_token(refresh_token),
            expires_at=expires_at,
        )
        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    async def resend_verification_code(self, email: str) -> None:
        user = await self.user_repo.get_by_email(email)
        if not user:
            return
        if user.is_verified:
            raise EmailAlreadyVerified()
        await self._send_verification_code(user.id, email)