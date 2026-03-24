from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
import hashlib

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import Settings


class SecurityManager:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=12,
        )

    def _pre_hash(self, password: str) -> str:
        """
        Предварительное хеширование (SHA-256),
        чтобы обойти ограничение bcrypt в 72 байта
        """
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def hash_password(self, password: str) -> str:
        password_hash = self._pre_hash(password)
        return self._pwd_context.hash(password_hash)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        password_hash = self._pre_hash(plain_password)
        return self._pwd_context.verify(password_hash, hashed_password)

    def create_access_token(self, subject: str) -> str:
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=self._settings.jwt_exp_minutes
        )
        payload: dict[str, Any] = {
            "sub": subject,
            "exp": expires_at,
        }
        return jwt.encode(
            payload,
            self._settings.jwt_secret,
            algorithm=self._settings.jwt_algorithm,
        )

    def decode_token(self, token: str) -> dict[str, Any] | None:
        try:
            return jwt.decode(
                token,
                self._settings.jwt_secret,
                algorithms=[self._settings.jwt_algorithm],
            )
        except JWTError:
            return None