from fastapi import APIRouter, FastAPI, HTTPException, Query, status, Response
from typing import List, Dict, Any
from datetime import datetime
from schemas import TaskBase, TaskCreate, TaskUpdate, TaskResponse
from database import tasks_db

router = APIRouter(
    prefix='/tasks',
    tags=["tasks"], # Группировка по тегу, без двойных кавычек не работает(
    responses={404: {'description': 'Task not found'}},
)


@router.get("")
async def get_all_tasks() -> dict:
    return {
        "count": len(tasks_db),
        "tasks": tasks_db
    }

@router.get("/stats")
async def get_tasks_stats() -> dict:
    total_tasks = len(tasks_db)

    by_quadrant = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}
    for task in tasks_db:
        quadrant = task.get("quadrant")
        if quadrant in by_quadrant:
            by_quadrant[quadrant] += 1

    completed = sum(1 for task in tasks_db if task.get("completed") is True)
    pending = total_tasks - completed

    return {
        "total_tasks": total_tasks,
        "by_quadrant": by_quadrant,
        "by_status": {
            "completed": completed,
            "pending": pending
        }
    }

@router.get("/search")
async def search_tasks(q: str) -> dict:
    if len(q) < 2:
        raise HTTPException(
            status_code=400,
            detail="Ключевое слово должно содержать минимум 2 символа"
        )
    
    query = q.lower()
    filtered_tasks = [
        task for task in tasks_db
        if (task.get("title") and query in task["title"].lower()) or
           (task.get("description") and query in task["description"].lower())
    ]
    
    return {
        "query": q,
        "count": len(filtered_tasks),
        "tasks": filtered_tasks
    }

# 3. Маршруты с параметрами в пути (динамические)
@router.get("/quadrant/{quadrant}")
async def get_tasks_by_quadrant(quadrant: str) -> dict:
    if quadrant not in {"Q1", "Q2", "Q3", "Q4"}:
        raise HTTPException(
            status_code=400,
            detail="Неверный квадрант. Используйте: Q1, Q2, Q3, Q4"
        )
    
    filtered_tasks = [
        task for task in tasks_db
        if task["quadrant"] == quadrant
    ]
    
    return {
        "quadrant": quadrant,
        "count": len(filtered_tasks),
        "tasks": filtered_tasks
    }

@router.get("/status/{status}")
async def get_tasks_by_status(status: str) -> dict:
    if status not in {"completed", "pending"}:
        raise HTTPException(
            status_code=404,
            detail="Статус не найден. Используйте: 'completed' или 'pending'"
        )
    
    if status == "completed":
        filtered_tasks = [task for task in tasks_db if task.get("completed") is True]
    else:
        filtered_tasks = [task for task in tasks_db if task.get("completed") is not True]
    
    return {
        "status": status,
        "count": len(filtered_tasks),
        "tasks": filtered_tasks
    }

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_by_id(task_id: int) -> TaskResponse:
    task = next((
        task for task in tasks_db
        if task["id"] == task_id),
        None
    )
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return task


# Мы указываем, что эндпоинт будет возвращать данные,
# соответствующие схеме TaskResponse
@router.post("/", response_model=TaskResponse,
             status_code=status.HTTP_201_CREATED)
async def create_task(task: TaskCreate) -> TaskResponse:
    # Определяем квадрант
    if task.is_important and task.is_urgent:
        quadrant = "Q1"
    elif task.is_important and not task.is_urgent:
        quadrant = "Q2"
    elif not task.is_important and task.is_urgent:
        quadrant = "Q3"
    else:
        quadrant = "Q4"
    new_id = max([t["id"] for t in tasks_db], default=0) + 1  # Генерируем новый ID

    new_task = {
        "id": new_id,
        "title": task.title,
        "description": task.description,
        "is_important": task.is_important,
        "is_urgent": task.is_urgent,
        "quadrant": quadrant,
        "completed": False,
        "created_at": datetime.now()
    }
    tasks_db.append(new_task)  # "Сохраняем" в нашу "базу данных"

    # Возвращаем созданную задачу (FastAPI автоматически
    # преобразует dict в Pydantic-модель Task)
    return new_task

# Изменение задач
@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: int, task_update: TaskUpdate) -> TaskResponse:
    # ШАГ 1: по аналогии с GET ищем задачу по ID
    task = next((
        task for task in tasks_db
        if task["id"] == task_id),
        None
    )
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    # ШАГ 2: Получаем и обновляем только переданные поля (exclude_unset=True)
    # Без exclude_unset=True все None поля тоже попадут в словарь
    update_data = task_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        task[field] = value
    
    # ШАГ 3: Пересчитываем квадрант, если изменились важность или срочность
    if "is_important" in update_data or "is_urgent" in update_data:
        if task["is_important"] and task["is_urgent"]:
            task["quadrant"] = "Q1"
        elif task["is_important"] and not task["is_urgent"]:
            task["quadrant"] = "Q2"
        elif not task["is_important"] and task["is_urgent"]:
            task["quadrant"] = "Q3"
        else:
            task["quadrant"] = "Q4"
    
    return task

@router.patch("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(task_id: int) -> TaskResponse:
    task = next((
        task for task in tasks_db
        if task["id"] == task_id),
        None
    )
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    task["completed"] = True
    task["completed_at"] = datetime.now()
    
    return task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int):
    task = next((
        task for task in tasks_db
        if task["id"] == task_id),
        None
    )
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    tasks_db.remove(task)
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)