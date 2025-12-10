from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from pydantic import BaseModel, Field
from models import User, UserRole
from schemas_auth import UserCreate, UserResponse, Token
from auth_utils import verify_password, get_password_hash, create_access_token
from dependencies import get_current_user

from database import get_db
from models import User, Task
from dependencies import get_current_user, get_current_admin
from auth_utils import verify_password, get_password_hash

router = APIRouter(
    prefix="/auth",
    tags=["authentication"]
)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Регистрация нового пользователя."""
    # Проверяем, не занят ли email
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )

    # Проверяем, не занят ли nickname
    result = await db.execute(
        select(User).where(User.nickname == user_data.nickname)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким никнеймом уже существует"
        )

    # Создаём нового пользователя
    new_user = User(
        nickname=user_data.nickname,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        role=UserRole.USER  # По умолчанию — обычный пользователь
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Аутентификация пользователя и выдача JWT-токена."""
    # Ищем пользователя по email (в OAuth2 форма использует `username` для email)
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()

    # Проверяем наличие пользователя и корректность пароля
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Создаём JWT-токен с user.id и ролью
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value}
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """Получение информации о текущем авторизованном пользователе."""
    return current_user


# Схема для смены пароля
class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6)


@router.patch("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Сменить пароль (требуется аутентификация)."""
    # Проверяем старый пароль
    if not verify_password(request.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный текущий пароль"
        )
    
    # Хешируем новый пароль
    new_hashed_password = get_password_hash(request.new_password)
    current_user.hashed_password = new_hashed_password

    await db.commit()
    return {"message": "Пароль успешно изменён"}