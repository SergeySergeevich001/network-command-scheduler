# api/app/main.py (основной файл фаст апи,импортирует эндпоинты, добавляет на них префиксы)
from fastapi import FastAPI
from app.api import devices, commands, schedules, results
from app.api.results import router as results_router, device_level_router
from app.api.commands import router as commands_router, command_by_id_router
from app.database import engine, Base

app = FastAPI(title="Scheduled Network Commands API")

# Создание таблиц
@app.on_event("startup") # встроенный декоратор фастапи,который выполняет функцию один раз при запуске приложения, то есть
''' до того как сервер начнет принимать хттп запросы '''
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/") # хэлс чек, проверяет что сервер запущен и принимает запросы, видим сообщение об этом в консоли
async def root():
    return {"message": "Scheduled Network Commands API"}

# Подключение роутеров (эндпоинтов датабейс,шедулез, шемаз (расписание), сами эндпоинты в файлах)
app.include_router(devices.router, prefix="/devices", tags=["devices"])
# Используем commands_router без дополнительного префикса
app.include_router(commands_router)
app.include_router(
    schedules.router,
    prefix="/devices/{device_id}/commands/{command_id}/schedules",
    tags=["schedules"]
)
# Подключение существующего results.router для эндпоинтов вида: POST /devices/{device_id}/schedules/{schedule_id}/result/
app.include_router(
    results_router,
    prefix="/devices/{device_id}/schedules/{schedule_id}/result",
    tags=["results"]
)
# Подключение нового device_level_router для эндпоинта: GET /devices/{device_id}/results/
app.include_router(device_level_router)
# Подключение нового роутера для получения команды по ID для эндпоинта: GET /commands/{command_id}
app.include_router(command_by_id_router)