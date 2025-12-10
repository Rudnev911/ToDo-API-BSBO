from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional
from models.user import UserRole


# Схема регистрации нового пользователя
class UserCreate(BaseModel):
    nickname: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Никнейм пользователя"
    )
    email: EmailStr = Field(
        ...,
        description="Email пользователя"
    )
    password: str = Field(
        ...,
        min_length=6,
        description="Пароль (минимум 6 символов)"
    )


# Схема для входа
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# Схема ответа с информацией о пользователе
class UserResponse(BaseModel):
    id: int
    nickname: str
    email: str
    role: str

    model_config = ConfigDict(from_attributes=True)


# Схема ответа с токеном
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Данные, извлекаемые из токена
class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[str] = None


# Схема для админского списка пользователей с количеством задач
class UserWithTaskCount(BaseModel):
    id: int
    nickname: str
    email: str
    role: str
    task_count: int

    model_config = ConfigDict(from_attributes=True)