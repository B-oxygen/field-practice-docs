from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from xml.etree.ElementTree import Element, tostring

from defusedxml import ElementTree

from field_practice.hwpx_xml import HwpxPackage


@dataclass(frozen=True, slots=True)
class CellFill:
    section_path: str
    table_index: int
    row_index: int
    cell_index: int
    text: str
    char_pr_id: str | None = None


@dataclass(frozen=True, slots=True)
class CellFillAddressError(Exception):
    fill: CellFill
    detail: str

    def __str__(self) -> str:
        return (
            f"{self.detail}: {self.fill.section_path} "
            f"table={self.fill.table_index} row={self.fill.row_index} "
            f"cell={self.fill.cell_index}"
        )


def fill_table_cells(package: HwpxPackage, fills: Sequence[CellFill]) -> HwpxPackage:
    entries = dict(package.entries)
    changed_sections = {fill.section_path for fill in fills}
    for section_path in changed_sections:
        root = ElementTree.fromstring(entries[section_path])
        for fill in (item for item in fills if item.section_path == section_path):
            _apply_fill(root, fill)
        entries[section_path] = _xml_bytes(root, source=entries[section_path])
    return HwpxPackage(
        entries=_refresh_preview_text(entries),
        compression_types=package.compression_types,
    )


def _apply_fill(root: Element, fill: CellFill) -> None:
    table = _addressed(_tables(root), fill.table_index, fill, "table")
    row = _addressed(_rows(table), fill.row_index, fill, "row")
    cell = _addressed(_cells(row), fill.cell_index, fill, "cell")
    _set_cell_text(cell, fill.text, char_pr_id=fill.char_pr_id)


def _addressed(
    items: tuple[Element, ...],
    index: int,
    fill: CellFill,
    label: str,
) -> Element:
    if 0 <= index < len(items):
        return items[index]
    raise CellFillAddressError(fill, f"{label} index out of range")


def _set_cell_text(
    cell: Element,
    value: str,
    *,
    char_pr_id: str | None,
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


def _namespace(tag: str) -> str:
    if tag.startswith("{"):
        return tag[1:].split("}", maxsplit=1)[0]
    return ""


def _local_name(tag: str) -> str:
    return tag.rsplit("}", maxsplit=1)[-1]


def _xml_bytes(root: Element, *, source: bytes) -> bytes:
    xml = tostring(root, encoding="utf-8", xml_declaration=True)
    return _restore_section_prefix(xml, source)


def _restore_section_prefix(xml: bytes, source: bytes) -> bytes:
    source_marker = source.find(b"<hp:p")
    xml_marker = xml.find(b"<hp:p")
    if source_marker < 0 or xml_marker < 0:
        return xml
    return source[:source_marker] + xml[xml_marker:]
