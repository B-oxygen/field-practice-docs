from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CellMap:
    week: int
    date: int
    weekday: int
    minutes: int
    activity: int


@dataclass(frozen=True, slots=True)
class TableMap:
    table_id: str
    kind: str
    section_path: str
    table_index: int
    header_row_index: int
    cell_map: CellMap
    row_count: int


@dataclass(frozen=True, slots=True)
class TemplateInspection:
    path: Path
    status: str
    tables: tuple[TableMap, ...]
    text_node_count: int
    notes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OutputPaths:
    weekly: Path
    final: Path
    validation: Path
    weekly_mapping: Path
    final_mapping: Path


def direct_output_paths(out_dir: Path, scenario: str) -> OutputPaths:
    return OutputPaths(
        weekly=out_dir
        / f"[홍길동] 2026-1학기 창업현장실습_주차별활동보고서_{scenario}_template_filled.hwpx",
        final=out_dir
        / f"[홍길동] 2026-1학기 창업현장실습_결과보고서_{scenario}_template_filled.hwpx",
        validation=out_dir / "direct_fill_validation.md",
        weekly_mapping=out_dir / "weekly_cell_mapping.csv",
        final_mapping=out_dir / "final_cell_mapping.csv",
    )
