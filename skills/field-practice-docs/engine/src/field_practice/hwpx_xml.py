from __future__ import annotations

import copy
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree.ElementTree import Element, register_namespace, tostring

from defusedxml import ElementTree

from field_practice.template_document import CellMap, TableMap, TemplateInspection
from field_practice.weeks import dates_in_week, report_date, weekday_ko

WEEKLY_ACTIVITY_CHAR_PR_ID = "12"
WEEKLY_BODY_CHAR_PR_ID = "12"
HWPX_NAMESPACES = {
    "ha": "http://www.hancom.co.kr/hwpml/2011/app",
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hp10": "http://www.hancom.co.kr/hwpml/2016/paragraph",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
    "hhs": "http://www.hancom.co.kr/hwpml/2011/history",
    "hm": "http://www.hancom.co.kr/hwpml/2011/master-page",
    "hpf": "http://www.hancom.co.kr/schema/2011/hpf",
    "dc": "http://purl.org/dc/elements/1.1/",
    "opf": "http://www.idpf.org/2007/opf/",
    "ooxmlchart": "http://www.hancom.co.kr/hwpml/2016/ooxmlchart",
    "hwpunitchar": "http://www.hancom.co.kr/hwpml/2016/HwpUnitChar",
    "epub": "http://www.idpf.org/2007/ops",
    "config": "urn:oasis:names:tc:opendocument:xmlns:config:1.0",
    "odf": "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0",
    "hv": "http://www.hancom.co.kr/hwpml/2011/version",
}

for _prefix, _uri in HWPX_NAMESPACES.items():
    register_namespace(_prefix, _uri)


@dataclass(frozen=True, slots=True)
class HwpxPackage:
    entries: dict[str, bytes]
    compression_types: dict[str, int] = field(default_factory=dict)

    def text(self, name: str) -> str:
        return self.entries[name].decode("utf-8")

    def combined_text(self) -> str:
        return "\n".join(
            value.decode("utf-8", errors="replace")
            for key, value in self.entries.items()
            if _is_text_entry(key)
        )


@dataclass(frozen=True, slots=True)
class WeeklyPackageDiagnostics:
    row_count_ok: bool
    red_activity_style_count: int
    activity_style_count: int
    forbidden_hits: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return (
            self.row_count_ok
            and self.red_activity_style_count == 0
            and len(self.forbidden_hits) == 0
        )


def read_hwpx(path: Path) -> HwpxPackage:
    with zipfile.ZipFile(path) as archive:
        return HwpxPackage(
            entries={name: archive.read(name) for name in archive.namelist()},
            compression_types={
                info.filename: info.compress_type for info in archive.infolist()
            },
        )


