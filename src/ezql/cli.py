import asyncio

import typer
import os
from rich import print
from ezql.validator import find_models, validate_models

app = typer.Typer()

@app.command()
def check(
    path: str,
    dsn: str = typer.Option(..., "--dsn", help="asyncpg DSN, e.g. postgresql://user:pass@host/db"),
):
    if os.path.isfile(path):
        print("[bold red]Provided path is a file, files are not supported[/bold red]")
        return

    if not os.path.isdir(path):
        print("[bold red]Provided path does not exist[/bold red]")
        return

    models = find_models(path)
    print(f"Found [bold]{len(models)}[/bold] models. Validating against DB...")

    asyncio.run(validate_models(models, dsn))

if __name__ == "__main__":
    app()