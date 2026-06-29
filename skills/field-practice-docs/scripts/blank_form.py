from __future__ import annotations

import argparse
import json
import re
import struct
import zlib
import zipfile
from pathlib import Path

_T = re.compile(r"<hp:t>(.*?)</hp:t>", re.S)
_SECTION = re.compile(r"Contents/section\d+\.xml")
_IMAGE = re.compile(r"BinData/.*\.(?:png|jpg|jpeg|bmp|gif|tif|tiff)$", re.I)


def _tiny_png() -> bytes:
    signature = b"\x89PNG\r\n\x1a\n"

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(
            ">I", zlib.crc32(body) & 0xFFFFFFFF
        )

    header = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    pixel = zlib.compress(b"\x00\x00\x00\x00\x00")
    return signature + chunk(b"IHDR", header) + chunk(b"IDAT", pixel) + chunk(
        b"IEND", b""
    )


def _keep(
    text: str, keep_exact: set[str], keep_regex: list[re.Pattern[str]]
) -> bool:
    stripped = text.strip()
    if stripped == "":
        return True
    if stripped in keep_exact:
        return True
    return any(pattern.search(stripped) for pattern in keep_regex)


def blank_hwpx(
    src: Path,
    dst: Path,
    keep_exact: set[str],
    keep_regex: list[re.Pattern[str]],
    transforms: list[tuple[str, str]],
    image_min_bytes: int,
) -> tuple[int, int]:
    with zipfile.ZipFile(src) as archive:
        blobs = {name: archive.read(name) for name in archive.namelist()}
    blanked = 0
    images = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal blanked
        inner = match.group(1)
        for needle, value in transforms:
            inner = inner.replace(needle, value)
        if _keep(inner, keep_exact, keep_regex):
            return f"<hp:t>{inner}</hp:t>"
        blanked += 1
        return "<hp:t></hp:t>"

    for name in list(blobs):
        if _SECTION.fullmatch(name):
            blobs[name] = _T.sub(repl, blobs[name].decode("utf-8")).encode("utf-8")
        elif image_min_bytes and _IMAGE.match(name) and len(blobs[name]) >= image_min_bytes:
            blobs[name] = _tiny_png()
            images += 1
    ordered = sorted(blobs, key=lambda name: (name != "mimetype", name))
    with zipfile.ZipFile(dst, "w") as archive:
        for name in ordered:
            store = name == "mimetype"
            archive.writestr(
                name,
                blobs[name],
                compress_type=zipfile.ZIP_STORED if store else zipfile.ZIP_DEFLATED,
            )
    return blanked, images


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Blank a filled HWPX into a reusable template. Whitelist approach: keep "
            "only structural text (title, labels, table headers, date skeleton) and "
            "empty every other cell, so personal data can never leak. Build the keep "
            "file by first running hwpx_extract.py and listing the form's structural "
            "strings. Large embedded images (e.g. a scanned certificate) can be "
            "replaced with a 1x1 transparent PNG via --blank-images-over."
        )
    )
    parser.add_argument("src", type=Path, help="Source .hwpx (convert .hwp first)")
    parser.add_argument("dst", type=Path, help="Output blanked .hwpx")
    parser.add_argument(
        "--keep",
        type=Path,
        required=True,
        help='JSON {"exact":[...], "regex":[...], "transform":[[old,new],...]}',
    )
    parser.add_argument(
        "--blank-images-over",
        type=int,
        default=0,
        metavar="BYTES",
        help="Replace BinData images >= BYTES with a blank 1x1 PNG (0 keeps all)",
    )
    args = parser.parse_args()
    config = json.loads(args.keep.read_text(encoding="utf-8"))
    keep_exact = set(config.get("exact", []))
    keep_regex = [re.compile(pattern) for pattern in config.get("regex", [])]
    transforms = [(pair[0], pair[1]) for pair in config.get("transform", [])]
    blanked, images = blank_hwpx(
        args.src, args.dst, keep_exact, keep_regex, transforms, args.blank_images_over
    )
    print(f"blanked {blanked} text node(s); blanked {images} image(s); wrote {args.dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
