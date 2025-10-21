# Главный файл приложения
from fastapi import FastAPI, HTTPException
from typing import List, Dict, Any
from datetime import datetime

app = FastAPI(
    title="ToDo лист API",
    description="API для управления задачами с использованием матрицы Эйзенхауэра",
    version="1.0.0",
    contact={
        'name', 'Руднев Илья Валерьевич',
    }
)

# Временное хранилище (позже будет заменено на PostgreSQL)
tasks_db: List[Dict[str, Any]] = [
    {
        "id": 1,
        "title": "Сдать проект по FastAPI",
        "description": "Завершить разработку API и написать документацию",
        "is_important": True,
        "is_urgent": True,
        "quadrant": "Q1",
        "completed": False,
        "created_at": datetime.now()
    },
    {
        "id": 2,
        "title": "Изучить SQLAlchemy",
        "description": "Прочитать документацию и попробовать примеры",
        "is_important": True,
        "is_urgent": False,
        "quadrant": "Q2",
        "completed": False,
        "created_at": datetime.now()
    },
    {
        "id": 3,
        "title": "Сходить на лекцию",
        "description": None,
        "is_important": False,
        "is_urgent": True,
        "quadrant": "Q3",
        "completed": False,
        "created_at": datetime.now()
    },
    {
        "id": 4,
        "title": "Посмотреть сериал",
        "description": "Новый сезон любимого сериала",
        "is_important": False,
        "is_urgent": False,
        "quadrant": "Q4",
        "completed": True,
        "created_at": datetime.now()
    },
]


@app.get('/')
async def welcome() -> dict:
    return {
        'message': 'Привет, студент !',
        'title': app.title,
        'description': app.description,
        'version': app.version,
        'contact': app.contact
    }

@app.get("/tasks")
async def get_all_tasks() -> dict:
    return {
        "count": len(tasks_db),
        "tasks": tasks_db
    }

@app.get("/tasks/stats")
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

@app.get("/tasks/search")
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
@app.get("/tasks/quadrant/{quadrant}")
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

@app.get("/tasks/status/{status}")
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

@app.get("/tasks/{task_id}")
async def get_task_by_id(task_id: int) -> dict:
    for task in tasks_db:
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=404, detail="Задача не найдена")