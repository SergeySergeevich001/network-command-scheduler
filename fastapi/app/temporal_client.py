#Настройка подключения к Temporal
from temporalio.client import Client
import os

# Глобальный клиент Temporal
temporal_client: Client = None

'''
    у меня их 2, то что здесь запускает воркфлоу то, что  в ворке, отвечает за выполнение 

'''
async def get_temporal_client() -> Client:
    global temporal_client
    if temporal_client is None:
        TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "scheduled_commands_temporal")
        TEMPORAL_PORT = os.getenv("TEMPORAL_PORT", "7233")
        TEMPORAL_NAMESPACE = os.getenv("TEMPORAL_NAMESPACE", "default")

        TEMPORAL_URL = f"http://{TEMPORAL_HOST}:{TEMPORAL_PORT}"

        try:
            temporal_client = await Client.connect(
                target_host=TEMPORAL_URL,
                namespace=TEMPORAL_NAMESPACE,
            )
            print(f"Successfully connected to Temporal at {TEMPORAL_URL}, namespace: {TEMPORAL_NAMESPACE}")
        except Exception as e:
            print(f"Failed to connect to Temporal at {TEMPORAL_URL}: {e}")
            raise
    return temporal_client
#Конец настройки подключения к Temporal