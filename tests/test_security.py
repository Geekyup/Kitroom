import time

import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_password_returns_different_string_than_input(self):
        hashed = hash_password("my-secret-password")
        assert hashed != "my-secret-password"

    def test_verify_password_success(self):
        hashed = hash_password("correct-horse-battery-staple")
        assert verify_password("correct-horse-battery-staple", hashed) is True

    def test_verify_password_wrong_password_fails(self):
        hashed = hash_password("correct-horse-battery-staple")
        assert verify_password("wrong-password", hashed) is False

    def test_same_password_produces_different_hashes(self):
        hash1 = hash_password("same-password")
        hash2 = hash_password("same-password")
        assert hash1 != hash2
        assert verify_password("same-password", hash1) is True
        assert verify_password("same-password", hash2) is True


class TestTokens:
    def test_access_token_has_correct_type(self):
        token = create_access_token(subject="42")
        payload = decode_token(token)
        assert payload["type"] == "access"
        assert payload["sub"] == "42"

    def test_refresh_token_has_correct_type(self):
        token = create_refresh_token(subject="42")
        payload = decode_token(token)
        assert payload["type"] == "refresh"
        assert payload["sub"] == "42"

    def test_access_and_refresh_tokens_differ(self):
        access = create_access_token(subject="1")
        refresh = create_refresh_token(subject="1")
        assert access != refresh

    def test_tokens_for_same_subject_have_unique_jti(self):
        token1 = create_access_token(subject="1")
        token2 = create_access_token(subject="1")
        assert token1 != token2
        payload1 = decode_token(token1)
        payload2 = decode_token(token2)
        assert payload1["jti"] != payload2["jti"]

    def test_decode_token_with_wrong_secret_raises(self):
        token = create_access_token(subject="1")
        with pytest.raises(jwt.InvalidTokenError):
            jwt.decode(token, "wrong-secret-key", algorithms=[settings.ALGORITHM])

    def test_decode_expired_token_raises(self):
        now = time.time()
        expired_payload = {
            "sub": "1",
            "type": "access",
            "iat": now - 1000,
            "exp": now - 500,  # уже истёк
        }
        expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_token(expired_token)

    def test_decode_tampered_token_raises(self):
        token = create_access_token(subject="1")
        tampered = token[:-2] + ("aa" if token[-2:] != "aa" else "bb")
        with pytest.raises(jwt.InvalidTokenError):
            decode_token(tampered)
