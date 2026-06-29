from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer

from field_practice.cell_fill_command import fill_cells_command
from field_practice.direct_template_fill import DirectFillRequest, fill_templates
from field_practice.direct_template_inspect import (
    TemplateInspectRequest,
    inspect_templates,
)
from field_practice.export_hwpx import ExportHwpxRequest, export_hwpx

document_app = typer.Typer(
    help="Create and verify HWPX/PDF submission files.",
    no_args_is_help=True,
)
document_app.command("cells")(fill_cells_command)


@document_app.command("inspect")
def inspect_template_command(
    weekly_template: Annotated[Path, typer.Option(help="Weekly HWPX template")],
    final_template: Annotated[Path, typer.Option(help="Final HWPX template")],
    out: Annotated[Path, typer.Option(help="Inspection output directory")],
) -> None:
    result = inspect_templates(
        TemplateInspectRequest(
            weekly_template=weekly_template,
            final_template=final_template,
            out_dir=out,
        )
    )
    typer.echo(f"wrote template inspection to {result.markdown}")


@document_app.command("fill")
def fill_template_command(
    scenario: Annotated[str, typer.Option(help="480 or 640")],
    weekly_template: Annotated[Path, typer.Option(help="Weekly HWPX/HWP template")],
    final_template: Annotated[Path, typer.Option(help="Final HWPX/HWP template")],
    weekly_data: Annotated[Path, typer.Option(help="Enriched weekly CSV")],
    final_draft: Annotated[Path, typer.Option(help="Final report draft markdown")],
    monthly_draft: Annotated[Path, typer.Option(help="Monthly report draft markdown")],
    evidence: Annotated[Path, typer.Option(help="Evidence ledger CSV")],
    out: Annotated[Path, typer.Option(help="Direct HWPX output directory")],
) -> None:
    _validate_document_scenario(scenario)
    result = fill_templates(
        DirectFillRequest(
            scenario=scenario,
            weekly_template=weekly_template,
            final_template=final_template,
            weekly_data=weekly_data,
            final_draft=final_draft,
            monthly_draft=monthly_draft,
            evidence=evidence,
            out_dir=out,
        )
    )
    typer.echo(f"direct fill status: {result.status}")
    typer.echo(f"wrote direct fill validation to {result.validation}")


@document_app.command("export")
def export_hwpx_command(
    scenario: Annotated[str, typer.Option(help="480 or 640")],
    weekly: Annotated[Path, typer.Option(help="Weekly report CSV")],
    final_draft: Annotated[Path, typer.Option(help="Final report draft markdown")],
    monthly_draft: Annotated[Path, typer.Option(help="Monthly draft markdown")],
    evidence: Annotated[Path, typer.Option(help="Evidence ledger CSV")],
    template_weekly: Annotated[Path, typer.Option(help="Weekly HWP template")],
    template_final: Annotated[Path, typer.Option(help="Final HWP template")],
    out: Annotated[Path, typer.Option(help="HWPX output directory")],
) -> None:
    _validate_document_scenario(scenario)
    result = export_hwpx(
        ExportHwpxRequest(
            scenario=scenario,
            weekly=weekly,
            final_draft=final_draft,
            monthly_draft=monthly_draft,
            evidence=evidence,
            template_weekly=template_weekly,
            template_final=template_final,
            out=out,
        )
    )
    typer.echo(f"wrote weekly source to {result.paths.weekly_source}")
    typer.echo(f"wrote final source to {result.paths.final_source}")
    typer.echo(f"wrote export validation to {result.paths.validation}")


@document_app.command("blank")
def blank_command(
    source: Annotated[Path, typer.Option("--input", help="Filled HWPX source")],
    out: Annotated[Path, typer.Option(help="Blank HWPX output")],
    keep: Annotated[Path, typer.Option(help="JSON keep/transform whitelist")],
    blank_images_over: Annotated[
        int,
        typer.Option(help="Replace embedded images larger than this many bytes"),
    ] = 0,
) -> None:
    _run_tool(
        [
            sys.executable,
            str(_skill_script("blank_form.py")),
            str(source),
            str(out),
            "--keep",
            str(keep),
            "--blank-images-over",
            str(blank_images_over),
        ]
    )


@document_app.command("render")
def render_command(
    source: Annotated[Path, typer.Option("--input", help="HWP/HWPX source")],
    out: Annotated[Path, typer.Option(help="Rendered SVG output")],
    page: Annotated[int, typer.Option(help="Zero-based page index")] = 0,
    node: Annotated[str, typer.Option(help="Node.js executable")] = "node",
) -> None:
    node_path = shutil.which(node)
    if node_path is None:
        msg = f"Node.js executable not found: {node}"
        raise typer.BadParameter(msg)
    _run_tool(
        [
            node_path,
            str(_skill_script("hwp_render.mjs")),
            str(source),
            str(page),
            str(out),
        ]
    )


@document_app.command("clean-pdf")
def clean_pdf_command(
    source: Annotated[Path, typer.Option("--input", help="PDF file or directory")],
    out_dir: Annotated[Path, typer.Option(help="Output directory")],
    min_x_frac: Annotated[
        float,
        typer.Option(help="Minimum x-position fraction for flattened memo boxes"),
    ] = 0.72,
    pad: Annotated[float, typer.Option(help="Redaction padding")] = 5.0,
) -> None:
    _run_tool(
        [
            sys.executable,
            str(_skill_script("pdf_remove_memos.py")),
            str(source),
            str(out_dir),
            "--min-x-frac",
            str(min_x_frac),
            "--pad",
            str(pad),
        ]
    )


def _validate_document_scenario(scenario: str) -> None:
    match scenario:
        case "480" | "640":
            return
        case _:
            msg = "--scenario must be 480 or 640"
            raise typer.BadParameter(msg)


def _skill_script(name: str) -> Path:
    path = Path(__file__).resolve().parents[3] / "scripts" / name
    if path.exists():
        return path
    msg = f"skill script not found: {path}"
    raise typer.BadParameter(msg)


def _run_tool(args: list[str]) -> None:
    result = subprocess.run(  # noqa: S603 - fixed local tool invocation
        args,
        capture_output=True,
        text=True,
        check=False,
    )
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    if stdout:
        typer.echo(stdout)
    if result.returncode == 0:
        return
    if stderr:
        typer.echo(stderr, err=True)
    raise typer.Exit(result.returncode)
