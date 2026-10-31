import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import UserRole

PASSWORD_RULE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).+$")


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr = Field(max_length=160)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("El nombre es muy corto")
        return value

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if not PASSWORD_RULE.match(value):
            raise ValueError("La contraseña debe tener letras y números")
        if len(value.encode()) > 72:
            raise ValueError("La contraseña es demasiado larga")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)
    role: UserRole = UserRole.USER


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str
    role: UserRole
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
