from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.settings import get_settings


class PasswordHasher:
    @staticmethod
    def hash(password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def verify(password: str, password_hash: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode(), password_hash.encode())
        except ValueError:
            return False


class TokenService:
    @staticmethod
    def create(subject: str, role: str) -> tuple[str, int]:
        settings = get_settings()
        expires_in = settings.jwt_expire_minutes * 60
        now = datetime.now(UTC)
        payload = {"sub": subject, "role": role, "iat": now, "exp": now + timedelta(seconds=expires_in)}
        return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm), expires_in

    @staticmethod
    def decode(token: str) -> dict:
        settings = get_settings()
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm], options={"require": ["sub", "exp"]})
