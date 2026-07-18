from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import jwt
import pytest

from app.core.config import settings
from app.core.exceptions import (
    EmailAlreadyVerified,
    EmailNotVerified,
    InactiveUser,
    InvalidCredentials,
    InvalidVerificationCode,
    TokenExpired,
    TokenRevoked,
    UserAlreadyExists,
    UsernameAlreadyExists,
    WrongTokenType,
)
from app.core.security import create_access_token, create_refresh_token, hash_password
from app.services.auth import AuthService


def make_user(
    id=1,
    email="user@example.com",
    username="testuser",
    hashed_password=None,
    is_active=True,
    is_verified=True,
    google_id=None,
):
    return SimpleNamespace(
        id=id,
        email=email,
        username=username,
        hashed_password=hashed_password or hash_password("correct-password"),
        is_active=is_active,
        is_verified=is_verified,
        google_id=google_id,
    )


def make_refresh_token_record(user_id=1, token_hash="hash", revoked=False, expires_in_days=30):
    return SimpleNamespace(
        id=1,
        user_id=user_id,
        token_hash=token_hash,
        revoked=revoked,
        expires_at=datetime.now(timezone.utc) + timedelta(days=expires_in_days),
    )


@pytest.fixture
def user_repo():
    repo = AsyncMock()
    repo.get_by_email = AsyncMock(return_value=None)
    repo.get_by_username = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def token_repo():
    return AsyncMock()


@pytest.fixture
def verification_repo():
    return AsyncMock()


@pytest.fixture
def auth_service(user_repo, token_repo, verification_repo):
    return AuthService(user_repo, token_repo, verification_repo)


class TestRegister:
    async def test_register_creates_user_and_sends_code(self, auth_service, user_repo):
        new_user = make_user(id=5, email="new@example.com", username="newuser")
        user_repo.create.return_value = new_user

        with patch("app.services.auth.send_verification_email") as mock_send:
            result = await auth_service.register("new@example.com", "newuser", "password123")

        assert result is new_user
        user_repo.create.assert_awaited_once()
        mock_send.assert_called_once()

    async def test_register_fails_if_email_taken(self, auth_service, user_repo):
        user_repo.get_by_email.return_value = make_user(email="taken@example.com")

        with pytest.raises(UserAlreadyExists):
            await auth_service.register("taken@example.com", "someuser", "password123")

        user_repo.create.assert_not_called()

    async def test_register_fails_if_username_taken(self, auth_service, user_repo):
        user_repo.get_by_email.return_value = None
        user_repo.get_by_username.return_value = make_user(username="taken")

        with pytest.raises(UsernameAlreadyExists):
            await auth_service.register("new@example.com", "taken", "password123")

        user_repo.create.assert_not_called()


class TestLogin:
    async def test_login_success_returns_token_pair(self, auth_service, user_repo):
        user = make_user(is_active=True, is_verified=True)
        user_repo.get_by_email.return_value = user

        result = await auth_service.login("user@example.com", "correct-password")

        assert result.access_token
        assert result.refresh_token

    async def test_login_fails_with_wrong_password(self, auth_service, user_repo):
        user_repo.get_by_email.return_value = make_user()

        with pytest.raises(InvalidCredentials):
            await auth_service.login("user@example.com", "wrong-password")

    async def test_login_fails_if_user_does_not_exist(self, auth_service, user_repo):
        user_repo.get_by_email.return_value = None

        with pytest.raises(InvalidCredentials):
            await auth_service.login("nobody@example.com", "whatever")

    async def test_login_fails_if_user_inactive(self, auth_service, user_repo):
        user_repo.get_by_email.return_value = make_user(is_active=False)

        with pytest.raises(InactiveUser):
            await auth_service.login("user@example.com", "correct-password")

    async def test_login_fails_if_email_not_verified(self, auth_service, user_repo):
        user_repo.get_by_email.return_value = make_user(is_verified=False)

        with pytest.raises(EmailNotVerified):
            await auth_service.login("user@example.com", "correct-password")

    async def test_login_checks_active_before_verified(self, auth_service, user_repo):
        user_repo.get_by_email.return_value = make_user(is_active=False, is_verified=False)

        with pytest.raises(InactiveUser):
            await auth_service.login("user@example.com", "correct-password")


