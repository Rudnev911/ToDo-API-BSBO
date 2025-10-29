# Главный файл приложения
from fastapi import FastAPI
from routers import tasks

app = FastAPI(
    title="ToDo лист API",
    description="API для управления задачами с использованием матрицы Эйзенхауэра",
    version="1.0.0",
    contact={
        'name': 'Руднев Илья Валерьевич'
    }
)

app.include_router(tasks.router, prefix="/api/v1") # Подключение роутера из /routers/tasks, плюс добавление префикса

@app.get('/')
async def welcome() -> dict:
    return {
        'message': 'Привет, студент !',
        'title': app.title,
        'description': app.description,
        'version': app.version,
        'contact': app.contact
    }
