import os
import asyncpg

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://logs_user:logs_pass@db:5432/logs_db"
)
db_pool = None


async def get_db():
    global db_pool
    if db_pool is None:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    return db_pool
