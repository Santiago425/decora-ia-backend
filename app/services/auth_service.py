from datetime import UTC, datetime

from app.core.security import PasswordHasher, TokenService
from app.models import User, UserRole
from app.repositories import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse

_DUMMY_HASH = PasswordHasher.hash("timing-protection-placeholder")


class AuthError(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AuthService:
    def __init__(self, users: UserRepository) -> None:
        self.users = users

    def register(self, data: RegisterRequest) -> TokenResponse:
        email = data.email.lower()
        if self.users.get_by_email(email):
            raise AuthError("Ya existe una cuenta con ese correo", 409)
        user = self.users.add(
            User(full_name=data.full_name, email=email, password_hash=PasswordHasher.hash(data.password), role=UserRole.USER)
        )
        return self._session_for(user)

    def login(self, data: LoginRequest) -> TokenResponse:
        user = self.users.get_by_email(data.email)
        valid = PasswordHasher.verify(data.password, user.password_hash if user else _DUMMY_HASH)
        if not user or not valid or not user.is_active:
            raise AuthError("Correo o contraseña incorrectos", 401)
        if user.role != data.role:
            message = "Esta cuenta no tiene acceso de administrador" if data.role == UserRole.ADMIN else "Usa el acceso de administrador para esta cuenta"
            raise AuthError(message, 403)
        user.last_login_at = datetime.now(UTC)
        self.users.save(user)
        return self._session_for(user)

    @staticmethod
    def _session_for(user: User) -> TokenResponse:
        token, expires_in = TokenService.create(str(user.id), user.role.value)
        return TokenResponse(access_token=token, expires_in=expires_in, user=UserResponse.model_validate(user))
