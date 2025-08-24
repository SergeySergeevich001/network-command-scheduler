# routers/app/routers/results.py
import logging
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from app import models, schemas
from app.database import get_db

logger = logging.getLogger(__name__)

# Роутер для результатов, связанных с расписанием
router = APIRouter(
    prefix="",
    tags=["command-results"]
)


@router.post("/", response_model=schemas.CommandResult, status_code=status.HTTP_201_CREATED)
async def create_or_update_result_for_schedule(
    schedule_id: uuid.UUID,
    result: schemas.CommandResultCreate,
    db: AsyncSession = Depends(get_db)
):
#    Создать или обновить результат для выполнения определенного расписания, вызывается Workflow'ом Temporal через API.

    logger.info(f"Создание/обновление результата для ID расписания: {schedule_id}")
    try:
        # Создать новый объект CommandResult
        db_result = models.CommandResult(
            schedule_id=schedule_id,
            output=result.output,
            status=result.status
        )
        db.add(db_result)
        await db.commit()
        await db.refresh(db_result)
        logger.info(f"Успешно создан результат с ID: {db_result.id} для ID расписания: {schedule_id}")
        return db_result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Не удалось создать/обновить результат для расписания {schedule_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера при сохранении результата команды"
        )


@router.get("/{result_id}", response_model=schemas.CommandResult)
async def read_result_by_id(
    device_id: uuid.UUID,
    schedule_id: uuid.UUID,
    result_id: uuid.UUID = Path(..., description="ID результата команды"),
    db: AsyncSession = Depends(get_db)
):
    # Получить конкретный результат команды по его ID.
    logger.info(f"Получение результата с ID: {result_id} для ID расписания: {schedule_id}")
    try:
        stmt = select(models.CommandResult).where(models.CommandResult.id == result_id)
        result = await db.execute(stmt)
        db_result = result.scalar_one_or_none()

        if db_result is None:
            logger.warning(f"Результат с ID {result_id} не найден.")
            raise HTTPException(status_code=404, detail="Результат команды не найден")

        logger.info(f"Успешно получен результат с ID: {result_id}")
        return db_result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Не удалось получить результат {result_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера при получении результата команды"
        )


# Новый роутер для эндпоинтов на уровне устройства
device_level_router = APIRouter(tags=["device-results"])


# Новый эндпоинт для получения результатов на уровне устройства
@device_level_router.get("/devices/{device_id}/results/", response_model=List[schemas.CommandResult])
async def read_results_for_device(
    device_id: uuid.UUID = Path(..., description="ID устройства"),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список результатов выполнения команд для определенного устройства.
    Результаты упорядочены по дате выполнения, сначала новые.
    """
    logger.info(f"Получение результатов для ID устройства: {device_id}, пропустить: {skip}, лимит: {limit}")
    try:
        # Получить результаты, связанные с расписаниями, которые принадлежат командам этого устройства
        stmt = (
            select(models.CommandResult)
            .join(models.Schedule, models.CommandResult.schedule_id == models.Schedule.id)
            .join(models.Command, models.Schedule.command_id == models.Command.id)
            .where(models.Command.device_id == device_id)
            .order_by(desc(models.CommandResult.created_at))
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(stmt)
        results = result.scalars().all()
        logger.info(f"Успешно получено {len(results)} результатов для ID устройства: {device_id}")
        return results
    except Exception as e:
        logger.error(f"Ошибка базы данных при получении результатов для устройства {device_id}: {e}", exc_info=True)
        raise