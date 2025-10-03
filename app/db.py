import os
import asyncpg
from dotenv import load_dotenv

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
    global db_pool
    if db_pool is None:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    return db_pool
