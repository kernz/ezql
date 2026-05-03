# EzQL

> [!WARNING]
> Its not recommended to use in production right now, API is currently unstable

EzQL - a simple wrapper around asyncpg that makes writing raw SQL in python a little easier

SQLAlchemy is overkill and you need something simpler? Have you tried writing raw SQL in Python but ended up in tears because there's no type safety? Then EzQL is your choice

Why use another bloated ORM when you can interact with your database in the most intuitive and simple way?

## Good place to start

PostgreSQL is an open-source relational database beloved by most developers for its reliability, performance, and rich feature set - from advanced indexing and full-text search to JSON support and powerful extensions like PostGIS.

If you're new to PostgreSQL, here are the best places to start:

- [Official PostgreSQL Documentation](https://www.postgresql.org/docs/) — comprehensive and well-written
- [PostgreSQL Tutorial](https://www.postgresqltutorial.com/) — beginner-friendly with practical examples

## Installation

```bash
uv add ezql
pip install ezql
```

## Example

```python
import asyncio
from pydantic import BaseModel
from ezql import create_client

class User(BaseModel):
    __table__ = "users" # Marks this model as an EzQL model

    id: int
    name: str

async def main():
    client = await create_client(
        user,
        password,
        database,
        host,
        min_connections,
        max_connections
    )

    # Does not return anything
    await client.execute("INSERT INTO users (name) VALUES ($1)", "Nazar")

    # Returns either list of users or an empty list
    users = await client.query_as(User, "SELECT id, name FROM users WHERE name = $1", "Nazar")

    assert users[0].name == "Nazar"
    assert len(users) == 1
    assert isinstance(users[0], User)


if __name__ == "__main__":
    asyncio.run(main())
```

## Joins

```python
class UserWithPosts(BaseModel):
    # No __table__ — this is a DTO, not a table model
    user_name: str
    post_title: str

users_with_posts = await client.query_as(UserWithPosts, """
    SELECT users.name as user_name, posts.title as post_title
    FROM users
    JOIN posts ON posts.user_id = users.id
    WHERE users.id = $1
""", user_id)
```

> [!WARNING]
> Always select columns explicitly when using joins. Using `SELECT *` may cause a `ValidationError` at runtime.

No magic - you write the SQL, EzQL maps the result.

## Transactions

```python
async with client.transaction() as tx:
    user = await tx.query_as(User, "INSERT INTO users (name) VALUES ($1) RETURNING id, name", "Nazar")
    await tx.execute("INSERT INTO posts (user_id, title) VALUES ($1, $2)", user[0].id, "My first post")
```

If any query fails, the entire transaction is rolled back automatically.

## Validate your models before production blows up

```bash
ezql ./models-dir --dsn postgresql://test:testpassword@localhost:5432/test
```

```py
Found 1 models. Validating against DB...

Validating User → table users
┏━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━┓
┃ Field ┃ Model type    ┃ DB type ┃ Status ┃
┡━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━┩
│ id    │ <class 'int'> │ integer │ ✓      │
│ name  │ <class 'str'> │ text    │ ✓      │
└───────┴───────────────┴─────────┴────────┘

All models are valid ✓
```

# TODO

- Migration tool
- Validate queries
