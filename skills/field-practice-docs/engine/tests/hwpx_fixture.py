from __future__ import annotations

import zipfile
from pathlib import Path


def write_weekly_hwpx_fixture(path: Path) -> None:
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<hp:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">'
        "<hp:p><hp:run><hp:t>예시대학 예시학과 / 000000001 / 홍길동 / "
        "주식회사 예시컴퍼니</hp:t></hp:run></hp:p>"
        '<hp:tbl borderFillIDRef="7"><hp:tr>'
        "<hp:tc><hp:p><hp:run><hp:t>주차</hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t>날짜</hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t>요일</hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t>근무시간(분)</hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t>활동내역</hp:t></hp:run></hp:p></hp:tc>"
        "</hp:tr><hp:tr>"
        "<hp:tc><hp:p><hp:run><hp:t>1</hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t>26//3/6</hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t>금</hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t>600</hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t>어플리케이션 개발(600min)</hp:t></hp:run></hp:p></hp:tc>"
        "</hp:tr></hp:tbl></hp:sec>"
    )
    _write_hwpx(path, xml)


def write_final_hwpx_fixture(path: Path) -> None:
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<hp:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">'
        "<hp:tbl><hp:tr>"
        "<hp:tc><hp:p><hp:run><hp:t>성명</hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t>홍길동</hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t>학번</hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t>0000000000</hp:t></hp:run></hp:p></hp:tc>"
        "</hp:tr><hp:tr>"
        "<hp:tc><hp:p><hp:run><hp:t>대상학기</hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t>2026년도 1학기</hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t>신청학점</hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t>12학점(주전공)</hp:t></hp:run></hp:p></hp:tc>"
        "</hp:tr></hp:tbl>"
        "<hp:tbl><hp:tr>"
        "<hp:tc><hp:p><hp:run><hp:t>인원현황</hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t>성명</hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t>직책</hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t>주요업무</hp:t></hp:run></hp:p></hp:tc>"
        "</hp:tr><hp:tr>"
        "<hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>"
        "</hp:tr></hp:tbl>"
        "<hp:tbl><hp:tr>"
        "<hp:tc><hp:p><hp:run><hp:t>창업아이템</hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t>전공학점 신청학과명</hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>"
        "</hp:tr><hp:tr><hp:tc><hp:p><hp:run><hp:t>창업아이템의 전공 연계성 보고</hp:t></hp:run></hp:p></hp:tc>"
        "</hp:tr><hp:tr><hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc></hp:tr></hp:tbl>"
        "<hp:tbl><hp:tr><hp:tc><hp:p><hp:run><hp:t>(  3  )월</hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc></hp:tr></hp:tbl>"
        "<hp:tbl><hp:tr><hp:tc><hp:p><hp:run><hp:t>창업현장실습결과</hp:t></hp:run></hp:p></hp:tc>"
        "<hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc></hp:tr></hp:tbl>"
        "</hp:sec>"
    )
    _write_hwpx(path, xml)


def _write_hwpx(path: Path, section_xml: str) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", "application/hwp+zip")
        archive.writestr("Contents/section0.xml", section_xml)
