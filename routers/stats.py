from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from database import get_db
from datetime import datetime, timezone
from schemas import TimingStatsResponse
from models import Task, User
from dependencies import get_current_user  # ← аутентификация и авторизация


router = APIRouter(
    prefix="/stats",
    tags=["statistics"]
)


def apply_user_filter(query, current_user: User):
    """Применяет фильтр по пользователю, если он не админ."""
    if current_user.role.value != "admin":
        return query.where(Task.user_id == current_user.id)
    return query


@router.get("/", response_model=dict)
async def get_tasks_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    """Статистика по задачам: общая для админа, личная — для пользователя."""
    
    # Общее количество задач
    total_query = apply_user_filter(select(func.count(Task.id)), current_user)
    total_result = await db.execute(total_query)
    total_tasks = total_result.scalar()

    # Подсчёт по квадрантам
    quadrant_query = apply_user_filter(
        select(Task.quadrant, func.count(Task.id).label('count')).group_by(Task.quadrant),
        current_user
    )
    quadrant_result = await db.execute(quadrant_query)
    by_quadrant = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}
    for row in quadrant_result:
        by_quadrant[row.quadrant] = row.count

    # Подсчёт по статусу
    completed_case = case(
        ((Task.completed == True, 1),),
        else_=0
    )
    pending_case = case(
        ((Task.completed == False, 1),),
        else_=0
    )
    status_query = apply_user_filter(
        select(
            func.sum(completed_case).label('completed'),
            func.sum(pending_case).label('pending')
        ),
        current_user
    )
    status_result = await db.execute(status_query)
    status_row = status_result.one()

    return {
        "total_tasks": total_tasks,
        "by_quadrant": by_quadrant,
        "by_status": {
            "completed": (status_row.completed or 0),
            "pending": (status_row.pending or 0)
        }
    }


@router.get("/timing", response_model=TimingStatsResponse)
async def get_deadline_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> TimingStatsResponse:
    """Статистика по срокам: админ — по всем задачам, пользователь — по своим."""
    
    now_utc = datetime.now(timezone.utc)

    # Базовые условия для CASE
    completed_on_time_cond = (Task.completed == True) & (Task.completed_at <= Task.deadline_at)
    completed_late_cond = (Task.completed == True) & (Task.completed_at > Task.deadline_at)
    on_plan_pending_cond = (
        (Task.completed == False) &
        (Task.deadline_at != None) &
        (Task.deadline_at > now_utc)
    )
    overtime_pending_cond = (
        (Task.completed == False) &
        (Task.deadline_at != None) &
        (Task.deadline_at <= now_utc)
    )

    statement = select(
        func.sum(case((completed_on_time_cond, 1), else_=0)).label("completed_on_time"),
        func.sum(case((completed_late_cond, 1), else_=0)).label("completed_late"),
        func.sum(case((on_plan_pending_cond, 1), else_=0)).label("on_plan_pending"),
        func.sum(case((overtime_pending_cond, 1), else_=0)).label("overtime_pending")
    )

    # Применяем фильтр по пользователю, если не админ
    if current_user.role.value != "admin":
        statement = statement.where(Task.user_id == current_user.id)

    result = await db.execute(statement)
    stats_row = result.one()

    return TimingStatsResponse(
        completed_on_time=stats_row.completed_on_time or 0,
        completed_late=stats_row.completed_late or 0,
        on_plan_pending=stats_row.on_plan_pending or 0,
        overtime_pending=stats_row.overtime_pending or 0,
    )