class TestRefreshToken:
    async def test_refresh_success_rotates_token(self, auth_service, token_repo):
        refresh_token = create_refresh_token(subject="1")
        stored = make_refresh_token_record(user_id=1, revoked=False)
        token_repo.get_by_hash.return_value = stored

        result = await auth_service.refresh(refresh_token)

        assert result.access_token
        assert result.refresh_token
        token_repo.revoke.assert_awaited_once_with(stored)

    async def test_refresh_fails_if_token_expired_jwt(self, auth_service):
        past = datetime.now(timezone.utc) - timedelta(days=1)
        expired_payload = {
            "sub": "1",
            "type": "refresh",
            "iat": past - timedelta(days=1),
            "exp": past,
        }
        expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        with pytest.raises(TokenExpired):
            await auth_service.refresh(expired_token)

    async def test_refresh_fails_with_access_token_instead_of_refresh(self, auth_service):
        access_token = create_access_token(subject="1")

        with pytest.raises(WrongTokenType):
            await auth_service.refresh(access_token)

    async def test_refresh_fails_if_token_not_found_in_db(self, auth_service, token_repo):
        refresh_token = create_refresh_token(subject="1")
        token_repo.get_by_hash.return_value = None

        with pytest.raises(TokenRevoked):
            await auth_service.refresh(refresh_token)
        token_repo.revoke_all_for_user.assert_awaited_once_with(1)

    async def test_refresh_fails_if_token_already_revoked(self, auth_service, token_repo):
        refresh_token = create_refresh_token(subject="1")
        stored = make_refresh_token_record(user_id=1, revoked=True)
        token_repo.get_by_hash.return_value = stored

        with pytest.raises(TokenRevoked):
            await auth_service.refresh(refresh_token)

        token_repo.revoke_all_for_user.assert_awaited_once_with(1)

    async def test_refresh_fails_if_stored_token_expired_in_db(self, auth_service, token_repo):
        refresh_token = create_refresh_token(subject="1")
        stored = make_refresh_token_record(user_id=1, revoked=False, expires_in_days=-1)
        token_repo.get_by_hash.return_value = stored

        with pytest.raises(TokenExpired):
            await auth_service.refresh(refresh_token)


class TestLogout:
    async def test_logout_revokes_token_if_found_and_active(self, auth_service, token_repo):
        stored = make_refresh_token_record(revoked=False)
        token_repo.get_by_hash.return_value = stored

        await auth_service.logout("some-refresh-token")

        token_repo.revoke.assert_awaited_once_with(stored)

    async def test_logout_is_noop_if_token_not_found(self, auth_service, token_repo):
        token_repo.get_by_hash.return_value = None

        await auth_service.logout("unknown-token")

        token_repo.revoke.assert_not_called()

    async def test_logout_is_noop_if_already_revoked(self, auth_service, token_repo):
        stored = make_refresh_token_record(revoked=True)
        token_repo.get_by_hash.return_value = stored

        await auth_service.logout("already-revoked-token")

        token_repo.revoke.assert_not_called()


