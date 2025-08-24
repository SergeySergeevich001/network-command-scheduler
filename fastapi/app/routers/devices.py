# routers/app/routers/devices.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete as sqlalchemy_delete
from app import models, schemas
from app.database import get_db
import uuid

router = APIRouter()


@router.post("/", response_model=schemas.Device, status_code=status.HTTP_201_CREATED)
async def create_device(device: schemas.DeviceCreate, db: AsyncSession = Depends(get_db)):
    # Проверка на уникальность IP
    stmt = select(models.Device).where(models.Device.ip_address == device.ip_address)
    result = await db.execute(stmt)
    db_device = result.scalar_one_or_none()
    if db_device:
        raise HTTPException(status_code=400, detail="Device with this IP address already exists")

    # Создание нового устройства
    db_device = models.Device(**device.model_dump())
    db.add(db_device)
    await db.commit()
    await db.refresh(db_device)
    return db_device


@router.get("/", response_model=list[schemas.Device])
async def read_devices(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    stmt = select(models.Device).offset(skip).limit(limit)
    result = await db.execute(stmt)
    devices = result.scalars().all()
    return devices


@router.get("/{device_id}", response_model=schemas.Device)
async def read_device(device_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(models.Device).where(models.Device.id == device_id)
    result = await db.execute(stmt)
    device = result.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(device_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(models.Device).where(models.Device.id == device_id)
    result = await db.execute(stmt)
    device = result.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    # Удаление устройства
    await db.delete(device)
    await db.commit()
    # FastAPI автоматически вернет 204 No Content для функций, которые ничего не возвращают
