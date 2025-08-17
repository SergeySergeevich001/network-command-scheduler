# api/app/api/commands.py
from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete as sqlalchemy_delete
from app import models, schemas
from app.database import get_db
import uuid
import logging

# Настройка логгирования
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/devices/{device_id}/commands", tags=["commands"])

# Создаем новый роутер специально для эндпоинта /commands/{command_id}
command_by_id_router = APIRouter(prefix="/commands", tags=["commands"])

async def get_device_or_404(device_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(models.Device).where(models.Device.id == device_id)
    result = await db.execute(stmt)
    device = result.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


# POST /devices/{device_id}/commands - создать команду для устройства
@router.post("/", response_model=schemas.Command, status_code=status.HTTP_201_CREATED)
async def create_command_for_device(
        device_id: uuid.UUID,
        command: schemas.CommandCreate,
        db: AsyncSession = Depends(get_db)
):
    # Проверяем, что устройство существует
    await get_device_or_404(device_id, db)

    # Создаем новую команду, связывая её с device_id
    db_command = models.Command(
        device_id=device_id,
        command_string=command.command_string,
        description=command.description
    )
    db.add(db_command)
    await db.commit()
    await db.refresh(db_command)
    return db_command


# GET /devices/{device_id}/commands - список команд устройства
@router.get("/", response_model=list[schemas.Command])
async def read_commands_for_device(
        device_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        db: AsyncSession = Depends(get_db)
):
    # Проверяем, что устройство существует
    await get_device_or_404(device_id, db)

    # Получаем список команд для данного устройства
    stmt = select(models.Command).where(models.Command.device_id == device_id).offset(skip).limit(limit)
    result = await db.execute(stmt)
    commands = result.scalars().all()
    return commands


# GET /devices/{device_id}/commands/{command_id} - получить команду
@router.get("/{command_id}", response_model=schemas.Command)
async def read_command_for_device(
        device_id: uuid.UUID,
        command_id: uuid.UUID,
        db: AsyncSession = Depends(get_db)
):
    # Проверяем, что устройство существует
    await get_device_or_404(device_id, db)

    # Получаем конкретную команду, принадлежащую данному устройству
    stmt = select(models.Command).where(
        models.Command.id == command_id,
        models.Command.device_id == device_id
    )
    result = await db.execute(stmt)
    command = result.scalar_one_or_none()
    if command is None:
        raise HTTPException(status_code=404, detail="Command not found for this device")
    return command


@command_by_id_router.get("/{command_id}", response_model=schemas.Command)
async def read_command_by_id(
        command_id: uuid.UUID = Path(..., description="The ID of the command to retrieve"),
        db: AsyncSession = Depends(get_db)
):
    # Получить команду по её уникальному идентификатору (UUID).
    logger.info(f"Attempting to fetch command with ID: {command_id}")

    try:
        # Создаем SQL-запрос для выборки команды по ID
        stmt = select(models.Command).where(models.Command.id == command_id)

        # Выполняем запрос асинхронно
        result = await db.execute(stmt)

        # Получаем первый результат (или None, если ничего не найдено)
        command = result.scalar_one_or_none()

        # Если команда не найдена в базе данных
        if command is None:
            logger.warning(f"Command with ID {command_id} not found in database.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Command with ID {command_id} not found"
            )

        # Если команда найдена, возвращаем её
        logger.info(f"Successfully fetched command with ID: {command_id}")
        return command

    except HTTPException:
        # Пробрасываем HTTPException как есть
        raise
    except Exception as e:
        # Логируем любую другую неожиданную ошибку
        logger.error(f"Unexpected error while fetching command {command_id}: {e}", exc_info=True)
        # Возвращаем 500 Internal Server Error для клиента
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while fetching command"
        )

