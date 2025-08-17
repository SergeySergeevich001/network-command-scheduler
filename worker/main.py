# worker/main.py
import asyncio
import logging
from temporalio.client import Client
from temporalio.worker import Worker

# Импортируем наш Workflow и Activity
# Обратите внимание на обновленный импорт - добавлена fetch_command_details
from workflows.schedule_workflow import (
    ScheduleExecutionWorkflow,
    publish_task_to_redis,
    wait_for_result_from_redis,
    save_result_to_api,
    fetch_command_details  # <-- Добавлен импорт новой Activity
)

logging.basicConfig(level=logging.INFO)


async def main():
    # Подключение к Temporal Server
    # Эти переменные окружения будут переданы из docker-compose.yml
    TEMPORAL_HOST = "scheduled_commands_temporal"  # Имя сервиса Temporal в Docker Compose
    TEMPORAL_PORT = "7233"
    TEMPORAL_NAMESPACE = "default"

    TEMPORAL_URL = f"http://{TEMPORAL_HOST}:{TEMPORAL_PORT}"

    logging.info(f"Connecting to Temporal at {TEMPORAL_URL}, namespace: {TEMPORAL_NAMESPACE}")

    try:
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
            # Обновлен список Activity добавлена fetch_command_details
            activities=[
                publish_task_to_redis,
                wait_for_result_from_redis,
                save_result_to_api,
                fetch_command_details  # Добавлена новая Activity
            ],
            # Добавьте другие параметры Worker'а при необходимости
        )
        logging.info("Starting Temporal Worker...")
        await worker.run()
    except Exception as e:
        logging.error(f"Error while running Temporal Worker: {e}")


if __name__ == "__main__":
    asyncio.run(main())