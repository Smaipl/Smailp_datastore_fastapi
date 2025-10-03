import asyncio
import secrets
from .db import get_db
from .utils import hash_token

"""
Модуль init_admin: Скрипт для создания первого администраторского токена
Компоненты:
  - main: Основная функция для создания токена администратора
"""


async def main():
    """
    Создает администраторский токен и выводит его в консоль

    Действия:
      - Генерирует случайный токен
      - Хэширует токен с использованием PEPPER
      - Сохраняет хэш токена в базу данных
      - Выводит сырой токен в консоль для сохранения
    """
    pool = await get_db()
    raw_token = secrets.token_urlsafe(32)
    hashed = hash_token(raw_token)
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO api_tokens (token_hash, role, comment, created_by) VALUES ($1,$2,$3,$4)",
            hashed,
            "admin",
            "initial admin",
            "init_script",
        )
    print("Admin token created:")
    print(raw_token)


if __name__ == "__main__":
    asyncio.run(main())
