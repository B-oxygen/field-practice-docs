from __future__ import annotations

import argparse
import json
import re
import zipfile
from collections import Counter
from pathlib import Path

_RUN = re.compile(r"<hp:t>(.*?)</hp:t>", re.S)

_PROTECT = re.compile(r"[A-Za-z]+|\d[\d,./:%~-]*|\"[^\"]*\"|'[^']*'|“[^”]*”")

_FILLERS = (
    "짧은 근무시간에 맞추어",
    "관점에서",
    "기준으로",
    "수 있도록",
)

_TRANSLATIONESE = (
    "에 대해",
    "을 통해",
    "를 통해",
    "통하여",
    "에 있어",
    "라는 점에서",
    "와 관련하여",
    "과 관련하여",
    "와 관련된",
    "과 관련된",
    "을 바탕으로",
    "를 바탕으로",
    "에 기반하여",
    "에 의해",
    "을 위해",
    "를 위해",
)

_DOUBLE_PASSIVE = (
    "되어진",
    "되어졌",
    "되어지",
    "여진다",
    "여졌다",
    "보여진",
    "쓰여진",
    "잊혀진",
    "불려진",
    "놓여진",
)

_HAVE_MAKE = (
    "가지고 있",
    "가지고있",
    "갖고 있",
    "갖고있",
)

_CONCLUSION_PIVOTS = (
    "결론적으로",
    "요약하면",
    "종합하면",
    "정리하자면",
    "따라서",
    "그러므로",
    "라고 할 수 있",
    "라고 볼 수 있",
)

_HYPE = (
    "혁신적",
    "획기적",
    "전례 없",
    "압도적",
    "막강",
    "폭발적",
    "파격적",
    "대대적",
    "강력한",
    "치열",
)

_CONNECTORS = (
    "또한",
    "따라서",
    "나아가",
    "아울러",
    "게다가",
    "더욱이",
)

_PROGRESSIVE = re.compile(r"고\s*있(?:다|었|는|을|던|는다)")
_DOUBLE_PARTICLE = re.compile(r"(?:에서의|에로의|으로의|에의|으로부터의|로부터의)")
_ENDING_COMMA = re.compile(r"(?:고|며|지만|면서|아서|어서)\s*,")
_HANJA_NOMINALIZER = re.compile(r"[가-힣](성|적|화)(?=[\s.,·)]|을|를|은|는|의|에|이|$)")


