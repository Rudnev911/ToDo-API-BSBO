from fastapi import APIRouter, FastAPI, HTTPException, Query, status, Response, Depends
from typing import List, Dict, Any
from datetime import datetime, timezone
from schemas import TaskBase, TaskCreate, TaskUpdate, TaskResponse
from database import get_db
from models import Task 
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from utils import calculate_urgency, determine_quadrant, calculate_days_until_deadline
from dependencies import get_current_user
from models import User

router = APIRouter(
    prefix='/tasks',
    tags=["tasks"], # Группировка по тегу, без двойных кавычек не работает(
    responses={404: {'description': 'Task not found'}},
)


#@router.get("", response_model=List[TaskResponse])
#async def get_all_tasks(
    # Сессия базы данных (автоматически через Depends)
    #db: AsyncSession = Depends(get_db)
#) -> List[TaskResponse]:
    # Выполняем SELECT запрос для получения всех задач
    #result = await db.execute(select(Task))
    # Получаем все объекты Task
    #tasks = result.scalars().all()
    # FastAPI автоматически преобразует список объектов Task в список TaskResponse
    #return tasks

@router.get("/", response_model=List[TaskResponse])
async def get_all_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[TaskResponse]:
    """Получает все задачи: админ видит всё, обычный пользователь — только свои."""
    
    if current_user.role.value == "admin":
        # Администратор видит все задачи
        result = await db.execute(select(Task))
    else:
        # Обычный пользователь видит только свои задачи
        result = await db.execute(
            select(Task).where(Task.user_id == current_user.id)
        )

    tasks = result.scalars().all()

    tasks_with_days = []
    for task in tasks:
        task_dict = task.__dict__.copy()
        task_dict['days_until_deadline'] = calculate_days_until_deadline(task.deadline_at)
        tasks_with_days.append(TaskResponse(**task_dict))

    return tasks_with_days

# 3. Маршруты с параметрами в пути (динамические)
@router.get("/quadrant/{quadrant}", response_model=list[TaskResponse])
async def get_tasks_by_quadrant(
    quadrant: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)  
) -> list[TaskResponse]:
    """Получить задачи пользователя по квадранту."""
    
    if quadrant not in ["Q1", "Q2", "Q3", "Q4"]:
        raise HTTPException(
            status_code=400,
            detail="Неверный квадрант. Используйте: Q1, Q2, Q3, Q4"
        )

    # Администраторы видят все задачи, обычные пользователи — только свои
    if current_user.role.value == "admin":
        result = await db.execute(
            select(Task).where(Task.quadrant == quadrant)
        )
    else:
        result = await db.execute(
            select(Task).where(
                Task.quadrant == quadrant,
                Task.user_id == current_user.id
            )
        )

    tasks = result.scalars().all()
    return tasks


