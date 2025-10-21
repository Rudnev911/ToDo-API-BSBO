# ToDo лист API

## Описание

Благодаря этому проекту можно управлять задачами с использованием матрицы Эйзенхауэра.

## Технологии

- Python 3.11
- FastAPI 0.119

## Запуск проекта в dev-режиме

- Установите и активируйте виртуальное окружение (python -m venv venv -> source venv/Scripts/activate)
- Установите зависимости из файла `requirements.txt`
- Запуск проекта

```bash
pip install -r requirements.txt
unicorn main:app --reload