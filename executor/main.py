# executor/main.py
import asyncio
import logging
import os
import redis
import json
import time
import uuid
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    # Параметры подключения к Redis
    REDIS_HOST = os.getenv("REDIS_HOST", "scheduled_commands_redis")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

    logger.info(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}")

    try:
        # Подключение к Redis
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
        r.ping()
        logger.info("Successfully connected to Redis")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return

    logger.info("Executor is running and waiting for tasks from Redis Stream 'tasks'...")

    # Настройка Redis Streams
    tasks_stream = "tasks"
    results_stream = "results"
    consumer_group = "executor_group"
    consumer_name = f"executor_{uuid.uuid4().hex}"

    # Создание группы потребителей
    try:
        r.xgroup_create(tasks_stream, consumer_group, id='0', mkstream=True)
        logger.info(f"Created consumer group '{consumer_group}' for stream '{tasks_stream}'")
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" in str(e):
            logger.info(f"Consumer group '{consumer_group}' already exists for stream '{tasks_stream}'")
        else:
            logger.error(f"Failed to create consumer group: {e}")
            return
    except Exception as e:
        logger.error(f"Unexpected error while creating consumer group: {e}")
        return

    # Основной цикл
    try:
        while True:
            # Чтение сообщений из потока 'tasks'
            messages = r.xreadgroup(consumer_group, consumer_name, {tasks_stream: '>'}, count=1, block=5000)

            if messages:
                for stream, message_list in messages:
                    for message_id, message_dict in message_list:
                        logger.info(f"Received task from Redis: ID={message_id}, Data={message_dict}")

                        try:
                            # Извлечение данных задачи
                            schedule_id = message_dict.get("schedule_id")
                            command_id = message_dict.get("command_id")
                            device_id = message_dict.get("device_id")
                            command_string = message_dict.get("command_string", "")

                            if not schedule_id:
                                logger.warning(f"Received task without schedule_id: {message_dict}")
                                r.xack(tasks_stream, consumer_group, message_id)
                                continue

                            # Эмуляция выполнения команды
                            logger.info(
                                f"Executing command '{command_string}' for device {device_id} (schedule {schedule_id})")

                            # Симуляция задержки
                            delay = random.randint(3, 7)
                            logger.info(f"Simulating execution delay of {delay} seconds...")
                            time.sleep(delay)

                            # Генерация результата
                            simulated_output = f"Command '{command_string}' executed successfully on device {device_id} at {time.strftime('%Y-%m-%d %H:%M:%S')}"
                            simulated_status = "success"

                            # С вероятностью 10% ошибка
                            if random.random() < 0.1:
                                simulated_output = f"Failed to execute command '{command_string}' on device {device_id}: Connection timeout"
                                simulated_status = "failed"

                            logger.info(f"Command execution completed. Output: {simulated_output}")

                            # Отправка результата в Redis Stream 'results'
                            result_message = {
                                "schedule_id": schedule_id,
                                "command_id": command_id,
                                "device_id": device_id,
                                "output": simulated_output,
                                "status": simulated_status,
                                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
                            }

                            # Публикация результата
                            result_msg_id = r.xadd(results_stream, result_message)
                            logger.info(f"Result published to Redis Stream '{results_stream}' with ID: {result_msg_id}")

                        except Exception as e:
                            logger.error(f"Error processing task {message_id}: {e}")

                        finally:
                            # Подтверждение обработки сообщения (ACK)
                            r.xack(tasks_stream, consumer_group, message_id)
                            logger.info(f"Task {message_id} acknowledged")

            else:
                logger.debug("No new tasks received, checking again...")

    except KeyboardInterrupt:
        logger.info("Executor stopped by user.")
    except Exception as e:
        logger.error(f"Unexpected error in executor main loop: {e}")
    finally:
        logger.info("Executor shutting down.")


if __name__ == "__main__":
    main()