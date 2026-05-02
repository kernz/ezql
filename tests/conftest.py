# tests/conftest.py
import pytest_asyncio
from ezql import EZQL, create_client


@pytest_asyncio.fixture(scope="session")
async def db_pool():
    client = await create_client(
        user="test",
        password="testpassword",
        database="test",
        host="127.0.0.1",
        min_connections=1,
        max_connections=10,
    )

    async with client._pool.acquire() as conn:
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS users (id serial PRIMARY KEY, name text)"
        )
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS posts (id SERIAL PRIMARY KEY, user_id INT, title TEXT)"
        )

    yield client._pool

    async with client._pool.acquire() as conn:
        await conn.execute("DROP TABLE IF EXISTS posts")
        await conn.execute("DROP TABLE IF EXISTS users")
    await client._pool.close()


@pytest_asyncio.fixture(scope="session")
async def db(db_pool):
    return EZQL(pool=db_pool)
