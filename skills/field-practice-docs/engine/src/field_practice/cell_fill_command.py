from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, TypeAlias

import typer

from field_practice.hwpx_xml import read_hwpx, write_hwpx
from field_practice.template_cell_fill import CellFill, fill_table_cells

JsonCellRecord: TypeAlias = dict[str, str | int | None]


def register_cell_fill_command(app: typer.Typer) -> None:
    app.command("fill-cells")(fill_cells_command)


def fill_cells_command(
    template: Annotated[Path, typer.Option(help="Source HWPX template")],
    cells: Annotated[Path, typer.Option(help="JSON array of table cell fills")],
    out: Annotated[Path, typer.Option(help="Filled HWPX output")],
) -> None:
    fills = _read_cell_fills(cells)
    write_hwpx(fill_table_cells(read_hwpx(template), fills), out)
    typer.echo(f"filled {len(fills)} cell(s) into {out}")


def _read_cell_fills(path: Path) -> tuple[CellFill, ...]:
    data: JsonCellRecord | list[JsonCellRecord] = json.loads(
        path.read_text(encoding="utf-8")
    )
    if not isinstance(data, list):
        msg = "--cells must be a JSON array"
        raise typer.BadParameter(msg)
    return tuple(_parse_cell_fill(item) for item in data)


def _parse_cell_fill(item: JsonCellRecord) -> CellFill:
    return CellFill(
        section_path=_required_str(item, "section_path"),
        table_index=_required_int(item, "table_index"),
        row_index=_required_int(item, "row_index"),
        cell_index=_required_int(item, "cell_index"),
        text=_required_str(item, "text"),
        char_pr_id=_optional_str(item, "char_pr_id"),
    )


def _required_str(item: JsonCellRecord, key: str) -> str:
    value = item.get(key)
    if isinstance(value, str):
        return value
    msg = f"{key} must be a string"
    raise typer.BadParameter(msg)


def _optional_str(item: JsonCellRecord, key: str) -> str | None:
    value = item.get(key)
    if value is None or isinstance(value, str):
        return value
    msg = f"{key} must be a string or null"
    raise typer.BadParameter(msg)


def _required_int(item: JsonCellRecord, key: str) -> int:
    value = item.get(key)
    if isinstance(value, int):
        return value
    msg = f"{key} must be an integer"
    raise typer.BadParameter(msg)