@router.get("/search", response_model=list[TaskResponse])
async def search_tasks(
    q: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> list[TaskResponse]:
    """Поиск задач по заголовку или описанию."""
    
    keyword = f"%{q.lower()}%"

    if current_user.role.value == "admin":
        # Администратор ищет по всем задачам
        result = await db.execute(
            select(Task).where(
                (Task.title.ilike(keyword)) | (Task.description.ilike(keyword))
            )
        )
    else:
        # Обычный пользователь ищет только в своих задачах
        result = await db.execute(
            select(Task).where(
                Task.user_id == current_user.id,
                (Task.title.ilike(keyword)) | (Task.description.ilike(keyword))
            )
        )

    tasks = result.scalars().all()

    if not tasks:
        raise HTTPException(
            status_code=404,
            detail="По данному запросу ничего не найдено"
        )

    return tasks

@router.get("/status/{status}", response_model=list[TaskResponse])
async def get_tasks_by_status(
    status: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> list[TaskResponse]:
    """Получить задачи по статусу: completed или pending."""
    
    if status not in ["completed", "pending"]:
        raise HTTPException(
            status_code=400,
            detail="Недопустимый статус. Используйте: completed или pending"
        )

    is_completed = (status == "completed")

    if current_user.role.value == "admin":
        # Администратор видит все задачи указанного статуса
        result = await db.execute(
            select(Task).where(Task.completed == is_completed)
        )
    else:
        # Обычный пользователь видит только свои задачи указанного статуса
        result = await db.execute(
            select(Task).where(
                Task.completed == is_completed,
                Task.user_id == current_user.id
            )
        )

    tasks = result.scalars().all()
    return tasks

@router.get("/today", response_model=List[TaskResponse])
async def get_tasks_due_today(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[TaskResponse]:
    """
    Возвращает задачи с дедлайном сегодня:
    - Администратор видит все такие задачи.
    - Обычный пользователь — только свои.
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    query = (
        select(Task)
        .where(
            Task.deadline_at >= today_start,
            Task.deadline_at <= today_end,
            Task.deadline_at.isnot(None)
        )
    )

    # Фильтрация по пользователю, если не админ
    if current_user.role.value != "admin":
        query = query.where(Task.user_id == current_user.id)

    result = await db.execute(query)
    tasks = result.scalars().all()
    return tasks


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_by_id(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> TaskResponse:
    """Получить задачу по ID. Обычный пользователь может видеть только свои задачи."""
    
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    # Проверка доступа: админ видит всё, обычный пользователь — только свои задачи
    if current_user.role.value != "admin" and task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этой задаче"
        )

    days_deadline = calculate_days_until_deadline(task.deadline_at)
    task_dict = task.__dict__.copy()
    task_dict['days_until_deadline'] = days_deadline  # Добавляем вычисленное значение

    # Проверяем, просрочена ли задача (если дедлайн существует)
    if task.deadline_at is not None and days_deadline is not None and days_deadline < 0:
        task_dict['status_message'] = "Задача просрочена"
    else:
        task_dict['status_message'] = "Все идет по плану!"

    return TaskResponse(**task_dict)


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> TaskResponse:
    """Создать новую задачу, привязанную к текущему пользователю."""
    
    # Вычисляем срочность на основе дедлайна
    is_urgent = calculate_urgency(task.deadline_at)
    # Определяем квадрант
    quadrant = determine_quadrant(task.is_important, is_urgent)

    # Создаём новую задачу, привязанную к текущему пользователю
    new_task = Task(
        title=task.title,
        description=task.description,
        is_important=task.is_important,
        is_urgent=is_urgent,
        quadrant=quadrant,
        deadline_at=task.deadline_at,
        completed=False,
        user_id=current_user.id  # Привязываем задачу к текущему пользователю
    )

    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    return new_task

# Изменение задач
@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> TaskResponse:
    """Обновить задачу. Обычный пользователь может редактировать только свои задачи."""
    
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    # Проверка доступа: админ может редактировать любую задачу, обычный пользователь — только свою
    if current_user.role.value != "admin" and task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этой задаче"
        )

    # Обновляем только переданные поля (exclude_unset=True)
    update_data = task_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(task, field, value)

    # Пересчитываем срочность и квадрант, если изменились важность или дедлайн
    if "is_important" in update_data or "deadline_at" in update_data:
        task.is_urgent = calculate_urgency(task.deadline_at)
        task.quadrant = determine_quadrant(task.is_important, task.is_urgent)

    await db.commit()
    await db.refresh(task)

    # Добавляем вычисленное значение days_until_deadline
    task_dict = task.__dict__.copy()
    task_dict['days_until_deadline'] = calculate_days_until_deadline(task.deadline_at)

    return TaskResponse(**task_dict)

# Отметить задачу выполненой
@router.patch("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> TaskResponse:
    """Отметить задачу как выполненную. Обычный пользователь может завершать только свои задачи."""
    
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    # Проверка доступа: админ может завершать любую задачу, обычный пользователь — только свою
    if current_user.role.value != "admin" and task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этой задаче"
        )

    # Отмечаем задачу как выполненную
    task.completed = True
    task.completed_at = datetime.now()  # Устанавливаем время завершения

    await db.commit()
    await db.refresh(task)

    # Добавляем вычисленное значение days_until_deadline
    task_dict = task.__dict__.copy()
    task_dict['days_until_deadline'] = calculate_days_until_deadline(task.deadline_at)

    return TaskResponse(**task_dict)

@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    """Удалить задачу. Обычный пользователь может удалять только свои задачи."""
    
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    # Проверка доступа: админ может удалять любую задачу, обычный пользователь — только свою
    if current_user.role.value != "admin" and task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этой задаче"
        )

    # Сохраняем информацию о задаче перед удалением
    deleted_task_info = {
        "id": task.id,
        "title": task.title
    }

    # Удаляем задачу
    await db.delete(task)
    await db.commit()

    return {
        "message": "Задача успешно удалена",
        "id": deleted_task_info["id"],
        "title": deleted_task_info["title"]
    }