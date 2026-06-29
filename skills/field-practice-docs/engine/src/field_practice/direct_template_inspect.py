from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from field_practice.hwpx_xml import inspect_hwpx
from field_practice.rhwp_backend import rhwp_status
from field_practice.writers import write_markdown


@dataclass(frozen=True, slots=True)
class TemplateInspectRequest:
    weekly_template: Path
    final_template: Path
    out_dir: Path


@dataclass(frozen=True, slots=True)
class TemplateInspectResult:
    weekly_map: Path
    final_map: Path
    markdown: Path
    status: str


def inspect_templates(request: TemplateInspectRequest) -> TemplateInspectResult:
    request.out_dir.mkdir(parents=True, exist_ok=True)
    weekly_map = request.out_dir / "weekly_template_map.json"
    final_map = request.out_dir / "final_template_map.json"
    markdown = request.out_dir / "template_inspection.md"
    weekly_status = _write_inspection(request.weekly_template, weekly_map)
    final_status = _write_inspection(request.final_template, final_map)
    backend = rhwp_status()
    status = (
        "ok"
        if weekly_status == "ok" and final_status in {"ok", "no_weekly_table"}
        else "template_hwpx_required"
    )
    write_markdown(
        markdown,
        "\n".join(
            [
                "# 템플릿 검사 결과",
                "",
                f"- weekly template: {request.weekly_template}",
                f"- weekly status: {weekly_status}",
                f"- final template: {request.final_template}",
                f"- final status: {final_status}",
                f"- rhwp: {backend.note}",
                f"- status: {status}",
                "",
            ]
        ),
    )
    return TemplateInspectResult(
        weekly_map=weekly_map,
        final_map=final_map,
        markdown=markdown,
        status=status,
    )


def _write_inspection(template: Path, output: Path) -> str:
    if template.suffix.lower() != ".hwpx":
        output.write_text(
            json.dumps({"status": "template_hwpx_required"}, ensure_ascii=False),
            encoding="utf-8",
        )
        return "template_hwpx_required"
    inspection = inspect_hwpx(template)
    output.write_text(
        json.dumps(
            {
                "status": inspection.status,
                "text_node_count": inspection.text_node_count,
                "tables": [
                    {
                        "table_id": table.table_id,
                        "kind": table.kind,
                        "section_path": table.section_path,
                        "header_row_index": table.header_row_index,
                        "row_count": table.row_count,
                    }
                    for table in inspection.tables
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return inspection.status
