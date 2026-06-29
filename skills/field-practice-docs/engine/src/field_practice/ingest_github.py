from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from field_practice.classify import (
    classify_text,
    has_sensitive_text,
    redact_sensitive,
    report_phrase,
)
from field_practice.ingest_local_git import collect_local_git_evidence
from field_practice.models import Confidence, Evidence, SourceType
from field_practice.timeparse import parse_local_date
from field_practice.weeks import in_period, week_for_date
from field_practice.writers import write_evidence_csv


def ingest_github(path: Path) -> tuple[Evidence, ...]:
    files = _github_files(path)
    evidence: list[Evidence] = []
    for file_path in files:
        match file_path.suffix.lower():
            case ".txt" | ".log":
                evidence.extend(_parse_git_log(file_path))
            case ".json":
                evidence.extend(_parse_github_json(file_path))
            case _:
                continue
    return tuple(evidence)


def ingest_github_to_csv(input_path: Path, output_path: Path) -> tuple[Evidence, ...]:
    evidence = ingest_github(input_path)
    write_evidence_csv(output_path, evidence)
    return evidence


def ingest_local_git_repos(
    repo_root: Path,
    since: str = "2026-03-02",
    until: str = "2026-06-21 23:59:59",
) -> list[Evidence]:
    return collect_local_git_evidence(repo_root, since, until)


def _github_files(path: Path) -> tuple[Path, ...]:
    if path.is_file():
        return (path,)
    if not path.exists():
        return ()
    return tuple(sorted(file for file in path.rglob("*") if file.is_file()))


def _parse_git_log(path: Path) -> tuple[Evidence, ...]:
    evidence: list[Evidence] = []
    with path.open(encoding="utf-8", errors="replace") as file:
        for line_number, line in enumerate(file, start=1):
            parts = line.strip().split("|", maxsplit=4)
            if len(parts) != 5:
                continue
            commit_hash, author, email, raw_date, subject = parts
            item = _github_evidence(
                evidence_id=f"GH-COMMIT-{len(evidence) + 1:04d}",
                source_type=SourceType.GITHUB_COMMIT,
                source_ref=commit_hash,
                raw_date=raw_date,
                title=subject,
                description=f"{author} {email} {subject}",
                fallback_ref=f"{path.name}:{line_number}",
            )
            if item is not None:
                evidence.append(item)
    return tuple(evidence)


def _parse_github_json(path: Path) -> tuple[Evidence, ...]:
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ()
    if not isinstance(payload, list):
        return ()
    evidence: list[Evidence] = []
    for index, raw_item in enumerate(payload, start=1):
        if not isinstance(raw_item, dict):
            continue
        item = _parse_json_item(path, index, raw_item)
        if item is not None:
            evidence.append(item)
    return tuple(evidence)


def _parse_json_item(
    path: Path, index: int, raw_item: dict[str, Any]
) -> Evidence | None:
    title = str(raw_item.get("title", "GitHub 항목"))
    raw_number = raw_item.get("number", index)
    source_ref = f"#{raw_number}"
    raw_date = str(
        raw_item.get("createdAt")
        or raw_item.get("mergedAt")
        or raw_item.get("closedAt")
        or "",
    )
    body = str(raw_item.get("body", ""))
    source_type = (
        SourceType.GITHUB_PR
        if "prs" in path.name.casefold() or "pull" in path.name.casefold()
        else SourceType.GITHUB_ISSUE
    )
    prefix = "GH-PR" if source_type == SourceType.GITHUB_PR else "GH-ISSUE"
    return _github_evidence(
        evidence_id=f"{prefix}-{index:04d}",
        source_type=source_type,
        source_ref=source_ref,
        raw_date=raw_date,
        title=title,
        description=body,
        fallback_ref=f"{path.name}:{index}",
    )


def _github_evidence(
    evidence_id: str,
    source_type: SourceType,
    source_ref: str,
    raw_date: str,
    title: str,
    description: str,
    fallback_ref: str,
    repo: str = "",
    confidence: Confidence = Confidence.D,
) -> Evidence | None:
    if raw_date == "":
        return None
    item_date = parse_local_date(raw_date)
    if not in_period(item_date):
        return None
    week = week_for_date(item_date)
    if week is None:
        return None
    combined = f"{title} {description}"
    workstream = classify_text(combined)
    safe_title = redact_sensitive(title)
    return Evidence(
        evidence_id=evidence_id,
        source_type=source_type,
        source_ref=source_ref or fallback_ref,
        date=item_date,
        week=week,
        title=safe_title,
        description=redact_sensitive(description),
        workstream=workstream,
        confidence=confidence,
        sensitive=has_sensitive_text(combined),
        report_phrase=report_phrase(workstream, safe_title),
        repo=repo,
    )
