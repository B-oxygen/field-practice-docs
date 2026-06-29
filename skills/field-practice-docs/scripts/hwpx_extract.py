from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path

_RUN = re.compile(r"<hp:t>(.*?)</hp:t>", re.S)
_UNESCAPE = (
    ("&lt;", "<"),
    ("&gt;", ">"),
    ("&quot;", '"'),
    ("&apos;", "'"),
    ("&amp;", "&"),
)


def _unescape(text: str) -> str:
    for token, char in _UNESCAPE:
        text = text.replace(token, char)
    return text


def extract_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        sections = sorted(
            name
            for name in archive.namelist()
            if re.fullmatch(r"Contents/section\d+\.xml", name)
        )
        lines: list[str] = []
        for name in sections:
            xml = archive.read(name).decode("utf-8", "replace")
            for paragraph in xml.split("</hp:p>"):
                runs = _RUN.findall(paragraph)
                if not runs:
                    continue
                for line in _unescape("".join(runs)).split("\n"):
                    cleaned = line.strip()
                    if cleaned:
                        lines.append(cleaned)
        return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract paragraph text from an HWPX (one paragraph per line)."
    )
    parser.add_argument("hwpx", type=Path, help="Path to the .hwpx file")
    parser.add_argument("--out", type=Path, default=None, help="Write text here")
    args = parser.parse_args()
    text = extract_text(args.hwpx)
    if args.out is None:
        print(text)
        return 0
    args.out.write_text(text + "\n", encoding="utf-8")
    print(f"wrote {len(text.splitlines())} lines to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
