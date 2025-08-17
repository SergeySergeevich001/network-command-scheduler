# tests/conftest.py
import pytest
import random
import uuid
import asyncio
# Импортируем напрямую из main.py
# main.py находится в /app внутри контейнера
from main import app as application  # Импортируем экземпляр FastAPI app из main.py

# Импорты из вашего проекта
from app.database import Base, DATABASE_URL, get_db
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient


# Фикстуры

@pytest.fixture(scope="session")
def event_loop():
    # Создает экземпляр event loop для тестов.
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    # Создает асинхронный движок SQLAlchemy для тестов.
    engine = create_async_engine(DATABASE_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def test_db_session(test_engine):
    # Создает и очищает сессию БД для каждого теста.
    # Создаем таблицы
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Создаем фабрику сессий
    async_session_factory = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_factory() as session:
        yield session  # Передаем сессию в тест

    # Очистка: удаляем таблицы после теста
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(test_db_session):
    # Создает тестовый HTTP клиент для FastAPI приложения.
    # Переопределяем зависимость get_db на тестовую сессию
    application.dependency_overrides[get_db] = lambda: test_db_session

    async with AsyncClient(app=application, base_url="http://test") as ac:
        yield ac

    # Очищаем overrides после теста
    application.dependency_overrides.clear()


# Фикстуры для данных
@pytest.fixture
def sample_device_data():
    # Генерирует уникальные тестовые данные для устройства.
    # Использует random.randint для создания IP-адреса без ведущих нулей.
    # Генерируем случайные числа от 1 до 254 для октетов
    octet2 = random.randint(1, 254)
    octet3 = random.randint(1, 254)
    octet4 = random.randint(1, 254)

    return {
        "ip_address": f"10.{octet2}.{octet3}.{octet4}",
        "device_type": "router",
        "username": "testuser",
        "password": "testpass",
        "hostname": "TestRouter"
    }


@pytest.fixture
def sample_command_data():
    return {
        "command_string": "show ip route",
        "description": "Display routing table"
    }


@pytest.fixture
def sample_schedule_data():
    return {
        "cron_expression": "*/5 * * * *",
        "is_active": True
    }