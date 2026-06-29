from __future__ import annotations

from pathlib import Path

from field_practice.validate import validate_weekly_csv


def test_validate_weekly_csv_when_student_id_typo_exists_then_reports_error(
    tmp_path: Path,
) -> None:
    weekly = tmp_path / "weekly.csv"
    weekly.write_text(
        "\ufeffweek,date,weekday_ko,minutes,activity,evidence_ids,confidence,scenario,needs_review\n"
        "16,26/6/16,화,60,000000001 typo,E1,A,480,false\n",
        encoding="utf-8",
    )
    issues = validate_weekly_csv(weekly)
    assert any("000000001" in issue.message for issue in issues)


def test_validate_weekly_csv_when_week_16_missing_then_reports_error(
    tmp_path: Path,
) -> None:
    weekly = tmp_path / "weekly.csv"
    weekly.write_text(
        "\ufeffweek,date,weekday_ko,minutes,activity,evidence_ids,confidence,scenario,needs_review\n"
        "1,26/3/6,금,60,activity,E1,A,480,false\n",
        encoding="utf-8",
    )
    issues = validate_weekly_csv(weekly)
    assert any("16주차" in issue.message for issue in issues)


def test_validate_weekly_csv_when_date_format_invalid_then_reports_error(
    tmp_path: Path,
) -> None:
    weekly = tmp_path / "weekly.csv"
    weekly.write_text(
        "\ufeffweek,date,weekday_ko,minutes,activity,evidence_ids,confidence,scenario,needs_review\n"
        "16,26//3/6,금,60,activity,E1,A,480,false\n",
        encoding="utf-8",
    )
    issues = validate_weekly_csv(weekly)
    assert any("날짜 형식 오류" in issue.message for issue in issues)
