from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path

_SECTION = re.compile(r"Contents/section\d+\.xml")


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def replace_in_hwpx(
    src: Path,
    dst: Path,
    mapping: dict[str, str],
    *,
    wrap: bool = True,
) -> int:
    with zipfile.ZipFile(src) as archive:
        blobs = {name: archive.read(name) for name in archive.namelist()}
    replaced = 0
    for name, blob in list(blobs.items()):
        if not _SECTION.fullmatch(name):
            continue
        xml = blob.decode("utf-8")
        for old, new in mapping.items():
            if wrap:
                needle = f"<hp:t>{_escape(old)}</hp:t>"
                value = f"<hp:t>{_escape(new)}</hp:t>"
            else:
                needle, value = _escape(old), _escape(new)
            count = xml.count(needle)
            if count:
                xml = xml.replace(needle, value)
                replaced += count
        blobs[name] = xml.encode("utf-8")
    ordered = sorted(blobs, key=lambda name: (name != "mimetype", name))
    with zipfile.ZipFile(dst, "w") as archive:
        for name in ordered:
            store = name == "mimetype"
            archive.writestr(
                name,
                blobs[name],
                compress_type=zipfile.ZIP_STORED if store else zipfile.ZIP_DEFLATED,
            )
    return replaced


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Replace text in an HWPX and repackage it (mimetype stays first and "
            "uncompressed, as the OPC/HWPX container requires)."
        )
    )
    parser.add_argument("src", type=Path, help="Source .hwpx")
    parser.add_argument("dst", type=Path, help="Output .hwpx (do not overwrite src)")
    parser.add_argument(
        "mapping", type=Path, help="JSON object of {old_text: new_text}"
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Match anywhere in the run text, not only whole <hp:t> paragraphs",
    )
    args = parser.parse_args()
    mapping: dict[str, str] = json.loads(args.mapping.read_text(encoding="utf-8"))
    count = replace_in_hwpx(args.src, args.dst, mapping, wrap=not args.raw)
    print(f"replaced {count} occurrence(s); wrote {args.dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
