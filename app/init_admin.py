import asyncio
import secrets
from .db import get_db
from .utils import hash_token


async def main():
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
