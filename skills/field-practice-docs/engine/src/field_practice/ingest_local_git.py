from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from shutil import which
from typing import Final

from field_practice.classify import (
    classify_text,
    has_sensitive_text,
    redact_sensitive,
    report_phrase,
)
from field_practice.discover_git import discover_git_repos
from field_practice.models import Confidence, Evidence, SourceType
from field_practice.timeparse import parse_local_date
from field_practice.weeks import in_period, week_for_date

GIT: Final = which("git") or "/usr/bin/git"


@dataclass(frozen=True, slots=True)
class LocalGitCommit:
    commit_hash: str
    raw_date: str
    subject: str
    changed_files: tuple[str, ...]


def collect_local_git_evidence(
    repo_root: Path,
    since: str = "2026-03-02",
    until: str = "2026-06-21 23:59:59",
) -> list[Evidence]:
    repos = discover_git_repos(repo_root)
    evidence: list[Evidence] = []
    for repo in repos:
        commits = _local_commits(repo, since=since, until=until)
        for commit in commits:
            item = _local_commit_evidence(
                repo=repo,
                commit=commit,
                evidence_id=f"GH-LOCAL-{len(evidence) + 1:04d}",
            )
            if item is not None:
                evidence.append(item)
    return evidence


def _local_commits(repo: Path, *, since: str, until: str) -> tuple[LocalGitCommit, ...]:
    result = subprocess.run(
        [
            GIT,
            "-C",
            str(repo),
            "log",
            "--all",
            f"--since={since}",
            f"--until={until}",
            "--date=iso-strict",
            "--pretty=format:__COMMIT__%H|%an|%ae|%ad|%s",
            "--numstat",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(f"Skipping git repo with unreadable log: {repo}\n")
        return ()
    return _parse_local_git_log(result.stdout)


def _parse_local_git_log(raw_log: str) -> tuple[LocalGitCommit, ...]:
    commits: list[LocalGitCommit] = []
    current: LocalGitCommit | None = None
    changed_files: list[str] = []
    for line in raw_log.splitlines():
        if line.startswith("__COMMIT__"):
            if current is not None:
                commits.append(_with_changed_files(current, changed_files))
            current = _parse_local_commit_header(line)
            changed_files = []
            continue
        if current is not None and line.strip() != "":
            path = _numstat_path(line)
            if path != "":
                changed_files.append(path)
    if current is not None:
        commits.append(_with_changed_files(current, changed_files))
    return tuple(commits)


def _parse_local_commit_header(line: str) -> LocalGitCommit | None:
    parts = line.removeprefix("__COMMIT__").split("|", maxsplit=4)
    if len(parts) != 5:
        return None
    commit_hash, _author, _email, raw_date, subject = parts
    return LocalGitCommit(
        commit_hash=commit_hash,
        raw_date=raw_date,
        subject=subject,
        changed_files=(),
    )


def _numstat_path(line: str) -> str:
    parts = line.split("\t")
    if len(parts) < 3:
        return ""
    return parts[2]


def _with_changed_files(
    commit: LocalGitCommit | None, changed_files: list[str]
) -> LocalGitCommit:
    if commit is None:
        msg = "commit header is required before numstat rows"
        raise RuntimeError(msg)
    return LocalGitCommit(
        commit_hash=commit.commit_hash,
        raw_date=commit.raw_date,
        subject=commit.subject,
        changed_files=tuple(changed_files),
    )


def _local_commit_evidence(
    repo: Path, commit: LocalGitCommit | None, evidence_id: str
) -> Evidence | None:
    if commit is None:
        return None
    item_date = parse_local_date(commit.raw_date)
    if not in_period(item_date):
        return None
    week = week_for_date(item_date)
    if week is None:
        return None
    changed_summary = ", ".join(commit.changed_files[:8])
    description = f"{commit.subject} 변경 파일: {changed_summary}".strip()
    combined = f"{commit.subject} {description}"
    workstream = classify_text(combined)
    title = redact_sensitive(commit.subject)
    return Evidence(
        evidence_id=evidence_id,
        source_type=SourceType.GITHUB_COMMIT_LOCAL,
        source_ref=commit.commit_hash,
        date=item_date,
        week=week,
        title=title,
        description=redact_sensitive(description),
        workstream=workstream,
        confidence=Confidence.A_CANDIDATE,
        sensitive=has_sensitive_text(combined),
        report_phrase=report_phrase(workstream, title),
        repo=repo.name,
    )
