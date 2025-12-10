from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, join
from pydantic import BaseModel

from database import get_db
from models import User, Task
from schemas_auth import UserResponse
from dependencies import get_current_admin
from typing import List
from schemas_auth import UserWithTaskCount


router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)


@router.get("/users", response_model=List[UserWithTaskCount])
async def get_all_users_with_task_count(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Получить список всех пользователей с количеством их задач (только для админов)."""
    
    # Подзапрос: количество задач по user_id
    task_count_subq = (
        select(Task.user_id, func.count(Task.id).label("task_count"))
        .group_by(Task.user_id)
        .subquery()
    )

    # Основной запрос: пользователи + количество задач
    query = (
        select(
            User.id,
            User.nickname,
            User.email,
            User.role,
            func.coalesce(task_count_subq.c.task_count, 0).label("task_count")
        )
        .outerjoin(task_count_subq, User.id == task_count_subq.c.user_id)
        .order_by(User.id)
    )

    result = await db.execute(query)
    users = result.fetchall()

    return [
        UserWithTaskCount(
            id=user.id,
            nickname=user.nickname,
            email=user.email,
            role=user.role.value,
            task_count=user.task_count
        )
        for user in users
    ]