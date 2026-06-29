from __future__ import annotations

import typer

from field_practice.doctor_cli import doctor_command
from field_practice.document_cli import document_app
from field_practice.draft_cli import draft_app

app = typer.Typer(
    help="Field-practice submission workflow.",
    no_args_is_help=True,
)
app.command("doctor")(doctor_command)
app.add_typer(draft_app, name="draft")
app.add_typer(document_app, name="document")


if __name__ == "__main__":
    app()
