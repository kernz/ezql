import pytest
from icecream import ic
from pydantic import BaseModel
from ezql import EZQL

class User(BaseModel):
    __table__ = "users"

    id: int
    name: str

class UserWithPosts(BaseModel):
    user_name: str
    post_title: str

@pytest.mark.asyncio
async def test_query_as_valid(db: EZQL):
    async with db._pool.acquire() as conn:
        await conn.execute("INSERT INTO users (name) VALUES ($1)", "Nazar")

    users = await db.query_as(User, "SELECT id, name FROM users WHERE name = $1", "Nazar")

    ic(users)

    assert len(users) == 1
    assert users[0].name == "Nazar"
    assert isinstance(users[0], User)

@pytest.mark.asyncio
async def test_query_as_empty(db: EZQL):
    users = await db.query_as(User, "SELECT id, name FROM users WHERE name = $1", "NonExistent")
    assert users == []

@pytest.mark.asyncio
async def test_query_insert_with_returning(db: EZQL):
    users = await db.query_as(User, "INSERT INTO users (name) VALUES ($1) RETURNING id, name", "Alice")

    ic(users)
    assert len(users) == 1
    assert users[0].name == "Alice"
    assert isinstance(users[0], User)

@pytest.mark.asyncio
async def test_query_insert_without_returning(db: EZQL):
    returning = await db.query_as(User, "INSERT INTO users (name) VALUES ($1)", "Bob")

    users = await db.query_as(User, "SELECT id, name FROM users WHERE name = $1", "Bob")

    ic(users)
    assert len(users) == 1
    assert returning == []
    assert users[0].name == "Bob"
    assert isinstance(users[0], User)

@pytest.mark.asyncio
async def test_query_invalid_sql(db: EZQL):
    with pytest.raises(Exception):
        await db.query_as(User, "SELECT non_existent_column FROM users")

@pytest.mark.asyncio
async def test_query_invalid_model(db: EZQL):
    class InvalidModel(BaseModel):
        non_existent_field: str

    with pytest.raises(Exception):
        await db.query_as(InvalidModel, "SELECT id, name FROM users")

@pytest.mark.asyncio
async def test_query_update_with_returning(db: EZQL):
    users = await db.query_as(User, "INSERT INTO users (name) VALUES ($1) RETURNING id, name", "Charlie")

    ic(users)
    assert len(users) == 1
    assert users[0].name == "Charlie"
    assert isinstance(users[0], User)

    updated_users = await db.query_as(User, "UPDATE users SET name = $1 WHERE id = $2 RETURNING id, name", "Charlie Updated", users[0].id)

    ic(updated_users)
    assert len(updated_users) == 1
    assert updated_users[0].name == "Charlie Updated"
    assert isinstance(updated_users[0], User)

@pytest.mark.asyncio
async def test_query_update_without_returning(db: EZQL):
    users = await db.query_as(User, "INSERT INTO users (name) VALUES ($1) RETURNING id, name", "Dave")

    assert len(users) == 1
    assert users[0].name == "Dave"
    assert isinstance(users[0], User)

    returning = await db.query_as(User, "UPDATE users SET name = $1 WHERE id = $2", "Dave Updated", users[0].id)

    assert returning == []

    updated_users = await db.query_as(User, "SELECT id, name FROM users WHERE id = $1", users[0].id)

    ic(updated_users)
    assert len(updated_users) == 1
    assert updated_users[0].name == "Dave Updated"
    assert isinstance(updated_users[0], User)

@pytest.mark.asyncio
async def test_join_query(db: EZQL):
    user = await db.query_as(User, "INSERT INTO users (name) VALUES ($1) RETURNING id, name", "Nazar")
    await db.execute("INSERT INTO posts (user_id, title) VALUES ($1, $2)", user[0].id, "My first post")

    result = await db.query_as(UserWithPosts, """
        SELECT users.name as user_name, posts.title as post_title
        FROM users
        JOIN posts ON posts.user_id = users.id
        WHERE users.id = $1
    """, user[0].id)

    assert len(result) == 1
    assert result[0].user_name == "Nazar"
    assert result[0].post_title == "My first post"
    assert isinstance(result[0], UserWithPosts)

@pytest.mark.asyncio
async def test_transaction_commit(db: EZQL):
    async with db.transaction() as tx:
        await tx.execute("INSERT INTO users (name) VALUES ($1)", "TransactionUser")

    users = await db.query_as(User, "SELECT id, name FROM users WHERE name = $1", "TransactionUser")
    assert len(users) == 1
    assert users[0].name == "TransactionUser"

@pytest.mark.asyncio
async def test_transaction_rollback(db: EZQL):
    with pytest.raises(Exception):
        async with db.transaction() as tx:
            await tx.execute("INSERT INTO users (name) VALUES ($1)", "RollbackUser")
            raise Exception("Forced rollback")

    users = await db.query_as(User, "SELECT id, name FROM users WHERE name = $1", "RollbackUser")
    assert users == []

@pytest.mark.asyncio
async def test_transaction_query_as(db: EZQL):
    async with db.transaction() as tx:
        await tx.execute("INSERT INTO users (name) VALUES ($1)", "TxQueryUser")
        users = await tx.query_as(User, "SELECT id, name FROM users WHERE name = $1", "TxQueryUser")

    assert len(users) == 1
    assert users[0].name == "TxQueryUser"
    assert isinstance(users[0], User)