from contextlib import asynccontextmanager
from typing import Any, List, Type, TypeVar

import asyncpg
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class EZQLTransaction:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def execute(self, query: str, *args: Any) -> None:
        await self._conn.execute(query, *args)

    async def query_as(self, model: Type[T], query: str, *args: Any) -> List[T]:
        rows = await self._conn.fetch(query, *args)
        return [model(**row) for row in rows]

class EZQL:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    @asynccontextmanager
    async def transaction(self):
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                yield EZQLTransaction(conn=conn) # type: ignore

    async def execute(self, query: str, *args: Any) -> None:
        """
        Executes a query and ignores the result set.

        Use this method for operations where the return type is irrelevant
        and only the database state change (side effect) is required.
        """
        async with self._pool.acquire() as conn:
            await conn.execute(query, *args)

    async def query_as(self, model: Type[T], query: str, *args: Any) -> List[T]:
        """Executes a query and maps the result set to a list of model instances.

        Use this method when type-strict results are required. It automatically
        performs data validation and transformation into the specified model class.

        Args:
            model (Type[T]): The Pydantic model class to instantiate.
            query (str): The SQL query to execute.
            *args (Any): Positional arguments for the SQL query parameters.

        Returns:
            List[T]: A list of objects instantiated from the result rows.
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *args)

        return [model(**row) for row in rows]


async def create_client(
    user: str,
    password: str,
    database: str,
    host: str,
    min_connections: int = 2,
    max_connections: int = 10,
) -> EZQL:
    pool = await asyncpg.create_pool(
        user=user,
        password=password,
        database=database,
        host=host,
        min_size=min_connections,
        max_size=max_connections,
    )

    return EZQL(pool=pool)
