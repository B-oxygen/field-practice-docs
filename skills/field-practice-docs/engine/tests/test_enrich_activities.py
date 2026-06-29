from __future__ import annotations

from pathlib import Path

from field_practice.enrich_activities import EnrichmentInputs, enrich_weekly_reports


def test_enrich_weekly_when_red_activity_then_rewrites_and_preserves_evidence(
    tmp_path: Path,
) -> None:
    inputs = _write_fixture(tmp_path, weekly_activity="어플리케이션 개발(600min)")

    result = enrich_weekly_reports(inputs)

    row = next(
        item for item in result.rows if item.week == 10 and item.date_text == "26/5/4"
    )
    assert "600min" not in row.activity
    assert "정리" in row.activity or "반영" in row.activity
    assert "GH-10" in row.evidence_ids
    assert len(result.rewrite_logs) >= 1


def test_enrich_weekly_when_full_week_has_alog_then_gets_detailed_activity(
    tmp_path: Path,
) -> None:
    inputs = _write_fixture(tmp_path, weekly_activity="QA")

    result = enrich_weekly_reports(inputs)

    rows = [item for item in result.rows if item.week == 10 and item.minutes > 0]
    assert sum(item.minutes for item in rows) == 3120
    assert all(len(item.activity) >= 45 for item in rows)
    assert all(
        "체크리스트" in item.activity or "반영" in item.activity for item in rows
    )


def test_enrich_weekly_keeps_weeks_1_to_16_present(tmp_path: Path) -> None:
    inputs = _write_fixture(tmp_path, weekly_activity="QA")

    result = enrich_weekly_reports(inputs)

    assert {item.week for item in result.rows} == set(range(1, 17))
    assert len(result.rows) == 112


def _write_fixture(tmp_path: Path, weekly_activity: str) -> EnrichmentInputs:
    weekly = tmp_path / "weekly.csv"
    weekly.write_text(
        "\ufeffweek,student_id,date,weekday_ko,minutes,activity,evidence_ids,confidence,scenario,needs_review\n"
        f"10,0000000000,26/5/4,월,600,{weekly_activity},GH-10,A_candidate,640,false\n",
        encoding="utf-8",
    )
    evidence = tmp_path / "evidence.csv"
    evidence.write_text(
        "\ufeffevidence_id,source_type,source_ref,repo,date,week,title,description,workstream,confidence,sensitive,report_phrase\n"
        "GH-10,github_commit_local,abc,repo,2026-05-04,10,feat dashboard,관리자 dashboard api 개발,B,A_candidate,false,old\n"
        "GH-11,github_commit_local,def,repo,2026-05-05,10,test qa,QA spec 정리,C,A_candidate,false,old\n"
        "GH-12,github_commit_local,ghi,repo,2026-05-06,10,fix api,API 오류 수정,C,A_candidate,false,old\n"
        "GH-13,github_commit_local,jkl,repo,2026-05-07,10,feat app,앱 기능 구현,B,A_candidate,false,old\n"
        "GH-14,github_commit_local,mno,repo,2026-05-08,10,docs qa,QA 문서 정리,G,A_candidate,false,old\n"
        "GH-15,github_commit_local,pqr,repo,2026-05-09,10,ops check,운영 점검,E,A_candidate,false,old\n"
        "GH-16,github_commit_local,stu,repo,2026-05-10,10,release check,배포 전 검증,C,A_candidate,false,old\n"
        "CAL-1,calendar,cal,calendar,2026-03-02,1,오리엔테이션,창업현장실습 운영 교육,G,C,false,old\n",
        encoding="utf-8",
    )
    alog_weekly = tmp_path / "alog_weekly.csv"
    alog_weekly.write_text(
        "week,start_date,end_date,capped_minutes_week,capped_hhmm,remaining_to_52h_minutes,source_note\n"
        "1,2026-03-02,2026-03-08,0,00:00,3120,week 1 existing report 1,500분 is separate scenario\n"
        "10,2026-05-04,2026-05-10,3120,52:00,0,week cap reached\n",
        encoding="utf-8",
    )
    time_ledger = tmp_path / "time.csv"
    time_ledger.write_text(
        "\ufeffdate,week,raw_minutes,proposed_minutes,capped_day_minutes,capped_week_minutes,scenario,evidence_ids,needs_review,reason\n",
        encoding="utf-8",
    )
    calendar = tmp_path / "calendar.csv"
    calendar.write_text(
        "date,week,start_time,end_time,duration_minutes,summary,category,workstream,report_usage,source_note\n",
        encoding="utf-8",
    )
    return EnrichmentInputs(
        scenario="640",
        weekly=weekly,
        time_ledger=time_ledger,
        evidence=evidence,
        calendar=calendar,
        alog_weekly=alog_weekly,
        out_dir=tmp_path / "out",
    )
