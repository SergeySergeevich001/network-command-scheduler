# worker/workflows/schedule_workflow.py
import asyncio
import logging
from datetime import datetime, timedelta
from temporalio import workflow, activity
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError
import json

# Настройка логгирования
logger = logging.getLogger(__name__)


# Импорты для Redis и HTTP внутри Activity
# так как они выполняются отдельно от Workflow

@activity.defn
async def fetch_command_details(command_id: str) -> dict:
    # Получение деталей команды по command_id через API.
    logger_activity = logging.getLogger(f"{__name__}.fetch_command_details")

    import os
    API_HOST = os.getenv("API_HOST", "scheduled_commands_api")
    API_PORT = os.getenv("API_PORT", "8000")
    API_BASE_URL = f"http://{API_HOST}:{API_PORT}"

    url = f"{API_BASE_URL}/commands/{command_id}"
    logger_activity.info(f"Fetching command details from API: GET {url}")

    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()

            command_data = response.json()
            command_string = command_data.get("command_string", "")

            logger_activity.info(f"Retrieved command_string: '{command_string}' for command_id: {command_id}")
            return {
                "command_string": command_string
            }

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error {e.response.status_code} while fetching command details: {e.response.text}"
        logger_activity.error(error_msg)
        raise ApplicationError(error_msg)
    except httpx.RequestError as e:
        error_msg = f"Network error while fetching command details for command_id {command_id}: {e}"
        logger_activity.error(error_msg)
        raise ApplicationError(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error while fetching command details for command_id {command_id}: {e}"
        logger_activity.error(error_msg)
        raise ApplicationError(error_msg)


@activity.defn
async def publish_task_to_redis(input_data: dict) -> bool:
    # Публикация задачи в Redis Streams.
    import redis
    import os

    REDIS_HOST = os.getenv("REDIS_HOST", "scheduled_commands_redis")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

    logger.info(f"Publishing task to Redis Stream 'tasks' at {REDIS_HOST}:{REDIS_PORT}")

    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

        task_message = {
            "schedule_id": input_data.get("schedule_id"),
            "command_id": input_data.get("command_id"),
            "device_id": input_data.get("device_id"),
            "command_string": input_data.get("command_string", ""),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        msg_id = r.xadd("tasks", task_message)
        logger.info(f"Task published to Redis Stream 'tasks' with ID: {msg_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to publish task to Redis: {e}")
        raise ApplicationError(f"Failed to publish task: {str(e)}")


@activity.defn
async def wait_for_result_from_redis(schedule_id: str) -> dict:
    # Ожидание результата из Redis Streams.
    import redis
    import os

    REDIS_HOST = os.getenv("REDIS_HOST", "scheduled_commands_redis")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

    logger.info(f"Waiting for result for schedule {schedule_id} from Redis Stream 'results'")

    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

        consumer_group = f"worker_group_{schedule_id}"
        stream_name = "results"

        try:
            r.xgroup_create(stream_name, consumer_group, id='0', mkstream=True)
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
            else:
                logger.info(f"Consumer group '{consumer_group}' already exists for stream '{stream_name}'")

        start_time = datetime.utcnow()
        timeout_duration = timedelta(minutes=5)

        while datetime.utcnow() - start_time < timeout_duration:
            messages = r.xreadgroup(consumer_group, "worker_instance_1", {stream_name: '>'}, count=1, block=5000)

            if messages:
                for stream, message_list in messages:
                    for message_id, message_dict in message_list:
                        logger.info(f"Received message from Redis: ID={message_id}, Data={message_dict}")

                        if message_dict.get("schedule_id") == schedule_id:
                            logger.info(f"Found result for schedule {schedule_id}")
                            r.xack(stream_name, consumer_group, message_id)
                            r.xdel(stream_name, message_id)
                            return message_dict
                        else:
                            logger.debug(f"Message {message_id} is not for schedule {schedule_id}, skipping...")
            else:
                logger.debug("No messages received in the last 5 seconds, checking timeout...")

        raise ApplicationError(f"Timeout waiting for result for schedule {schedule_id}")

    except ApplicationError:
        raise
    except Exception as e:
        logger.error(f"Failed to wait for result from Redis: {e}")
        raise ApplicationError(f"Failed to wait for result: {str(e)}")


@activity.defn
async def save_result_to_api(input_data: dict) -> bool:
    # Сохранение результата выполнения команды через API.
    import httpx
    import os

    API_HOST = os.getenv("API_HOST", "scheduled_commands_api")
    API_PORT = os.getenv("API_PORT", "8000")
    API_BASE_URL = f"http://{API_HOST}:{API_PORT}"

    schedule_id = input_data.get("schedule_id")
    device_id = input_data.get("device_id")
    result_data = input_data.get("result_data")

    if not schedule_id or not device_id or not result_data:
        error_msg = "Missing required data for saving result to API"
        logger.error(error_msg)
        raise ApplicationError(error_msg)

    url = f"{API_BASE_URL}/devices/{device_id}/schedules/{schedule_id}/result/"
    logger.info(f"Calling API to save result: POST {url}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=result_data, timeout=30.0)
            response.raise_for_status()
            logger.info(f"Successfully saved result to API for schedule {schedule_id}. Status: {response.status_code}")
            return True
    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error {e.response.status_code} while saving result to API: {e.response.text}"
        logger.error(error_msg)
        raise ApplicationError(error_msg)
    except httpx.RequestError as e:
        error_msg = f"Request error while saving result to API: {e}"
        logger.error(error_msg)
        raise ApplicationError(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error while saving result to API: {e}"
        logger.error(error_msg)
        raise ApplicationError(error_msg)


@workflow.defn
class ScheduleExecutionWorkflow:
    @workflow.run
    async def run(self, input_data: dict):
        # Основной Workflow для выполнения команды по расписанию.

        # Args:
        #     input_data (dict): Данные расписания.

        # Returns:
        #     dict: Результат выполнения.
        logger.info(f"Workflow started for schedule: {input_data}")

        schedule_id = input_data.get("schedule_id")
        command_id = input_data.get("command_id")
        device_id = input_data.get("device_id")
        cron_expression = input_data.get("cron_expression")

        try:
            logger.info(f"Waiting for next execution time based on cron: {cron_expression}")

            # Получаем command_string из API
            logger.info(f"Fetching command details for command_id: {command_id}")
            command_details = await workflow.execute_activity(
                fetch_command_details,
                command_id,
                start_to_close_timeout=timedelta(seconds=15),
                retry_policy=RetryPolicy(
                    maximum_attempts=3,
                    backoff_coefficient=2.0,
                    initial_interval=timedelta(seconds=1)
                )
            )
            command_string = command_details.get("command_string", "")
            logger.info(f"Successfully fetched command_string: '{command_string}'")

            # Публикуем задачу в Redis
            logger.info("Publishing task to Redis Stream 'tasks'...")
            task_data = {
                "schedule_id": schedule_id,
                "command_id": command_id,
                "device_id": device_id,
                "command_string": command_string
            }
            await workflow.execute_activity(
                publish_task_to_redis,
                task_data,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=3)
            )

            # Ждем результата из Redis
            logger.info("Waiting for result from Redis Stream 'results'...")
            result_data = await workflow.execute_activity(
                wait_for_result_from_redis,
                schedule_id,
                start_to_close_timeout=timedelta(minutes=6),
                retry_policy=RetryPolicy(maximum_attempts=1)
            )

            logger.info(f"Received result from executor: {result_data}")

            # Сохраняем результат в API
            logger.info("Saving result to API service...")
            save_result_input = {
                "schedule_id": schedule_id,
                "device_id": device_id,
                "result_data": {
                    "output": result_data.get("output"),
                    "status": result_data.get("status")
                }
            }
            await workflow.execute_activity(
                save_result_to_api,
                save_result_input,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=3)
            )
            logger.info("Result successfully saved to API service.")

            return {
                "schedule_id": schedule_id,
                "status": "completed",
                "result": result_data
            }

        except Exception as e:
            logger.error(f"Error in ScheduleExecutionWorkflow for schedule {schedule_id}: {e}")
            return {
                "schedule_id": schedule_id,
                "status": "failed",
                "error": str(e)
            }
