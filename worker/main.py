'''

    Worker (организатор):
        - Получает этот Workflow от Temporal.
        - Говорит: "Окей, я буду следить за этим делом".
        - Ждёт 2:00 с помощью встроенного таймера Temporal (не висит в памяти!).
        - В 2:00: отправляет задачу в очередь tasks (через брокер Redis).

    Executor (исполнитель):
        - Постоянно слушает очередь tasks.
        - Получает задачу: "Выполни команду на устройстве 1".
        - Эмулирует выполнение: ждёт 2 секунды, генерирует вывод.
        - Отправляет результат в очередь results.

'''



# worker/main.py
import asyncio
import logging
from temporalio.client import Client
from temporalio.worker import Worker

# Импортируем наш Workflow и Activity
from workflows.schedule_workflow import (
    ScheduleExecutionWorkflow,
    publish_task_to_redis,
    wait_for_result_from_redis,
    save_result_to_api,
    fetch_command_details  # <-- Получить данные о команде из БД (через апи)
)

logging.basicConfig(level=logging.INFO) # включаем систему логирования


async def main():
    # Подключение к Temporal Server это нужно чтобы выполнять Workflow
    # Эти переменные окружения будут переданы из docker-compose.yml
    TEMPORAL_HOST = "scheduled_commands_temporal"  # Имя сервиса Temporal в Docker Compose
    TEMPORAL_PORT = "7233"
    TEMPORAL_NAMESPACE = "default"

    TEMPORAL_URL = f"http://{TEMPORAL_HOST}:{TEMPORAL_PORT}"

    logging.info(f"Connecting to Temporal at {TEMPORAL_URL}, namespace: {TEMPORAL_NAMESPACE}")

    try: # Пытается подключиться к Temporal Server
        client = await Client.connect(
            target_host=TEMPORAL_URL,
            namespace=TEMPORAL_NAMESPACE,
        )
        logging.info("Successfully connected to Temporal")
    except Exception as e:
        logging.error(f"Failed to connect to Temporal: {e}")
        return

    # Создание и запуск Worker'а
    try:
        worker = Worker(
            client,
            task_queue="scheduled-tasks",  # Должна совпадать с task_queue_name в API
            workflows=[ScheduleExecutionWorkflow],  # Список классов Workflow
            activities=[
                publish_task_to_redis,
                wait_for_result_from_redis,
                save_result_to_api,
                fetch_command_details
            ],
        )
        logging.info("Starting Temporal Worker...")
        await worker.run()
    except Exception as e:
        logging.error(f"Error while running Temporal Worker: {e}")


if __name__ == "__main__":
    asyncio.run(main())