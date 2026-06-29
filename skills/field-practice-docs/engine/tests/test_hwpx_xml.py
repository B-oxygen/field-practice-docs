from __future__ import annotations

import zipfile
from pathlib import Path

from field_practice.hwpx_xml import (
    clone_week_rows,
    fill_weekly_table,
    inspect_hwpx,
    read_hwpx,
    replace_text,
    write_hwpx,
)
from field_practice.template_cell_fill import CellFill, fill_table_cells


def test_hwpx_xml_when_unzip_and_rezip_then_preserves_entries(tmp_path: Path) -> None:
    source = _sample_hwpx(tmp_path)

    package = read_hwpx(source)
    target = tmp_path / "roundtrip.hwpx"
    write_hwpx(package, target)

    with zipfile.ZipFile(target) as archive:
        first = archive.infolist()[0]
        section = archive.read("Contents/section0.xml").decode("utf-8")
        assert "Contents/section0.xml" in archive.namelist()
        assert "mimetype" in archive.namelist()
        assert first.filename == "mimetype"
        assert first.compress_type == zipfile.ZIP_STORED
        assert "<ns0:" not in section


def test_hwpx_xml_when_replacing_text_then_preserves_non_text_xml(
    tmp_path: Path,
) -> None:
    source = _sample_hwpx(tmp_path)
    package = read_hwpx(source)

    updated = replace_text(package, {"000000001": "0000000000"})

    section = updated.text("Contents/section0.xml")
    assert "0000000000" in section
    assert 'borderFillIDRef="7"' in section


def test_hwpx_xml_detects_weekly_table_headers(tmp_path: Path) -> None:
    inspection = inspect_hwpx(_sample_hwpx(tmp_path))

    assert inspection.tables[0].kind == "weekly_activity"
    assert inspection.tables[0].header_row_index == 0


def test_hwpx_xml_can_clone_week_rows(tmp_path: Path) -> None:
    package = read_hwpx(_sample_hwpx(tmp_path))

    updated = clone_week_rows(package, 16)

    assert "26/6/15" in updated.text("Contents/section0.xml")
    assert "26/6/15" in updated.text("Preview/PrvText.txt")
    assert "16" in updated.text("Contents/section0.xml")


def test_hwpx_xml_overwrites_stale_weekly_body_rows(tmp_path: Path) -> None:
    package = read_hwpx(_sample_hwpx(tmp_path, include_blank_activity_row=True))
    rows = {
        "26/3/6": ("1", "26/3/6", "금", "600", "요구사항 정리"),
        "26/3/7": ("1", "26/3/7", "토", "600", "로그인 화면 구현"),
    }

    updated, _mappings = fill_weekly_table(package, rows)

    section = updated.text("Contents/section0.xml")
    preview = updated.text("Preview/PrvText.txt")
    assert "어플리케이션 개발(600min)" not in section
    assert "어플리케이션 개발(600min)" not in preview
    assert "요구사항 정리" in section
    assert "요구사항 정리" in preview
    assert "로그인 화면 구현" in section
    assert "로그인 화면 구현" in preview
    assert 'charPrIDRef="17"' not in section


def test_hwpx_xml_fills_empty_activity_cell_without_text_node(tmp_path: Path) -> None:
    package = read_hwpx(_sample_hwpx(tmp_path, empty_first_activity_cell=True))
    rows = {
        "26/3/6": ("1", "26/3/6", "금", "600", "오리엔테이션 내용 정리"),
    }

    updated, _mappings = fill_weekly_table(package, rows)

    assert "오리엔테이션 내용 정리" in updated.text("Contents/section0.xml")
    assert "오리엔테이션 내용 정리" in updated.text("Preview/PrvText.txt")


def test_hwpx_xml_renumbers_cell_addresses_when_rows_are_appended(
    tmp_path: Path,
) -> None:
    package = read_hwpx(_sample_hwpx(tmp_path))
    rows = {
        "26/3/6": ("1", "26/3/6", "금", "600", "요구사항 정리"),
        "26/3/7": ("1", "26/3/7", "토", "600", "기능 검증"),
        "26/3/8": ("1", "26/3/8", "일", "-", ""),
    }

    updated, _mappings = fill_weekly_table(package, rows)

    section = updated.text("Contents/section0.xml")
    assert 'rowCnt="4"' in section
    assert 'rowAddr="1"' in section
    assert 'rowAddr="2"' in section
    assert 'rowAddr="3"' in section


