# Система выполнения команд по расписанию на сетевых устройствах

![Docker Compose](https://img.shields.io/badge/docker--compose-up-blue) ![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.100.0%2B-brightgreen) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13-blue) ![Redis](https://img.shields.io/badge/Redis-7--alpine-red) ![Temporal](https://img.shields.io/badge/Temporal-latest-orange)

## Описание

Этот проект реализует систему для автоматического выполнения команд на сетевых устройствах по заданному расписанию. Она позволяет пользователям:

1.  Регистрировать сетевые устройства (IP, тип, учетные данные).
2.  Определять команды, которые нужно выполнить на этих устройствах.
3.  Создавать расписания (используя cron-выражения) для автоматического запуска этих команд.
4.  Просматривать историю выполнения команд и их результаты.

Архитектура системы построена на микросервисах и использует оркестрацию для надежного и масштабируемого выполнения задач.

## Архитектура

Система состоит из следующих компонентов:

*   **API-Сервис (`api`)**: Основная точка входа. Предоставляет RESTful API для управления устройствами, командами, расписаниями и результатами выполнения. Построен на FastAPI.
*   **Temporal Worker (`worker`)**: Сервис, который подключается к серверу Temporal и выполняет Workflow (`ScheduleExecutionWorkflow`). Workflow отвечает за ожидание времени выполнения, взаимодействие с брокером сообщений (Redis Streams) и вызов API для сохранения результатов.
*   **Executor (`executor`)**: Сервис, который "выполняет" команды. Он подписывается на поток `tasks` в Redis Streams, получает задачи, "эмулирует" выполнение (в реальной системе здесь был бы код для подключения к устройству и выполнения команды) и публикует результат в поток `results` в Redis Streams.
*   **Temporal Server (`temporal`)**: Сервер оркестрации Workflow. Управляет жизненным циклом Workflow и Activity, обеспечивает надежность и отслеживаемость процессов.
*   **Temporal Web UI (`temporal-ui`)**: Веб-интерфейс для мониторинга и отладки Workflow'ов, запущенных на Temporal Server.
*   **PostgreSQL (`postgresql`)**: Реляционная база данных для хранения информации об устройствах, командах, расписаниях и результатах выполнения.
*   **Redis (`redis`)**: Брокер сообщений (Redis Streams) для асинхронного обмена задачами (`tasks`) и результатами (`results`) между Temporal Worker'ом и Executor'ом.
*   **Тесты (`api-test`)**: Сервис (контейнер), используемый для запуска автоматических тестов (юнит- и интеграционных).

## Технологии

*   **Язык программирования**: Python 3.10+
*   **Веб-фреймворк**: FastAPI (асинхронный)
*   **ORM**: SQLAlchemy (асинхронный)
*   **База данных**: PostgreSQL
*   **Брокер сообщений**: Redis Streams
*   **Оркестрация**: Temporal
*   **Контейнеризация**: Docker, Docker Compose
*   **Тестирование**: Pytest

## Быстрый старт

### Предварительные требования

*   Установленный [Docker](https://www.docker.com/products/docker-desktop/)
*   Установленный [Docker Compose](https://docs.docker.com/compose/install/) (обычно идет вместе с Docker Desktop)

### Запуск

1.  **Клонируйте репозиторий** (если вы его еще не скачали):
    ```bash
    git clone <URL_вашего_репозитория>
    cd <имя_папки_проекта>
    ```
2.  **(Опционально) Настройте переменные окружения**:
    *   Проверьте файл `.env` в корне проекта. При необходимости измените значения по умолчанию (например, пароль к БД).
3.  **Запустите все сервисы**:
    *   Выполните команду в корневой директории проекта:
        ```bash
        docker-compose up -d
        ```
    *   Эта команда соберет (если нужно) и запустит все необходимые контейнеры в фоновом режиме.
4.  **Дождитесь запуска**:
    *   Подождите пару минут, пока все сервисы полностью запустятся. Контейнеры `postgresql` и `temporal` должны перейти в состояние `Healthy`.
    *   Проверить статус можно командой:
        ```bash
        docker-compose ps
        ```
    *   Всего контейнеров 8 (один с тестами), бывает воркер пытается стартовать раньше чем поднялся темпорал (проще всего поднять руками через гуи докера), после каких либо нюансов не возникает
### Доступ к сервисам

*   **Swagger UI (API Документация/Тестирование)**: `http://localhost:8000/docs`
*   **Temporal Web UI (Мониторинг Workflow'ов)**: `http://localhost:8080`
*   **PostgreSQL**: `localhost:5432` (данные подключения в `.env`)
*   **Redis**: `localhost:6379`

## Использование

После запуска системы вы можете взаимодействовать с ней через Swagger UI (`http://localhost:8000/docs`):

1.  **Создайте устройство**: Используйте эндпоинт `POST /devices/`.
2.  **Создайте команду для устройства**: Используйте эндпоинт `POST /devices/{device_id}/commands/`.
3.  **Создайте расписание для команды**: Используйте эндпоинт `POST /devices/{device_id}/commands/{command_id}/schedules/`. Укажите `cron_expression` (например, `*/1 * * * *` для выполнения каждую минуту).
4.  **Просмотрите результаты**: Через некоторое время (в зависимости от `cron_expression`) результат выполнения появится. Проверить его можно через эндпоинт `GET /devices/{device_id}/results/`.

## Тестирование

Проект включает юнит-тесты и интеграционные тесты.

### Запуск тестов

*   Убедитесь, что основные сервисы (`postgresql`, `redis`, `temporal`) запущены:
    ```bash
    docker-compose up -d postgresql redis temporal
    ```
*   Запустите тесты в отдельном контейнере:
    ```bash
    docker-compose run --rm api-test pytest tests -v
    ```
*   Запустите конкретный тест:
    ```bash
    docker-compose run --rm api-test pytest tests/test_integration/test_full_flow.py::test_full_command_execution_flow -v
    ```

## Структура проекта
Проект организован по принципам микросервисной архитектуры. Каждый основной компонент находится в своей директории на одном уровне с другими.
   ```
.
├── api/ # API-сервис (FastAPI)
│ ├── app/ # Основное приложение
│ │ ├── api/ # Эндпоинты REST API
│ │ │ ├── init.py
│ │ │ ├── commands.py 
│ │ │ ├── devices.py
│ │ │ ├── results.py
│ │ │ └── schedules.py
│ │ ├── init.py
│ │ ├── database.py # Настройка асинхронного подключения к PostgreSQL
│ │ ├── main.py # Точка входа FastAPI приложения, настройка lifespan
│ │ ├── models.py # Модели SQLAlchemy для таблиц БД
│ │ └── schemas.py # Схемы Pydantic для валидации и сериализации данных
│ ├── Dockerfile # Dockerfile для сборки образа API-сервиса
│ ├── requirements.txt # Зависимости Python для API-сервиса
│ └── tests/ # Автоматические тесты
│ ├── test_integration/ # Интеграционные тесты
│ ├── test_unit/ # Юнит-тесты
│ └── conftest.py # Общие фикстуры и настройки для pytest
├── executor/ # Executor (обработчик задач)
│ ├── Dockerfile # Dockerfile для сборки образа Executor'а
│ ├── main.py # Точка входа Executor'а
│ └── requirements.txt # Зависимости Python для Executor'а
├── worker/ # Temporal Worker
│ ├── workflows/ # Определния Workflow и Activity
│ │ └── schedule_workflow.py # Логика ScheduleExecutionWorkflow
│ ├── Dockerfile # Dockerfile для сборки образа Temporal Worker'а
│ ├── main.py # Точка входа Worker'а
│ └── requirements.txt # Зависимости Python для Worker'а
├── docker-compose.yml # Конфигурация запуска всей системы
├── .env # Файл с переменными окружения
├── main.py #  главный управляющий файл API-сервиса
└── README.md # Этот файл

   ```