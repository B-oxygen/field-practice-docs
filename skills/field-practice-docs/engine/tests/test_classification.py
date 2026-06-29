from __future__ import annotations

from field_practice.classify import classify_text
from field_practice.models import Workstream


def test_classify_text_when_fix_login_bug_then_returns_qa() -> None:
    assert classify_text("fix login bug") == Workstream.C


def test_classify_text_when_admin_dashboard_api_then_returns_build() -> None:
    assert classify_text("admin dashboard API") == Workstream.B


def test_classify_text_when_mit_cooperation_document_then_returns_external() -> None:
    assert classify_text("MIT cooperation document") == Workstream.D


def test_classify_text_when_final_report_then_returns_reporting() -> None:
    assert classify_text("final report") == Workstream.G