def write_hwpx(package: HwpxPackage, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in package.entries.items():
            archive.writestr(
                name,
                content,
                compress_type=package.compression_types.get(
                    name, _default_compression(name)
                ),
            )


def replace_text(package: HwpxPackage, replacements: dict[str, str]) -> HwpxPackage:
    entries = dict(package.entries)
    for name in _text_entry_names(entries):
        text = entries[name].decode("utf-8")
        for old, new in replacements.items():
            text = text.replace(old, new)
        entries[name] = text.encode("utf-8")
    return HwpxPackage(
        entries=_refresh_preview_text(entries),
        compression_types=package.compression_types,
    )


def inspect_hwpx(path: Path) -> TemplateInspection:
    package = read_hwpx(path)
    tables: list[TableMap] = []
    text_count = 0
    for section_path in _section_names(package):
        root = ElementTree.fromstring(package.entries[section_path])
        text_count += len(_text_nodes(root))
        for index, table in enumerate(_tables(root)):
            header = _weekly_header(table)
            if header is None:
                continue
            tables.append(
                TableMap(
                    table_id=f"table_{len(tables)}",
                    kind="weekly_activity",
                    section_path=section_path,
                    table_index=index,
                    header_row_index=header,
                    cell_map=CellMap(week=0, date=1, weekday=2, minutes=3, activity=4),
                    row_count=len(_rows(table)),
                )
            )
    status = "ok" if len(tables) > 0 else "no_weekly_table"
    return TemplateInspection(
        path=path,
        status=status,
        tables=tuple(tables),
        text_node_count=text_count,
        notes=(),
    )


def clone_week_rows(package: HwpxPackage, week: int) -> HwpxPackage:
    entries = dict(package.entries)
    for section_path in _section_names(package):
        root = ElementTree.fromstring(entries[section_path])
        for table in _tables(root):
            if _weekly_header(table) is None:
                continue
            prototype = _rows(table)[-1]
            for current in dates_in_week(week):
                cloned = copy.deepcopy(prototype)
                cells = _cells(cloned)
                if len(cells) >= 5:
                    _set_cell_text(cells[0], str(week))
                    _set_cell_text(cells[1], report_date(current))
                    _set_cell_text(cells[2], weekday_ko(current))
                    _set_cell_text(cells[3], "-")
                    _set_cell_text(cells[4], "")
                table.append(cloned)
            entries[section_path] = _xml_bytes(root, source=entries[section_path])
            return HwpxPackage(
                entries=_refresh_preview_text(entries),
                compression_types=package.compression_types,
            )
    return package


def fill_weekly_table(
    package: HwpxPackage,
    row_values: dict[str, tuple[str, str, str, str, str]],
) -> tuple[HwpxPackage, tuple[tuple[str, int, str], ...]]:
    package = replace_text(package, {"000000001": "0000000000", "26//3/6": "26/3/6"})
    entries = dict(package.entries)
    mappings: list[tuple[str, int, str]] = []
    for section_path in _section_names(package):
        root = ElementTree.fromstring(entries[section_path])
        for table in _tables(root):
            header_index = _weekly_header(table)
            if header_index is None:
                continue
            _ensure_week_rows(table, header_index, tuple(row_values.values()))
            _renumber_weekly_table_cells(table, header_index)
            table.set("rowCnt", str(len(_rows(table))))
            for (date_text, values), (row_index, row) in zip(
                row_values.items(),
                _weekly_body_rows(table, header_index),
                strict=False,
            ):
                _set_weekly_body_row(row, values)
                mappings.append((date_text, row_index, "filled"))
            entries[section_path] = _xml_bytes(root, source=entries[section_path])
            return (
                HwpxPackage(
                    entries=_refresh_preview_text(entries),
                    compression_types=package.compression_types,
                ),
                tuple(mappings),
            )
    return HwpxPackage(
        entries=entries, compression_types=package.compression_types
    ), tuple(mappings)


def fill_text_blocks(package: HwpxPackage, replacements: dict[str, str]) -> HwpxPackage:
    return replace_text(package, replacements)


def fill_final_report_tables(package: HwpxPackage) -> HwpxPackage:
    package = replace_text(package, {"000000001": "0000000000"})
    entries = dict(package.entries)
    for section_path in _section_names(package):
        root = ElementTree.fromstring(entries[section_path])
        for table in _tables(root):
            rows = _rows(table)
            _fill_final_staff_table(rows)
            _fill_final_item_table(rows)
            _fill_final_performance_table(rows)
            _fill_final_monthly_table(rows)
            _fill_final_result_table(rows)
        entries[section_path] = _xml_bytes(root, source=entries[section_path])
    return HwpxPackage(
        entries=_refresh_preview_text(entries),
        compression_types=package.compression_types,
    )


def diagnose_weekly_package(package: HwpxPackage) -> WeeklyPackageDiagnostics:
    text = package.combined_text()
    forbidden_hits = tuple(
        pattern
        for pattern in ("000000001", "26//", "(600min)", "어플리케이션 개발(600min)")
        if pattern in text
    )
    row_count_ok = True
    red_activity_style_count = 0
    activity_style_count = 0
    for section_path in _section_names(package):
        root = ElementTree.fromstring(package.entries[section_path])
        for table in _tables(root):
            header_index = _weekly_header(table)
            if header_index is None:
                continue
            expected_row_count = len(_rows(table))
            if table.get("rowCnt") != str(expected_row_count):
                row_count_ok = False
            for _, row in _weekly_body_rows(table, header_index):
                cells = _cells(row)
                if len(cells) < 4:
                    continue
                activity_cell = cells[4] if len(cells) >= 5 else cells[3]
                for item in activity_cell.iter():
                    if _local_name(item.tag) != "run":
                        continue
                    char_pr_id = item.get("charPrIDRef")
                    if char_pr_id == WEEKLY_ACTIVITY_CHAR_PR_ID:
                        activity_style_count += 1
                    if char_pr_id == "17":
                        red_activity_style_count += 1
    return WeeklyPackageDiagnostics(
        row_count_ok=row_count_ok,
        red_activity_style_count=red_activity_style_count,
        activity_style_count=activity_style_count,
        forbidden_hits=forbidden_hits,
    )


def _fill_final_staff_table(rows: tuple[Element, ...]) -> None:
    if not _table_has_text(rows, "인원현황"):
        return
    if len(rows) < 2:
        return
    cells = _cells(rows[1])
    if len(cells) >= 4:
        _set_cell_text(cells[0], "홍길동")
        _set_cell_text(cells[1], "CTO")
        _set_cell_text(cells[2], "서비스 기획·개발\nQA·사업화 자료 정리")
        _set_cell_text(cells[3], "")


def _fill_final_item_table(rows: tuple[Element, ...]) -> None:
    if not _table_has_text(rows, "전공학점 신청학과명"):
        return
    if len(rows) >= 1:
        cells = _cells(rows[0])
        if len(cells) >= 4:
            _set_cell_text(cells[1], "대학·기관 협업 기반 유학생 서비스 플랫폼")
            _set_cell_text(cells[3], "예시학과")
    if len(rows) >= 3:
        cells = _cells(rows[2])
        if len(cells) >= 1:
            _set_cell_text(
                cells[0],
                "경영학 전공에서 학습한 창업, 전략경영, 마케팅, 운영관리 지식을 "
                "고객 요구사항 분석과 서비스 사업화, 운영 지표 정리에 적용함.",
            )


def _fill_final_performance_table(rows: tuple[Element, ...]) -> None:
    if not _table_has_text(rows, "사업화 추진 단계"):
        return
    for row in rows:
        cells = _cells(row)
        if len(cells) < 2:
            continue
        label = _cell_text(cells[0])
        if label == "창업아이템":
            _set_cell_text(cells[1], "유학생 온보딩·운영 관리 서비스 플랫폼")
        elif label == "업종":
            _set_cell_text(cells[1], "정보서비스업 / SaaS")
        elif label == "매출실적":
            _set_cell_text(cells[1], "기관 고객 검증 및 파일럿 운영 준비")
        elif label == "사 업추진실적":
            _set_cell_text(cells[1], "앱·관리자 대시보드 기능 구현 및 QA 수행")
        elif label == "사업성과":
            _set_cell_text(cells[1], "운영 자료, 제안서, 최종 산출물 패키징 완료")


def _fill_final_monthly_table(rows: tuple[Element, ...]) -> None:
    monthly = {
        "(  3  )월": "오리엔테이션, 역할 정리, 초기 앱·대시보드 개발 착수",
        "(  4  )월": "고객 요구사항 정의, 프로토타입 개발, QA 및 오류 재현",
        "(  5  )월": "집중 개발 스프린트, 운영 테스트, 고객 피드백 반영",
        "(  6  )월": "최종 QA, 결과보고서 보완, 산출물 패키징 정리",
    }
    for row in rows:
        cells = _cells(row)
        if len(cells) < 2:
            continue
        month = _cell_text(cells[0])
        if month in monthly:
            _set_cell_text(cells[1], monthly[month])


def _fill_final_result_table(rows: tuple[Element, ...]) -> None:
    if len(rows) != 1:
        return
    cells = _cells(rows[0])
    if len(cells) < 2 or _cell_text(cells[0]) != "창업현장실습결과":
        return
    _set_cell_text(
        cells[1],
        "창업현장실습 기간 동안 제품 기획, 개발 구축, QA 검증, 외부 협력 자료 정리, "
        "사업화 운영 문서화를 통합 수행하며 예시컴퍼니 서비스의 실무 산출물을 정리함.",
    )


def _table_has_text(rows: tuple[Element, ...], expected: str) -> bool:
    return any(expected in _cell_text(cell) for row in rows for cell in _cells(row))


def _ensure_week_rows(
    table: Element,
    header_index: int,
    row_values: tuple[tuple[str, str, str, str, str], ...],
) -> None:
    body_rows = _weekly_body_rows(table, header_index)
    missing_values = row_values[len(body_rows) :]
    if len(missing_values) == 0:
        return
    for values in missing_values:
        cloned = copy.deepcopy(_row_prototype(body_rows, table, values))
        table.append(cloned)


def _weekly_body_rows(
    table: Element, header_index: int
) -> tuple[tuple[int, Element], ...]:
    return tuple(
        (row_index, row)
        for row_index, row in enumerate(_rows(table))
        if row_index > header_index and len(_cells(row)) >= 4
    )


def _row_prototype(
    body_rows: tuple[tuple[int, Element], ...],
    table: Element,
    values: tuple[str, str, str, str, str],
) -> Element:
    if values[2] == "월":
        for _, row in reversed(body_rows):
            if len(_cells(row)) >= 5:
                return row
    if len(body_rows) > 0:
        return body_rows[-1][1]
    return _rows(table)[-1]


def _renumber_weekly_table_cells(table: Element, header_index: int) -> None:
    for row_index, row in _weekly_body_rows(table, header_index):
        cells = _cells(row)
        start_col = 0 if len(cells) >= 5 else 1
        for offset, cell in enumerate(cells):
            for item in cell:
                if _local_name(item.tag) == "cellAddr":
                    item.set("rowAddr", str(row_index))
                    item.set("colAddr", str(start_col + offset))


def _set_weekly_body_row(
    row: Element,
    values: tuple[str, str, str, str, str],
) -> None:
    cells = _cells(row)
    if len(cells) >= 5:
        _set_cell_text(cells[0], values[0], char_pr_id=WEEKLY_BODY_CHAR_PR_ID)
        _set_cell_text(cells[1], values[1], char_pr_id=WEEKLY_BODY_CHAR_PR_ID)
        _set_cell_text(cells[2], values[2], char_pr_id=WEEKLY_BODY_CHAR_PR_ID)
        _set_cell_text(cells[3], values[3], char_pr_id=WEEKLY_BODY_CHAR_PR_ID)
        _set_cell_text(
            cells[4],
            values[4],
            char_pr_id=WEEKLY_ACTIVITY_CHAR_PR_ID,
        )
        return
    if len(cells) >= 4:
        _set_cell_text(cells[0], values[1], char_pr_id=WEEKLY_BODY_CHAR_PR_ID)
        _set_cell_text(cells[1], values[2], char_pr_id=WEEKLY_BODY_CHAR_PR_ID)
        _set_cell_text(cells[2], values[3], char_pr_id=WEEKLY_BODY_CHAR_PR_ID)
        _set_cell_text(
            cells[3],
            values[4],
            char_pr_id=WEEKLY_ACTIVITY_CHAR_PR_ID,
        )


def _weekly_header(table: Element) -> int | None:
    for index, row in enumerate(_rows(table)):
        texts = [_cell_text(cell) for cell in _cells(row)]
        joined = " ".join(texts)
        if all(
            label in joined
            for label in ("주차", "날짜", "요일", "근무시간", "활동내역")
        ):
            return index
    return None


def _section_names(package: HwpxPackage) -> tuple[str, ...]:
    return tuple(
        name
        for name in package.entries
        if name.startswith("Contents/") and name.endswith(".xml")
    )


def _text_entry_names(entries: dict[str, bytes]) -> tuple[str, ...]:
    return tuple(name for name in entries if _is_text_entry(name))


def _is_text_entry(name: str) -> bool:
    return (
        name.startswith("Contents/") and name.endswith(".xml")
    ) or name == "Preview/PrvText.txt"


def _refresh_preview_text(entries: dict[str, bytes]) -> dict[str, bytes]:
    if "Preview/PrvText.txt" not in entries:
        return entries
    updated = dict(entries)
    updated["Preview/PrvText.txt"] = _plain_section_text(entries).encode("utf-8")
    return updated


def _plain_section_text(entries: dict[str, bytes]) -> str:
    lines: list[str] = []
    for name, value in entries.items():
        if not (name.startswith("Contents/") and name.endswith(".xml")):
            continue
        root = ElementTree.fromstring(value)
        lines.extend(text for text in (node.text for node in _text_nodes(root)) if text)
    return "\r\n".join(lines)


def _tables(root: Element) -> tuple[Element, ...]:
    return tuple(item for item in root.iter() if _local_name(item.tag) == "tbl")


def _rows(table: Element) -> tuple[Element, ...]:
    return tuple(item for item in list(table) if _local_name(item.tag) == "tr")


def _cells(row: Element) -> tuple[Element, ...]:
    return tuple(item for item in list(row) if _local_name(item.tag) == "tc")


def _text_nodes(root: Element) -> tuple[Element, ...]:
    return tuple(item for item in root.iter() if _local_name(item.tag) == "t")


def _cell_text(cell: Element) -> str:
    return "".join(node.text or "" for node in _text_nodes(cell))


def _set_cell_text(
    cell: Element,
    value: str,
    *,
    char_pr_id: str | None = None,
) -> None:
    nodes = _text_nodes(cell)
    if len(nodes) == 0:
        nodes = (_append_text_node(cell),)
    nodes[0].text = value
    for node in nodes[1:]:
        node.text = ""
    if char_pr_id is not None:
        _set_cell_char_pr(cell, char_pr_id)


def _set_cell_char_pr(cell: Element, char_pr_id: str) -> None:
    for item in cell.iter():
        if _local_name(item.tag) == "run":
            item.set("charPrIDRef", char_pr_id)


def _append_text_node(cell: Element) -> Element:
    for item in cell.iter():
        if _local_name(item.tag) == "run":
            text_node = Element(f"{{{_namespace(item.tag)}}}t")
            item.append(text_node)
            return text_node
    namespace = _namespace(cell.tag)
    paragraph = Element(f"{{{namespace}}}p")
    run = Element(f"{{{namespace}}}run")
    text_node = Element(f"{{{namespace}}}t")
    run.append(text_node)
    paragraph.append(run)
    cell.append(paragraph)
    return text_node


def _namespace(tag: str) -> str:
    if tag.startswith("{"):
        return tag[1:].split("}", maxsplit=1)[0]
    return ""


def _local_name(tag: str) -> str:
    return tag.rsplit("}", maxsplit=1)[-1]


def _xml_bytes(root: Element, *, source: bytes | None = None) -> bytes:
    xml = tostring(root, encoding="utf-8", xml_declaration=True)
    if source is None:
        return xml
    return _restore_section_prefix(xml, source)


def _restore_section_prefix(xml: bytes, source: bytes) -> bytes:
    source_marker = source.find(b"<hp:p")
    xml_marker = xml.find(b"<hp:p")
    if source_marker < 0 or xml_marker < 0:
        return xml
    return source[:source_marker] + xml[xml_marker:]


def _default_compression(name: str) -> int:
    if name == "mimetype":
        return zipfile.ZIP_STORED
    return zipfile.ZIP_DEFLATED
