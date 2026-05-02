import importlib
import inspect
import os
import pkgutil
import sys
from typing import List, Type
import asyncpg
from pydantic import BaseModel
from rich import print
from rich.table import Table


def find_models(folder_path: str) -> List[Type[BaseModel]]:
    abs_path = os.path.abspath(folder_path)

    parent_dir = os.path.dirname(abs_path)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    package_name = os.path.basename(abs_path)
    models = []

    for loader, modname, ispkg in pkgutil.walk_packages([abs_path], package_name + "."):
        try:
            module = importlib.import_module(modname)
            for name, obj in inspect.getmembers(module):
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, BaseModel)
                    and obj is not BaseModel
                    and hasattr(obj, "__table__")
                    and obj not in models
                ):
                    models.append(obj)
        except ImportError as e:
            print(f"Skipping module {modname}: {e}")

    return models


PG_TYPE_MAP = {
    "integer": int,
    "bigint": int,
    "smallint": int,
    "serial": int,
    "bigserial": int,
    "text": str,
    "varchar": str,
    "character varying": str,
    "char": str,
    "boolean": bool,
    "float": float,
    "real": float,
    "double precision": float,
    "numeric": float,
    "json": dict,
    "jsonb": dict,
    "uuid": str,
}


async def get_table_columns(
    conn: asyncpg.Connection, table_name: str
) -> dict[str, str]:
    rows = await conn.fetch(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = $1 AND table_schema = 'public'
        """,
        table_name,
    )
    return {row["column_name"]: row["data_type"] for row in rows}


def check_type_compat(py_type: type, pg_type: str) -> bool:
    expected = PG_TYPE_MAP.get(pg_type)
    if expected is None:
        return True
    return py_type is expected


async def validate_models(models: List[Type[BaseModel]], dsn: str) -> None:
    try:
        conn = await asyncpg.connect(dsn)
    except Exception as e:
        print(f"[bold red]Failed to connect to DB:[/bold red] {e}")
        return

    try:
        all_ok = True

        for model in models:
            table = model.__table__
            print(
                f"\n[bold cyan]Validating[/bold cyan] {model.__name__} → table [italic]{table}[/italic]"
            )

            exists = await conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = $1 AND table_schema = 'public')",
                table,
            )
            if not exists:
                print(f"  [bold red]✗[/bold red] Table '{table}' does not exist in DB")
                all_ok = False
                continue

            db_columns = await get_table_columns(conn, table)
            model_fields = model.model_fields

            table_out = Table(show_header=True, header_style="bold magenta")
            table_out.add_column("Field")
            table_out.add_column("Model type")
            table_out.add_column("DB type")
            table_out.add_column("Status")

            for field_name, field_info in model_fields.items():
                py_type = field_info.annotation

                if field_name not in db_columns:
                    table_out.add_row(
                        field_name,
                        str(py_type),
                        "—",
                        "[red]✗ missing in DB[/red]",
                    )
                    all_ok = False
                    continue

                pg_type = db_columns[field_name]
                compat = check_type_compat(py_type, pg_type)

                status = (
                    "[green]✓[/green]" if compat else "[yellow]⚠ type mismatch[/yellow]"
                )
                if not compat:
                    all_ok = False

                table_out.add_row(field_name, str(py_type), pg_type, status)

            for col in db_columns:
                if col not in model_fields:
                    table_out.add_row(
                        col, "—", db_columns[col], "[red]✗ missing in model[/red]"
                    )
                    all_ok = False

            print(table_out)

        print()
        if all_ok:
            print("[bold green]All models are valid ✓[/bold green]")
        else:
            print("[bold red]Validation finished with errors ✗[/bold red]")

    finally:
        await conn.close()
