from __future__ import annotations

import argparse
import re
from pathlib import Path

_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/+-]*")


def check_pairs(
    pairs: list[tuple[str, str]],
    proper_nouns: tuple[str, ...],
) -> list[str]:
    failures: list[str] = []
    for index, (old, new) in enumerate(pairs):
        old_tokens = {token.lower() for token in _TOKEN.findall(old)}
        new_tokens = {token.lower() for token in _TOKEN.findall(new)}
        missing = sorted(old_tokens - new_tokens)
        if missing:
            failures.append(f"row {index}: dropped tokens {missing}")
        for noun in proper_nouns:
            if noun in old and noun not in new:
                failures.append(f"row {index}: dropped proper noun '{noun}'")
    return failures


def load_pairs(path: Path) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if "\t" not in line:
            continue
        old, new = line.split("\t", 1)
        pairs.append((old, new))
    return pairs


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify a de-slop / rewrite preserved every English/number token and "
            "listed proper noun. Input is a TSV of old<TAB>new per line."
        )
    )
    parser.add_argument("tsv", type=Path, help="old<TAB>new pairs, one per line")
    parser.add_argument(
        "--proper-nouns",
        default="",
        help="Comma-separated Korean proper nouns that must be preserved",
    )
    args = parser.parse_args()
    nouns = tuple(n.strip() for n in args.proper_nouns.split(",") if n.strip())
    pairs = load_pairs(args.tsv)
    failures = check_pairs(pairs, nouns)
    print(f"pairs checked: {len(pairs)}")
    if failures:
        print(f"FAILURES: {len(failures)}")
        for failure in failures[:50]:
            print(f"  {failure}")
        return 1
    print("PASS: all facts preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