def _extract_hwpx(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        names = sorted(
            n for n in archive.namelist() if re.fullmatch(r"Contents/section\d+\.xml", n)
        )
        out: list[str] = []
        for name in names:
            xml = archive.read(name).decode("utf-8", "replace")
            for paragraph in xml.split("</hp:p>"):
                runs = _RUN.findall(paragraph)
                if not runs:
                    continue
                for line in "".join(runs).split("\n"):
                    cleaned = line.strip()
                    if cleaned:
                        out.append(cleaned)
        return "\n".join(out)


def load_text(path: Path) -> str:
    if path.suffix.lower() == ".hwpx":
        return _extract_hwpx(path)
    return path.read_text(encoding="utf-8")


def _mask_facts(text: str) -> str:
    return _PROTECT.sub(lambda match: " " * len(match.group()), text)


def _count_tokens(text: str, tokens: tuple[str, ...]) -> dict[str, int]:
    return {token: text.count(token) for token in tokens if text.count(token)}


def analyze(text: str) -> dict[str, object]:
    masked = _mask_facts(text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    sentences = [line for line in lines if re.search(r"(함|음|함\.|음\.)$", line)]
    endings = Counter(line[-3:] for line in sentences)
    verbs = Counter(
        match.group(1)[-2:]
        for line in sentences
        if (match := re.search(r"([가-힣]+)(함|하였음|했음)\.?$", line))
    )
    titles = sum(1 for line in lines if line.startswith("[") and line.endswith("]"))
    top_ending = endings.most_common(1)
    ending_ratio = (
        round(top_ending[0][1] / max(len(sentences), 1), 3) if top_ending else 0.0
    )
    translationese = _count_tokens(masked, _TRANSLATIONESE)
    double_passive = _count_tokens(masked, _DOUBLE_PASSIVE)
    have_make = _count_tokens(masked, _HAVE_MAKE)
    conclusion = _count_tokens(masked, _CONCLUSION_PIVOTS)
    hype = _count_tokens(masked, _HYPE)
    connectors = _count_tokens(masked, _CONNECTORS)
    progressive = len(_PROGRESSIVE.findall(masked))
    double_particle = len(_DOUBLE_PARTICLE.findall(masked))
    ending_comma = len(_ENDING_COMMA.findall(masked))
    hanja = len(_HANJA_NOMINALIZER.findall(masked))
    flags = _risk_flags(
        ending_ratio,
        sum(conclusion.values()),
        ending_comma,
        sum(double_passive.values()),
        sum(hype.values()),
        sum(translationese.values()),
        double_particle,
        hanja,
    )
    score = sum(2 if level == "S1" else 1 for _, level in flags)
    band = "high" if score >= 6 else "medium" if score >= 3 else "low"
    return {
        "sentences": len(sentences),
        "titles": titles,
        "dominant_ending_ratio": ending_ratio,
        "ending_top": endings.most_common(6),
        "verb_top": verbs.most_common(8),
        "filler_hits": _count_tokens(text, _FILLERS),
        "translationese_hits": translationese,
        "double_passive_hits": double_passive,
        "have_make_hits": have_make,
        "conclusion_pivot_hits": conclusion,
        "hype_hits": hype,
        "connector_hits": connectors,
        "progressive_aspect": progressive,
        "double_particle": double_particle,
        "ending_comma": ending_comma,
        "hanja_nominalizer": hanja,
        "risk_flags": flags,
        "risk_score": score,
        "risk_band": band,
    }


def _risk_flags(
    ending_ratio: float,
    conclusion: int,
    ending_comma: int,
    double_passive: int,
    hype: int,
    translationese: int,
    double_particle: int,
    hanja: int,
) -> list[tuple[str, str]]:
    flags: list[tuple[str, str]] = []
    if ending_ratio >= 0.9:
        flags.append(("dominant_ending>=0.9", "S1"))
    if conclusion >= 3:
        flags.append(("conclusion_pivots>=3", "S1"))
    if ending_comma >= 6:
        flags.append(("ending_comma>=6", "S1"))
    if double_passive > 0:
        flags.append(("double_passive", "S1"))
    if hype > 0:
        flags.append(("hype_words", "S1"))
    if translationese >= 6:
        flags.append(("translationese>=6", "S2"))
    if double_particle > 3:
        flags.append(("double_particle>3", "S2"))
    if hanja > 12:
        flags.append(("hanja_nominalizer>12", "S2"))
    return flags


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Quantify AI-tells in a Korean activity report (.hwpx or .txt). "
            "Korean slop signals adapted from epoko77-ai/im-not-ai (MIT). "
            "Numbers, dates, English and quoted spans are masked before scoring "
            "so facts are never flagged."
        )
    )
    parser.add_argument("source", type=Path, help="A .hwpx or extracted .txt")
    parser.add_argument(
        "--json", action="store_true", help="Print the full report as JSON"
    )
    args = parser.parse_args()
    report = analyze(load_text(args.source))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    print(f"sentences         : {report['sentences']}")
    print(f"bracket titles    : {report['titles']}")
    print(f"dominant ending % : {report['dominant_ending_ratio']}")
    print(f"ending top        : {report['ending_top']}")
    print(f"verb top          : {report['verb_top']}")
    print(f"filler hits       : {report['filler_hits']}")
    print(f"translationese    : {report['translationese_hits']}")
    print(f"double passive    : {report['double_passive_hits']}")
    print(f"have/make literal : {report['have_make_hits']}")
    print(f"conclusion pivots : {report['conclusion_pivot_hits']}")
    print(f"hype words        : {report['hype_hits']}")
    print(f"connectors        : {report['connector_hits']}")
    print(f"progressive aspect: {report['progressive_aspect']}")
    print(f"double particle   : {report['double_particle']}")
    print(f"ending comma      : {report['ending_comma']}")
    print(f"hanja nominalizer : {report['hanja_nominalizer']}")
    print(f"risk flags        : {report['risk_flags']}")
    print(f"risk band         : {report['risk_band']} (score {report['risk_score']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
