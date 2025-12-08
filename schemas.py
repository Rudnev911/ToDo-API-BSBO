from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


# Базовая схема для Task.
# Все поля, которые есть в нашей "базе данных" tasks_db
class TaskBase(BaseModel):
    title: str = Field(
        ...,  # троеточие означает "обязательное поле"
        min_length=3,
        max_length=100,
        description="Название задачи"
    )
    description: Optional[str] = Field(
        None,  # None = необязательное поле
        max_length=500,
        description="Описание задачи"
    )
    is_important: bool = Field(
        ...,
        description="Важность задачи"
    )
    #is_urgent: bool = Field(
        #...,
        #description="Срочность задачи"
    #)
    deadline_at: Optional[datetime] = Field(
    default=None,
    description="Плановый срок выполнения задачи"
)


# Схема для создания новой задачи
# Наследует все поля от TaskBase
class TaskCreate(TaskBase):
    pass


# Схема для обновления задачи (используется в PUT)
# Все поля опциональные, т.к. мы можем захотеть обновить только title или status
class TaskUpdate(BaseModel):
    title: Optional[str] = Field(
        None,
        min_length=3,
        max_length=100,
        description="Новое название задачи"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Новое описание"
    )
    is_important: Optional[bool] = Field(
        None,
        description="Новая важность"
    )
    deadline_at: Optional[datetime] = Field(
    default=None,
    description="Новый дедлайн"
    )
    completed: Optional[bool] = Field(
        None,
        description="Статус выполнения"
    )


class TaskResponse(TaskBase):
    """
    Модель ответа API для задачи — содержит все поля из TaskBase + дополнительные системные поля.
    Автоматически конвертирует ORM-объекты (например, из SQLAlchemy).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        ...,
        description="Уникальный идентификатор задачи",
        examples=[1]
    )

    quadrant: str = Field(
        ...,
        description="Квадрант матрицы Эйзенхауэра (Q1, Q2, Q3, Q4)",
        examples=["Q1"]
    )

    is_urgent: bool = Field(
        ...,
        description="Срочность задачи (вычисляется автоматически)"
    )

    completed: bool = Field(
        default=False,
        description="Статус выполнения задачи"
    )

    created_at: datetime = Field(
        ...,
        description="Дата и время создания задачи"
    )

    completed_at: Optional[datetime] = Field(
        default=None,
        description="Дата и время завершения задачи"
    )

    days_until_deadline: Optional[int] = Field(
        default=None,
        description="Количество дней до дедлайна (если указан)"
    )

    status_message: Optional[str] = Field(
        default=None,
        description="Сообщение о статусе задачи (например, 'Задача просрочена')"
    )

class TimingStatsResponse(BaseModel):
    completed_on_time: int = Field(
        ...,
        description="Количество задач, завершенных в срок"
    )

    completed_late: int = Field(
        ...,
        description="Количество задач, завершенных с нарушением сроков"
    )

    on_plan_pending: int = Field(
        ...,
        description="Количество задач в работе, выполняемых в соответствии с планом"
    )

    overtime_pending: int = Field(
        ...,
        description="Количество просроченных незавершенных задач"
    )