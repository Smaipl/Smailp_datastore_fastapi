import os
import asyncpg
from dotenv import load_dotenv

"""
Модуль db: Подключение к базе данных PostgreSQL
Компоненты:
  - DATABASE_URL: URL подключения к базе данных
  - db_pool: Пул подключений к БД
Функции:
  - get_db: Получение пула подключений к БД
"""

# Загружаем переменные из .env. Если они отсутствуют, то используем значения по умолчанию.
# Если файл энвов другой, то в скобках говорим какой.
# load_dotenv(".env.dev")

load_dotenv()

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "logs_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "logs_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "logs_pass")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

db_pool = None


async def get_db():
    """
    Инициализирует и возвращает пул подключений к базе данных

    Returns:
        asyncpg.pool.Pool: Пул подключений к PostgreSQL

    Особенности:
        - Создает пул при первом вызове
        - Возвращает существующий пул при последующих вызовах
    """
    global db_pool
    if db_pool is None:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    return db_pool
