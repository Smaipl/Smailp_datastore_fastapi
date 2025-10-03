import os
import asyncpg
from dotenv import load_dotenv
import time
import logging

"""
Модуль db: Подключение к базе данных PostgreSQL с обработкой ошибок
Компоненты:
  - DATABASE_URL: URL подключения к базе данных
  - db_pool: Пул подключений к БД
Функции:
  - get_db: Получение пула подключений к БД с реконнектом
"""

logger = logging.getLogger(__name__)

load_dotenv()

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "logs_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "logs_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "logs_pass")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

db_pool = None


async def get_db(max_retries: int = 5, retry_delay: int = 2):
    """
    Инициализирует и возвращает пул подключений к базе данных с реконнектом

    Args:
        max_retries: Максимальное количество попыток подключения
        retry_delay: Задержка между попытками в секундах

    Returns:
        asyncpg.pool.Pool: Пул подключений к PostgreSQL
    """
    global db_pool
    if db_pool:
        return db_pool

    for attempt in range(max_retries):
        try:
            db_pool = await asyncpg.create_pool(
                DATABASE_URL, min_size=1, max_size=10, command_timeout=30
            )
            logger.info("Successfully connected to PostgreSQL")
            return db_pool
        except (ConnectionRefusedError, asyncpg.CannotConnectNowError, OSError) as e:
            logger.error(
                f"Connection attempt {attempt+1}/{max_retries} failed: {str(e)}"
            )
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.critical(
                    "Failed to connect to PostgreSQL after multiple attempts"
                )
                raise RuntimeError("Failed to connect to PostgreSQL") from e
        except asyncpg.PostgresError as e:
            logger.critical(f"PostgreSQL connection error: {str(e)}")
            raise
        except Exception as e:
            logger.critical(f"Unexpected connection error: {str(e)}")
            raise

    # This should never be reached
    raise RuntimeError("Failed to establish database connection")
