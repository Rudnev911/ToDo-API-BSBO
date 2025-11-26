# ToDo лист API

## Описание

Благодаря этому проекту можно управлять задачами с использованием матрицы Эйзенхауэра.

# Структура проекта

TODO-API-BSBO/
├── models/ # Модели SQLAlchemy
├── routers/ # Роутеры FastAPI
├── database.py # Настройка подключения к БД
├── main.py # Точка входа приложения
├── requirements.txt # Зависимости
└── README.md # Документация

## Технологии

- Python 3.11
- FastAPI 0.119
- SQLAlchemy 2.x (ORM)
- SQLite (или PostgreSQL, если используете)
- Uvicorn (ASGI сервер)
- Pydantic (для валидации данных)

## Запуск проекта в dev-режиме

- Установите и активируйте виртуальное окружение (python -m venv venv -> source venv/Scripts/activate) #Windows
- source venv/bin/activate   # Linux/Mac
- Установите зависимости из файла `requirements.txt`
- Запуск проекта

```bash
pip install -r requirements.txt
uvicorn main:app --reload
pip freeze > requirements.txt #Обновление зависимостей    