import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла для локальной разработки
load_dotenv()

# Настройка подключения к PostgreSQL
DATABASE_USER = os.getenv("POSTGRES_USER", "postgres")
DATABASE_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
# Имя хоста должно совпадать с именем сервиса PostgreSQL в docker-compose.yml
DATABASE_HOST = os.getenv("POSTGRES_HOST", "scheduled_commands_postgresql")
DATABASE_PORT = os.getenv("POSTGRES_PORT", "5432")
DATABASE_NAME = os.getenv("POSTGRES_DB", "scheduled_commands")

DATABASE_URL = f"postgresql+asyncpg://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"

engine = create_async_engine(DATABASE_URL, echo=True)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()


# Зависимость для получения сессии БД в эндпоинтах FastAPI
#  функция, которая даёт  эндпоинту доступ в БД
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            print(f"Database session error: {e}")
            raise
        finally:
            await session.close()


#Конец настройки подключения к PostgreSQL


