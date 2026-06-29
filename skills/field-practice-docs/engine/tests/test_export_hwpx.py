from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from field_practice.export_hwpx import ExportHwpxRequest, export_hwpx


def test_markdown_to_hwpx_script_exists() -> None:
    assert Path("scripts/markdown_to_hwpx.mjs").exists()


def test_export_hwpx_creates_sources_and_graceful_validation(
    tmp_path: Path,
) -> None:
    request = _request(tmp_path, node_command="missing-node-command")

    result = export_hwpx(request)

    assert result.paths.weekly_source.exists()
    assert result.paths.final_source.exists()
    assert result.paths.validation.exists()
    validation = result.paths.validation.read_text(encoding="utf-8")
    assert "Node.js를 찾을 수 없습니다" in validation
    assert "0000000000" in result.paths.final_source.read_text(encoding="utf-8")


def test_export_hwpx_when_kordoc_available_creates_non_empty_hwpx(
    tmp_path: Path,
) -> None:
    if shutil.which("node") is None:
        return
    probe = subprocess.run(
        ["node", "-e", "import('kordoc').then(()=>{}).catch(()=>process.exit(2))"],
        check=False,
    )
    if probe.returncode != 0:
        return

    result = export_hwpx(_request(tmp_path))

    assert result.paths.weekly_hwpx.exists()
    assert result.paths.weekly_hwpx.stat().st_size > 0
    assert result.paths.final_hwpx.exists()
    assert result.paths.final_hwpx.stat().st_size > 0


def _request(tmp_path: Path, node_command: str = "node") -> ExportHwpxRequest:
    weekly = tmp_path / "weekly_report_640.csv"
    weekly.write_text(
        "\ufeffweek,student_id,date,weekday_ko,minutes,activity,evidence_ids,confidence,scenario,needs_review\n"
        "16,0000000000,26/6/16,화,120,결과보고서 작성을 위해 최종 활동을 정리하여 보고서 초안을 작성함.,GH-1,A,640,false\n",
        encoding="utf-8",
    )
    (tmp_path / "validation_report.md").write_text(
        "# 검증 보고서\n\n"
        "## 640시간 시나리오\n"
        "- 합계: 37734분\n"
        "- 목표: 38400분\n"
        "- 부족분: 666분\n",
        encoding="utf-8",
    )
    final_draft = tmp_path / "final.md"
    monthly_draft = tmp_path / "monthly.md"
    evidence = tmp_path / "evidence.csv"
    template_weekly = tmp_path / "weekly.hwp"
    template_final = tmp_path / "final.hwp"
    final_draft.write_text("# final\n", encoding="utf-8")
    monthly_draft.write_text("# monthly\n", encoding="utf-8")
    evidence.write_text("evidence_id\nGH-1\n", encoding="utf-8")
    template_weekly.write_text("weekly template\n", encoding="utf-8")
    template_final.write_text("final template\n", encoding="utf-8")
    return ExportHwpxRequest(
        scenario="640",
        weekly=weekly,
        final_draft=final_draft,
        monthly_draft=monthly_draft,
        evidence=evidence,
        template_weekly=template_weekly,
        template_final=template_final,
        out=tmp_path / "hwpx",
        node_command=node_command,
    )
