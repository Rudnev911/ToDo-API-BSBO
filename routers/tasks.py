from fastapi import APIRouter, FastAPI, HTTPException, Query, status, Response, Depends
from typing import List, Dict, Any
from datetime import datetime, timezone
from schemas import TaskBase, TaskCreate, TaskUpdate, TaskResponse
from database import get_db
from models import Task
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from utils import calculate_urgency, determine_quadrant, calculate_days_until_deadline

router = APIRouter(
    prefix='/tasks',
    tags=["tasks"], # Группировка по тегу, без двойных кавычек не работает(
    responses={404: {'description': 'Task not found'}},
)


@router.get("", response_model=List[TaskResponse])
async def get_all_tasks(
    # Сессия базы данных (автоматически через Depends)
    db: AsyncSession = Depends(get_db)
) -> List[TaskResponse]:
    # Выполняем SELECT запрос для получения всех задач
    result = await db.execute(select(Task))
    # Получаем все объекты Task
    tasks = result.scalars().all()
    # FastAPI автоматически преобразует список объектов Task в список TaskResponse
    return tasks

@router.get("/search", response_model=List[TaskResponse])
async def search_tasks(
    q: str = Query(..., min_length=2),
    # Используем get_db, если это название вашей зависимости в database.py
    db: AsyncSession = Depends(get_db)
) -> List[TaskResponse]:
    keyword = f"%{q.lower()}%"  # %keyword% для LIKE

    # SELECT * FROM tasks
    # WHERE LOWER(title) LIKE '%keyword%'
    # OR LOWER(description) LIKE '%keyword%'
    result = await db.execute(
        select(Task).where(
            (Task.title.ilike(keyword)) |
            (Task.description.ilike(keyword))
        )
    )
    tasks = result.scalars().all()

    if not tasks:
        raise HTTPException(status_code=404, detail="По данному запросу ничего не найдено")

    return tasks

# 3. Маршруты с параметрами в пути (динамические)
@router.get("/quadrant/{quadrant}", response_model=List[TaskResponse])
async def get_tasks_by_quadrant(
    quadrant: str,
    # Используем get_db, если это название вашей зависимости в database.py
    db: AsyncSession = Depends(get_db)
) -> List[TaskResponse]:
    if quadrant not in ["Q1", "Q2", "Q3", "Q4"]:
        raise HTTPException(
            status_code=400,
            detail="Неверный квадрант. Используйте: Q1, Q2, Q3, Q4"  # текст, который будет выведен пользователю
        )

    # SELECT * FROM tasks WHERE quadrant = 'Q1'
    result = await db.execute(
        select(Task).where(Task.quadrant == quadrant)
    )
    tasks = result.scalars().all()
    return tasks

@router.get("/status/{status}", response_model=List[TaskResponse])
async def get_tasks_by_status(
    status: str,
    # Используем get_db, если это название вашей зависимости в database.py
    db: AsyncSession = Depends(get_db)
) -> List[TaskResponse]:
    if status not in ["completed", "pending"]:
        raise HTTPException(status_code=404, detail="Недопустимый статус. Используйте: completed или pending")

    is_completed = (status == "completed")

    # SELECT * FROM tasks WHERE completed = True/False
    result = await db.execute(
        select(Task).where(Task.completed == is_completed)
    )

    tasks = result.scalars().all()
    return tasks

@router.get("/today", response_model=List[TaskResponse])
async def get_tasks_due_today(
    db: AsyncSession = Depends(get_db)
) -> List[TaskResponse]:
    """
    Возвращает все задачи, у которых дедлайн приходится на сегодняшний день (в UTC).
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    result = await db.execute(
        select(Task).where(
            Task.deadline_at >= today_start,
            Task.deadline_at <= today_end,
            Task.deadline_at.isnot(None)
        )
    )
    tasks = result.scalars().all()
    return tasks


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_by_id(
    task_id: int,
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    # SELECT * FROM tasks WHERE id = task_id
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    # Получаем одну задачу или None
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    days_deadline = calculate_days_until_deadline(task.deadline_at)

    task_dict = task.__dict__.copy()
    task_dict['days_until_deadline'] = days_deadline  # Добавляем вычисленное значение

    # 2. Проверяем, просрочена ли задача (если дедлайн существует)
    if task.deadline_at is not None and days_deadline is not None and days_deadline < 0:
        task_dict['status_message'] = "Задача просрочена"  # <-- ДОБАВЛЯЕМ СООБЩЕНИЕ!
    else:
        task_dict['status_message'] = "Все идет по плану!"

    return TaskResponse(**task_dict)


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate,
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    # Вычисляем срочность на основе дедлайна
    is_urgent = calculate_urgency(task.deadline_at)

    # Определяем квадрант
    quadrant = determine_quadrant(task.is_important, is_urgent)

    new_task = Task(
        title=task.title,
        description=task.description,
        is_important=task.is_important,
        is_urgent=is_urgent,  # Вычисленное значение
        quadrant=quadrant,
        deadline_at=task.deadline_at,
        completed=False  # Новая задача всегда не выполнена
    )

    db.add(new_task)  # Добавляем в сессию (еще не в БД!)
    await db.commit()  # Выполняем INSERT в БД
    await db.refresh(new_task)  # Обновляем объект (получаем ID из БД)

    # FastAPI автоматически преобразует Task → TaskResponse
    return new_task

# Изменение задач
@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: AsyncSession = Depends(get_db) 
) -> TaskResponse:
    
    # ШАГ 1: по аналогии с GET ищем задачу по ID
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    # Получаем одну задачу или None
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    # ШАГ 2: Получаем и обновляем только переданные поля (exclude_unset=True)
    # Без exclude_unset=True все None поля тоже попадут в БД
    update_data = task_update.model_dump(exclude_unset=True)

    # ШАГ 3: Обновить атрибуты объекта
    for field, value in update_data.items():
        setattr(task, field, value)  # <-- Присваиваем значение полю

    # ШАГ 4: Пересчитываем квадрант, если изменились важность или срочность
    if "is_important" in update_data or "deadline_at" in update_data:
        task.is_urgent = calculate_urgency(task.deadline_at)
        task.quadrant = determine_quadrant(task.is_important, task.is_urgent)

    await db.commit()  # UPDATE tasks SET ... WHERE id = task_id
    await db.refresh(task)  # Обновить объект (получаем актуальные данные из БД)

    return task

# Отметить задачу выполненой
@router.patch("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: int,
    # Используем get_db, если это название вашей зависимости в database.py
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    # Ищем задачу по ID
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    # Получаем одну задачу или None
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    # Обновляем статус задачи
    task.completed = True
    task.completed_at = datetime.now()

    await db.commit()    # Выполняем UPDATE в БД
    await db.refresh(task) # Обновляем объект из БД

    return task

@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
async def delete_task(
    task_id: int,
    # Используем get_db, если это название вашей зависимости в database.py
    db: AsyncSession = Depends(get_db)
) -> dict:
    # Ищем задачу по ID
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    # Получаем одну задачу или None
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    # Сохраняем информацию для ответа до удаления объекта
    deleted_task_info = {
        "id": task.id,
        "title": task.title
    }

    await db.delete(task)  # Помечаем объект для удаления
    await db.commit()      # Выполняем DELETE FROM tasks WHERE id = task_id

    return {
        "message": "Задача успешно удалена",
        "id": deleted_task_info["id"],
        "title": deleted_task_info["title"]
    }