class TestGoogleLogin:
    async def test_creates_new_user_when_no_match(self, auth_service, user_repo):
        user_repo.get_by_google_id.return_value = None
        user_repo.get_by_email.return_value = None
        user_repo.get_by_username.return_value = None
        new_user = make_user(id=10, email="google@example.com", google_id="g-123")
        user_repo.create_oauth_user.return_value = new_user

        result = await auth_service.login_with_google("g-123", "google@example.com")

        assert result.access_token
        user_repo.create_oauth_user.assert_awaited_once()
        user_repo.mark_verified.assert_awaited_once_with(new_user)

    async def test_links_google_id_to_existing_email_account(self, auth_service, user_repo):
        existing = make_user(id=7, email="existing@example.com", google_id=None)
        user_repo.get_by_google_id.return_value = None
        user_repo.get_by_email.return_value = existing
        user_repo.link_google_id.return_value = existing

        result = await auth_service.login_with_google("g-456", "existing@example.com")

        assert result.access_token
        user_repo.link_google_id.assert_awaited_once_with(existing, "g-456")
        user_repo.create_oauth_user.assert_not_called()

    async def test_uses_existing_google_linked_user_directly(self, auth_service, user_repo):
        linked_user = make_user(id=3, google_id="g-789")
        user_repo.get_by_google_id.return_value = linked_user

        result = await auth_service.login_with_google("g-789", "user@example.com")

        assert result.access_token
        user_repo.get_by_email.assert_not_called()

    async def test_fails_if_linked_user_is_inactive(self, auth_service, user_repo):
        inactive_user = make_user(is_active=False, google_id="g-999")
        user_repo.get_by_google_id.return_value = inactive_user

        with pytest.raises(InactiveUser):
            await auth_service.login_with_google("g-999", "user@example.com")

    async def test_generates_unique_username_on_conflict(self, auth_service, user_repo):
        user_repo.get_by_google_id.return_value = None
        user_repo.get_by_email.return_value = None
        # первая попытка "bob" занята, "bob1" свободна
        user_repo.get_by_username.side_effect = [make_user(username="bob"), None]
        created_user = make_user(id=20, username="bob1")
        user_repo.create_oauth_user.return_value = created_user

        await auth_service.login_with_google("g-1", "bob@example.com")

        _, kwargs = user_repo.create_oauth_user.call_args
        assert kwargs["username"] == "bob1"


class TestEmailVerification:
    async def test_verify_email_success(self, auth_service, user_repo, verification_repo):
        user = make_user(is_verified=False)
        user_repo.get_by_email.return_value = user
        record = SimpleNamespace(id=1, used=False)
        verification_repo.get_valid_code.return_value = record

        await auth_service.verify_email("user@example.com", "123456")

        verification_repo.mark_used.assert_awaited_once_with(record)
        user_repo.mark_verified.assert_awaited_once_with(user)

    async def test_verify_email_fails_with_invalid_code(self, auth_service, user_repo, verification_repo):
        user_repo.get_by_email.return_value = make_user(is_verified=False)
        verification_repo.get_valid_code.return_value = None

        with pytest.raises(InvalidVerificationCode):
            await auth_service.verify_email("user@example.com", "000000")

    async def test_verify_email_fails_if_user_not_found(self, auth_service, user_repo):
        user_repo.get_by_email.return_value = None

        with pytest.raises(InvalidVerificationCode):
            await auth_service.verify_email("nobody@example.com", "123456")

    async def test_resend_verification_fails_if_already_verified(self, auth_service, user_repo):
        user_repo.get_by_email.return_value = make_user(is_verified=True)

        with pytest.raises(EmailAlreadyVerified):
            await auth_service.resend_verification_code("user@example.com")

    async def test_resend_verification_is_silent_if_user_not_found(self, auth_service, user_repo):
        user_repo.get_by_email.return_value = None
        await auth_service.resend_verification_code("nobody@example.com")


class TestPasswordReset:
    async def test_forgot_password_is_silent_if_user_not_found(self, auth_service, user_repo):
        user_repo.get_by_email.return_value = None
        await auth_service.forgot_password("nobody@example.com")

    async def test_reset_password_success_revokes_all_tokens(
        self, auth_service, user_repo, verification_repo, token_repo
    ):
        user = make_user()
        user_repo.get_by_email.return_value = user
        record = SimpleNamespace(id=1, used=False)
        verification_repo.get_valid_code.return_value = record

        await auth_service.reset_password("user@example.com", "123456", "new-password")

        user_repo.update_password.assert_awaited_once()
        token_repo.revoke_all_for_user.assert_awaited_once_with(user.id)

    async def test_reset_password_fails_with_invalid_code(self, auth_service, user_repo, verification_repo):
        user_repo.get_by_email.return_value = make_user()
        verification_repo.get_valid_code.return_value = None

        with pytest.raises(InvalidVerificationCode):
            await auth_service.reset_password("user@example.com", "000000", "new-password")
