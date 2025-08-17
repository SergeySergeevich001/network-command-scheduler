# api/app/api/schedules.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app import models, schemas
from app.database import get_db, get_temporal_client
import uuid
from temporalio.client import Client

router = APIRouter()


# Вспомогательная функция для получения устройства или 404
async def get_device_or_404(device_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(models.Device).where(models.Device.id == device_id)
    result = await db.execute(stmt)
    device = result.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


# Вспомогательная функция для получения команды устройства или 404
async def get_command_for_device_or_404(
        device_id: uuid.UUID,
        command_id: uuid.UUID,
        db: AsyncSession = Depends(get_db)
):
    # Сначала проверяем, что устройство существует
    await get_device_or_404(device_id, db)

    # Затем проверяем, что команда существует и принадлежит этому устройству
    stmt = select(models.Command).where(
        models.Command.id == command_id,
        models.Command.device_id == device_id
    )
    result = await db.execute(stmt)
    command = result.scalar_one_or_none()
    if command is None:
        raise HTTPException(status_code=404, detail="Command not found for this device")
    return command


# POST /devices/{device_id}/commands/{command_id}/schedules - создать расписание для команды
@router.post("/", response_model=schemas.Schedule, status_code=status.HTTP_201_CREATED)
async def create_schedule_for_command(
        device_id: uuid.UUID,
        command_id: uuid.UUID,
        schedule: schemas.ScheduleCreate,
        db: AsyncSession = Depends(get_db)
):
    """
    Создать расписание для команды.
    Если расписание активно (is_active=True), запускает Temporal Workflow.
    """
    # Проверяем, что команда существует и принадлежит устройству
    await get_command_for_device_or_404(device_id, command_id, db)

    # Создаем новое расписание, связывая его с command_id
    db_schedule = models.Schedule(
        command_id=command_id,
        cron_expression=schedule.cron_expression,
        is_active=schedule.is_active
    )
    db.add(db_schedule)
    await db.commit()
    await db.refresh(db_schedule)

    # Если расписание активно, запускаем Workflow в Temporal
    if schedule.is_active:
        try:
            # Получаем клиента Temporal
            client: Client = await get_temporal_client()

            # Определяем ID Workflow
            workflow_id = f"schedule-execution-{db_schedule.id}"
            task_queue_name = "scheduled-tasks"

            # Подготавливаем аргументы для Workflow
            workflow_input = {
                "schedule_id": str(db_schedule.id),
                "command_id": str(command_id),
                "device_id": str(device_id),
                "cron_expression": db_schedule.cron_expression,
            }

            # Запуск Workflow
            handle = await client.start_workflow(
                "ScheduleExecutionWorkflow",
                workflow_input,
                id=workflow_id,
                task_queue=task_queue_name,
            )
            print(f"Started Temporal Workflow with Run ID: {handle.result_run_id}")

        except Exception as e:
            # Логируем ошибку, но не прерываем создание расписания
            print(f"Warning: Failed to start/process Temporal Workflow for schedule {db_schedule.id}: {e}")

    return db_schedule


# GET /devices/{device_id}/commands/{command_id}/schedules - список расписаний команды
@router.get("/", response_model=list[schemas.Schedule])
async def read_schedules_for_command(
        device_id: uuid.UUID,
        command_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        db: AsyncSession = Depends(get_db)
):
    # Проверяем, что команда существует и принадлежит устройству
    await get_command_for_device_or_404(device_id, command_id, db)

    # Получаем список расписаний для данной команды
    stmt = select(models.Schedule).where(
        models.Schedule.command_id == command_id
    ).offset(skip).limit(limit)
    result = await db.execute(stmt)
    schedules = result.scalars().all()
    return schedules


# GET /devices/{device_id}/commands/{command_id}/schedules/{schedule_id} - получить расписание
@router.get("/{schedule_id}", response_model=schemas.Schedule)
async def read_schedule_for_command(
        device_id: uuid.UUID,
        command_id: uuid.UUID,
        schedule_id: uuid.UUID,
        db: AsyncSession = Depends(get_db)
):
    # Проверяем, что команда существует и принадлежит устройству
    await get_command_for_device_or_404(device_id, command_id, db)

    # Получаем конкретное расписание, принадлежащее данной команде
    stmt = select(models.Schedule).where(
        models.Schedule.id == schedule_id,
        models.Schedule.command_id == command_id
    )
    result = await db.execute(stmt)
    schedule = result.scalar_one_or_none()
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found for this command")
    return schedule