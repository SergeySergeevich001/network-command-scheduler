# api/app/models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.database import Base

class Device(Base):
    __tablename__ = "devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    ip_address = Column(String, unique=True, index=True, nullable=False)
    device_type = Column(String, nullable=False)
    username = Column(String, nullable=True)
    password = Column(String, nullable=True) # В реальном приложении рекомендуется шифровать пароли
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Уникальное ограничение на IP
    __table_args__ = (UniqueConstraint('ip_address', name='uq_device_ip_address'),)

class Command(Base):
    __tablename__ = "commands"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    command_string = Column(Text, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    command_id = Column(UUID(as_uuid=True), ForeignKey("commands.id", ondelete="CASCADE"), nullable=False, index=True)
    cron_expression = Column(String, nullable=False) # Cron-выражение для расписания
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class CommandResult(Base):
    __tablename__ = "command_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    schedule_id = Column(UUID(as_uuid=True), ForeignKey("schedules.id", ondelete="SET NULL"), nullable=True, index=True)
    # schedule_id может быть NULL, если результат не связан с расписанием (например, выполнение по запросу)
    output = Column(Text, nullable=True)
    status = Column(String, nullable=False) # Например, 'pending', 'success', 'failed'
    executed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
