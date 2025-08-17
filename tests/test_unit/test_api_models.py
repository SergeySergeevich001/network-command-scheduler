# tests/test_unit/test_api_models.py
import pytest
from app.schemas import DeviceCreate, CommandCreate, ScheduleCreate
from pydantic import ValidationError


def test_device_create_valid():
    # Тест создания валидной схемы DeviceCreate.
    data = {
        "ip_address": "192.168.1.1",
        "device_type": "switch",
        "username": "admin",
        "password": "password123",
        "hostname": "CoreSwitch"
    }
    device = DeviceCreate(**data)
    assert device.ip_address == data["ip_address"]
    assert device.device_type == data["device_type"]
    assert device.username == data["username"]
    assert device.password == data["password"]


def test_device_create_invalid_ip():
    # Тест создания схемы DeviceCreate с невалидным IP.
    data = {
        "ip_address": "invalid_ip",
        "device_type": "switch",
        "username": "admin",
        "password": "password123",
        "hostname": "CoreSwitch"
    }
    with pytest.raises(ValidationError) as exc_info:
        DeviceCreate(**data)

    errors = exc_info.value.errors()
    # Проверяем, что ошибка связана с полем ip_address
    assert any("ip_address" in str(err) for err in errors) or any("value_error" in str(err) for err in errors)


def test_command_create_missing_command_string():
    # Тест создания схемы CommandCreate без обязательного поля command_string.
    data = {
        "description": "Show device version information"
    }
    with pytest.raises(ValidationError) as exc_info:
        CommandCreate(**data)

    errors = exc_info.value.errors()
    assert len(errors) >= 1
    # Проверяем тип ошибки: 'missing' для отсутствующего поля
    assert errors[0]['type'] == 'missing'
    assert 'command_string' in str(errors[0].get('loc', []))


def test_schedule_create_valid_cron():
    # Тест создания валидной схемы ScheduleCreate.
    data = {
        "cron_expression": "0 2 * * *",
        "is_active": True
    }
    schedule = ScheduleCreate(**data)
    assert schedule.cron_expression == data["cron_expression"]
    assert schedule.is_active == data["is_active"]
