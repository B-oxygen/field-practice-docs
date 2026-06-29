from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from field_practice.hwp_markdown import (
    HwpxOutputPaths,
    read_weekly_rows,
    render_final_source_markdown,
    render_weekly_source_from_rows,
)
from field_practice.hwp_validation import (
    render_hwp_export_validation,
    summarize_weekly_validation,
)
from field_practice.writers import ensure_parent, write_markdown


@dataclass(frozen=True, slots=True)
class ExportHwpxRequest:
    scenario: str
    weekly: Path
    final_draft: Path
    monthly_draft: Path
    evidence: Path
    template_weekly: Path
    template_final: Path
    out: Path
    node_command: str = "node"


@dataclass(frozen=True, slots=True)
class ExportHwpxResult:
    paths: HwpxOutputPaths
    conversion_notes: tuple[str, ...]


def export_hwpx(request: ExportHwpxRequest) -> ExportHwpxResult:
    paths = _output_paths(request.out, request.scenario)
    rows = read_weekly_rows(request.weekly, request.scenario)
    weekly_source = render_weekly_source_from_rows(rows)
    final_source = render_final_source_markdown(
        request.final_draft,
        request.monthly_draft,
        rows,
        request.scenario,
    )
    write_markdown(paths.weekly_source, weekly_source)
    write_markdown(paths.final_source, final_source)
    notes = _convert_sources(request, paths)
    summary = summarize_weekly_validation(
        rows,
        request.scenario,
        request.weekly.parent / "validation_report.md",
    )
    validation = render_hwp_export_validation(
        paths,
        request.scenario,
        summary,
        weekly_source,
        final_source,
        notes,
    )
    write_markdown(paths.validation, validation)
    return ExportHwpxResult(paths=paths, conversion_notes=notes)


def _output_paths(out_dir: Path, scenario: str) -> HwpxOutputPaths:
    return HwpxOutputPaths(
        weekly_source=out_dir / f"weekly_activity_report_{scenario}_source.md",
        final_source=out_dir / f"final_result_report_{scenario}_source.md",
        weekly_hwpx=out_dir
        / f"[홍길동] 2026-1학기 창업현장실습_주차별활동보고서_{scenario}.hwpx",
        final_hwpx=out_dir
        / f"[홍길동] 2026-1학기 창업현장실습_결과보고서_{scenario}.hwpx",
        validation=out_dir / "hwp_export_validation.md",
    )


def _convert_sources(
    request: ExportHwpxRequest,
    paths: HwpxOutputPaths,
) -> tuple[str, ...]:
    node_path = shutil.which(request.node_command)
    if node_path is None:
        return (
            "HWPX 변환 생략: Node.js를 찾을 수 없습니다. "
            "Node.js 설치 후 `npm install kordoc`를 실행하세요.",
        )
    script = Path("scripts/markdown_to_hwpx.mjs")
    if not script.exists():
        return (f"HWPX 변환 생략: 변환 스크립트를 찾을 수 없습니다: {script}",)
    notes = [
        _convert_one(node_path, script, paths.weekly_source, paths.weekly_hwpx),
        _convert_one(node_path, script, paths.final_source, paths.final_hwpx),
    ]
    return tuple(notes)


def _convert_one(
    node_path: str,
    script: Path,
    source: Path,
    target: Path,
) -> str:
    ensure_parent(target)
    result = subprocess.run(
        [node_path, str(script), str(source), str(target)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0 and target.exists() and target.stat().st_size > 0:
        return f"HWPX 변환 완료: {target}"
    detail = result.stderr.strip() or result.stdout.strip() or "원인 미상"
    return f"HWPX 변환 실패: {source} -> {target}; {detail}"
