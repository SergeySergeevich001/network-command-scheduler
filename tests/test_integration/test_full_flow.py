# tests/test_integration/test_full_flow.py
"""
Интеграционные тесты для проверки основных API эндпоинтов и полного потока.
"""
import pytest
# Используем синхронный клиент TestClient для тестирования FastAPI приложения
from starlette.testclient import TestClient
# Импорт приложения FastAPI
from app.main import app


@pytest.fixture(scope="function")
def client():
    # Создаем синхронный клиент
    # TestClient автоматически вызывает lifespan приложения
    with TestClient(app) as tc:
        yield tc
    # Закрытие клиента


@pytest.mark.asyncio
async def test_full_command_execution_flow(client, sample_device_data, sample_command_data, sample_schedule_data):

    # Интеграционный тест: Создание устройства - команды - расписания - проверка результата.
    # Создание устройства
    response = client.post("/devices/", json=sample_device_data)
    assert response.status_code == 201, f"Failed to create device: {response.text}"
    device_data = response.json()
    device_id = device_data["id"]
    # Простая проверка формата UUID
    assert len(device_id) == 36 and '-' in device_id

    # Создание команды для устройства
    response = client.post(f"/devices/{device_id}/commands/", json=sample_command_data)
    assert response.status_code == 201, f"Failed to create command: {response.text}"
    command_data = response.json()
    command_id = command_data["id"]
    assert len(command_id) == 36 and '-' in command_id
    assert command_data["command_string"] == sample_command_data["command_string"]

    # Создание расписания для команды
    response = client.post(f"/devices/{device_id}/commands/{command_id}/schedules/", json=sample_schedule_data)
    assert response.status_code == 201, f"Failed to create schedule: {response.text}"
    schedule_data = response.json()
    schedule_id = schedule_data["id"]
    assert len(schedule_id) == 36 and '-' in schedule_id
    assert schedule_data["is_active"] == sample_schedule_data["is_active"]

    # Проверка, что расписание существует
    response = client.get(f"/devices/{device_id}/commands/{command_id}/schedules/{schedule_id}")
    assert response.status_code == 200, f"Failed to get schedule: {response.text}"
    retrieved_schedule = response.json()
    assert retrieved_schedule["id"] == schedule_id
    assert retrieved_schedule["command_id"] == command_id

    # Проверка результатов
    # Проверяем, что эндпоинт результатов возвращает 200
    response = client.get(f"/devices/{device_id}/results/")
    assert response.status_code == 200, f"Failed to get results: {response.text}"
    results_data = response.json()

    print(f"Integration test completed successfully for device {device_id}, command {command_id}, schedule {schedule_id}")

