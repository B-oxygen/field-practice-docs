from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from field_practice.direct_template_inspect import (
    TemplateInspectRequest,
    inspect_templates,
)
from field_practice.rhwp_backend import hop_status, rhwp_status


def doctor_command(
    weekly_template: Annotated[
        Path | None,
        typer.Option(help="Optional weekly HWPX template to inspect"),
    ] = None,
    final_template: Annotated[
        Path | None,
        typer.Option(help="Optional final HWPX template to inspect"),
    ] = None,
    out: Annotated[
        Path,
        typer.Option(help="Template inspection output directory"),
    ] = Path("reports/doctor"),
) -> None:
    rhwp = rhwp_status()
    hop = hop_status()
    typer.echo(rhwp.note)
    typer.echo(hop.note)
    if weekly_template is None and final_template is None:
        return
    if weekly_template is None or final_template is None:
        msg = "--weekly-template and --final-template must be provided together"
        raise typer.BadParameter(msg)
    result = inspect_templates(
        TemplateInspectRequest(
            weekly_template=weekly_template,
            final_template=final_template,
            out_dir=out,
        )
    )
    typer.echo(f"wrote template inspection to {result.markdown}")