def test_hwpx_xml_when_filling_weekly_table_then_preserves_section_prefix(
    tmp_path: Path,
) -> None:
    source = _sample_hwpx(tmp_path)
    with zipfile.ZipFile(source) as archive:
        original = archive.read("Contents/section0.xml")
    package = read_hwpx(source)

    updated, _mappings = fill_weekly_table(
        package,
        {"26/3/6": ("1", "26/3/6", "금", "600", "· 활동 정리")},
    )
    target = tmp_path / "filled.hwpx"
    write_hwpx(updated, target)

    with zipfile.ZipFile(target) as archive:
        filled = archive.read("Contents/section0.xml")
    marker = b"<hp:p"
    assert filled[: filled.find(marker)] == original[: original.find(marker)]


def test_template_cell_fill_sets_addressed_empty_cell_and_style(
    tmp_path: Path,
) -> None:
    package = read_hwpx(_sample_hwpx(tmp_path, empty_first_activity_cell=True))

    updated = fill_table_cells(
        package,
        (
            CellFill(
                section_path="Contents/section0.xml",
                table_index=0,
                row_index=1,
                cell_index=4,
                text="사업 아이템 검증 인터뷰 정리",
                char_pr_id="12",
            ),
        ),
    )

    section = updated.text("Contents/section0.xml")
    assert "사업 아이템 검증 인터뷰 정리" in section
    assert "사업 아이템 검증 인터뷰 정리" in updated.text("Preview/PrvText.txt")
    assert 'charPrIDRef="12"' in section
    assert 'charPrIDRef="17"' not in section


def _sample_hwpx(
    tmp_path: Path,
    *,
    include_blank_activity_row: bool = False,
    empty_first_activity_cell: bool = False,
) -> Path:
    path = tmp_path / "sample.hwpx"
    first_activity_cell = (
        '<hp:tc><hp:p><hp:run /></hp:p><hp:cellAddr colAddr="4" rowAddr="1" /></hp:tc>'
        if empty_first_activity_cell
        else '<hp:tc><hp:p><hp:run charPrIDRef="17"><hp:t>'
        "어플리케이션 개발(600min)</hp:t></hp:run></hp:p>"
        '<hp:cellAddr colAddr="4" rowAddr="1" /></hp:tc>'
    )
    extra_row = (
        "<hp:tr>"
        '<hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p><hp:cellAddr colAddr="1" rowAddr="2" /></hp:tc>'
        '<hp:tc><hp:p><hp:run><hp:t>토</hp:t></hp:run></hp:p><hp:cellAddr colAddr="2" rowAddr="2" /></hp:tc>'
        '<hp:tc><hp:p><hp:run><hp:t>600</hp:t></hp:run></hp:p><hp:cellAddr colAddr="3" rowAddr="2" /></hp:tc>'
        '<hp:tc><hp:p><hp:run charPrIDRef="17"><hp:t>'
        "어플리케이션 개발(600min)</hp:t></hp:run></hp:p>"
        '<hp:cellAddr colAddr="4" rowAddr="2" /></hp:tc>'
        "</hp:tr>"
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<hp:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">'
        "<hp:p><hp:run><hp:t>예시대학 예시학과 / 000000001 / 홍길동 / "
        "주식회사 예시컴퍼니</hp:t></hp:run></hp:p>"
        '<hp:tbl borderFillIDRef="7" rowCnt="2"><hp:tr>'
        "<hp:tc><hp:p><hp:run><hp:t>주차</hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t>날짜</hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t>요일</hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t>근무시간(분)</hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t>활동내역</hp:t></hp:run></hp:p></hp:tc>"
        "</hp:tr><hp:tr>"
        '<hp:tc><hp:p><hp:run><hp:t>1</hp:t></hp:run></hp:p><hp:cellAddr colAddr="0" rowAddr="1" /></hp:tc>'
        '<hp:tc><hp:p><hp:run><hp:t>26//3/6</hp:t></hp:run></hp:p><hp:cellAddr colAddr="1" rowAddr="1" /></hp:tc>'
        '<hp:tc><hp:p><hp:run><hp:t>금</hp:t></hp:run></hp:p><hp:cellAddr colAddr="2" rowAddr="1" /></hp:tc>'
        '<hp:tc><hp:p><hp:run><hp:t>600</hp:t></hp:run></hp:p><hp:cellAddr colAddr="3" rowAddr="1" /></hp:tc>'
        f"{first_activity_cell}"
        "</hp:tr>"
        f"{extra_row if include_blank_activity_row else ''}"
        "</hp:tbl></hp:sec>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "mimetype",
            "application/hwp+zip",
            compress_type=zipfile.ZIP_STORED,
        )
        archive.writestr("Contents/section0.xml", xml)
        archive.writestr(
            "Preview/PrvText.txt",
            "<주차><날짜><요일><근무시간 (분)><활동내역>\r\n"
            "<1><26//3/6><금><600><어플리케이션 개발(600min)>",
        )
    return path
