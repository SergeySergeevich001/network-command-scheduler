# api/app/schemas.py
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Union
from datetime import datetime
import uuid

# Схемы для Device
class DeviceBase(BaseModel):
    ip_address: str = Field(..., example="192.168.1.1")
    device_type: str = Field(..., example="router")
    username: Optional[str] = Field(None, example="admin")
    password: Optional[str] = Field(None, example="secret_password")

    @validator('ip_address')
    def validate_ip_address(cls, v):
        # Простая валидация формата IP-адреса
        import ipaddress
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError('Invalid IP address format')

class DeviceCreate(DeviceBase):
    pass

class DeviceUpdate(BaseModel):
    ip_address: Optional[str] = Field(None, example="192.168.1.1")
    device_type: Optional[str] = Field(None, example="switch")
    username: Optional[str] = Field(None, example="new_user")
    password: Optional[str] = Field(None, example="new_password")

    @validator('ip_address')
    def validate_ip_address(cls, v):
        if v is not None:
            import ipaddress
            try:
                ipaddress.ip_address(v)
                return v
            except ValueError:
                raise ValueError('Invalid IP address format')
        return v

class Device(DeviceBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True # Для совместимости с ORM

# Схемы для Command
class CommandBase(BaseModel):
    command_string: str = Field(..., example="show version")
    description: Optional[str] = Field(None, example="Show device version information")

class CommandCreate(CommandBase):
    pass

class CommandUpdate(BaseModel):
    command_string: Optional[str] = Field(None, example="show interfaces")
    description: Optional[str] = Field(None, example="Show interface status")

class Command(CommandBase):
    id: uuid.UUID
    device_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Схемы для Schedule
class ScheduleBase(BaseModel):
    cron_expression: str = Field(..., example="0 2 * * *") # Ежедневно в 02:00
    is_active: bool = Field(default=True, example=True)

class ScheduleCreate(ScheduleBase):
    pass

class ScheduleUpdate(BaseModel):
    cron_expression: Optional[str] = Field(None, example="0 3 * * *") # Ежедневно в 03:00
    is_active: Optional[bool] = Field(None, example=False)

class Schedule(ScheduleBase):
    id: uuid.UUID
    command_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Схемы для CommandResult
class CommandResultBase(BaseModel):
    output: Optional[str] = Field(None, example="Cisco IOS Software, C2960 Software ...")
    status: str = Field(..., example="success") # 'pending', 'success', 'failed'

class CommandResultCreate(CommandResultBase):
    '''
    При создании результата через API (из Workflow)
    schedule_id может быть неизвестен или не передаваться напрямую
    в реальности schedule_id будет определяться на стороне сервера
    или передаваться в URL. Пока делаем его обязательным в схеме,
    в будущем можно будет уточнить логику.
    '''
    pass

class CommandResultUpdate(BaseModel):
    output: Optional[str] = Field(None, example="Updated output...")
    status: Optional[str] = Field(None, example="failed")

class CommandResult(CommandResultBase):
    id: uuid.UUID
    schedule_id: Optional[uuid.UUID] # Может быть NULL в БД
    executed_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# Дополнительная схема для обновления результата через API

class CommandResultUpdateApi(BaseModel):
    output: Optional[str] = Field(None, example="Command executed successfully")
    status: str = Field(..., example="success") # 'pending', 'success', 'failed'

    @validator('status')
    def validate_status(cls, v):
        if v not in ['pending', 'success', 'failed']:
            raise ValueError("Status must be 'pending', 'success', or 'failed'")
        return v