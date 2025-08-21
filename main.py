# api/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.api import devices, commands, schedules
from app import schemas
from app.database import engine, Base, get_db
import uuid
from app import models

app = FastAPI(title="Scheduled Network Commands API")


# Создание таблиц (так как не используем Alembic)
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/")
async def root():
    return {"message": "Scheduled Network Commands API"}


# Подключение роутеров ресурсов
app.include_router(devices.router, prefix="/devices", tags=["devices"])
app.include_router(commands.router, prefix="/devices/{device_id}/commands", tags=["commands"])
app.include_router(
    schedules.router,
    prefix="/devices/{device_id}/commands/{command_id}/schedules",
    tags=["schedules"]
)


# Новый эндпоинт для обновления результата
# POST /devices/{device_id}/schedules/{schedule_id}/result
@app.post("/devices/{device_id}/schedules/{schedule_id}/result", status_code=status.HTTP_204_NO_CONTENT)
async def update_command_result(
        device_id: uuid.UUID,
        schedule_id: uuid.UUID,
        result_update: schemas.CommandResultUpdateApi,
        db: AsyncSession = Depends(get_db)
):
    """
    Обновляет результат выполнения команды для заданного расписания.
    Вызывается Temporal Workflow после завершения выполнения.
    """
    # Проверяем, что устройство существует
    stmt_device = select(models.Device).where(models.Device.id == device_id)
    result_device = await db.execute(stmt_device)
    device = result_device.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    # Проверяем, что расписание существует
    stmt_schedule = select(models.Schedule).where(models.Schedule.id == schedule_id)
    result_schedule = await db.execute(stmt_schedule)
    schedule = result_schedule.scalar_one_or_none()
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Проверка, что schedule.command_id указывает на команду, принадлежащую device_id
    stmt_command = select(models.Command).where(
        models.Command.id == schedule.command_id,
        models.Command.device_id == device_id
    )
    result_command = await db.execute(stmt_command)
    command = result_command.scalar_one_or_none()
    if command is None:
        raise HTTPException(status_code=400, detail="Schedule does not belong to the specified device's command")

    # Находим последний результат для этого schedule_id
    stmt_result = select(models.CommandResult).where(
        models.CommandResult.schedule_id == schedule_id
    ).order_by(models.CommandResult.created_at.desc()).limit(1)

    result_result = await db.execute(stmt_result)
    command_result = result_result.scalar_one_or_none()

    if command_result is None:
        # Если результат еще не создан, Workflow должен был его сначала создать.
        raise HTTPException(status_code=404, detail="No command result found for this schedule to update")

    # Обновляем найденный результат
    if result_update.output is not None:
        command_result.output = result_update.output
    command_result.status = result_update.status


    db.add(command_result)
    await db.commit()
    # Возвращаем 204 No Content

