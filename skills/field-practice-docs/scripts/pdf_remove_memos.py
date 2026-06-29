from __future__ import annotations

import argparse
import sys
import unicodedata
from pathlib import Path

try:
    import fitz
except ImportError:
    print(
        "PyMuPDF required. Run with: uv run --with pymupdf python pdf_remove_memos.py ...",
        file=sys.stderr,
    )
    raise SystemExit(2) from None


def _is_memo_fill(fill: object, rect: "fitz.Rect", min_x: float) -> bool:
    if not isinstance(fill, (tuple, list)) or len(fill) != 3:
        return False
    red, green, blue = fill
    return (
        green >= 0.9
        and 0.6 <= red <= 0.95
        and 0.4 <= blue <= 0.85
        and rect.x0 >= min_x
    )


def clean_pdf(src: Path, dst: Path, *, min_x_frac: float, pad: float) -> int:
    doc = fitz.open(src)
    removed = 0
    for page in doc:
        for annot in list(page.annots() or []):
            page.delete_annot(annot)
            removed += 1
        min_x = page.rect.width * min_x_frac
        boxes = [
            draw["rect"]
            for draw in page.get_drawings()
            if _is_memo_fill(draw.get("fill"), draw["rect"], min_x)
        ]
        unique: list[fitz.Rect] = []
        for rect in boxes:
            if not any(
                abs(rect.x0 - seen.x0) < 2 and abs(rect.y0 - seen.y0) < 2
                for seen in unique
            ):
                unique.append(rect)
        for rect in unique:
            page.add_redact_annot(
                fitz.Rect(rect.x0 - pad, rect.y0 - pad, rect.x1 + pad, rect.y1 + pad),
                fill=(1, 1, 1),
            )
        page.apply_redactions()
        for rect in unique:
            page.draw_rect(
                fitz.Rect(rect.x0 - pad, rect.y0 - pad, rect.x1 + pad, rect.y1 + pad),
                color=(1, 1, 1),
                fill=(1, 1, 1),
            )
        removed += len(unique)
    doc.save(dst, garbage=4, deflate=True)
    doc.close()
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Remove flattened green memo boxes and PDF annotations from PDF(s). "
            "Form content stays; only right-margin memo boxes are redacted."
        )
    )
    parser.add_argument("inputs", type=Path, help="A .pdf file or a directory of PDFs")
    parser.add_argument("out_dir", type=Path, help="Output directory")
    parser.add_argument("--min-x-frac", type=float, default=0.72)
    parser.add_argument("--pad", type=float, default=5.0)
    args = parser.parse_args()

    sources = (
        sorted(args.inputs.glob("*.pdf"))
        if args.inputs.is_dir()
        else [args.inputs]
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for src in sources:
        name = unicodedata.normalize("NFC", src.name)
        dst = args.out_dir / name
        count = clean_pdf(src, dst, min_x_frac=args.min_x_frac, pad=args.pad)
        print(f"{name}: removed {count} memo/annotation element(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
