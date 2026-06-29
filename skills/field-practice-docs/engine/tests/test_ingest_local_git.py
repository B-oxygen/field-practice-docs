from __future__ import annotations

import os
import subprocess
from pathlib import Path

from field_practice.ingest_github import ingest_local_git_repos
from field_practice.models import Confidence, SourceType


def test_ingest_local_git_repos_when_commit_in_period_then_returns_evidence(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "uniport-api"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "sejun@example.com"],
        cwd=repo,
        check=True,
    )
    subprocess.run(["git", "config", "user.name", "홍길동"], cwd=repo, check=True)
    (repo / "app.py").write_text("print('dashboard api')\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.py"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "admin dashboard API"],
        cwd=repo,
        check=True,
        env={
            **os.environ,
            "GIT_AUTHOR_DATE": "2026-03-23T09:00:00+09:00",
            "GIT_COMMITTER_DATE": "2026-03-23T09:00:00+09:00",
        },
        capture_output=True,
    )

    evidence = ingest_local_git_repos(tmp_path)

    assert len(evidence) == 1
    assert evidence[0].source_type == SourceType.GITHUB_COMMIT_LOCAL
    assert evidence[0].repo == "uniport-api"
    assert evidence[0].confidence == Confidence.A_CANDIDATE
    assert "app.py" in evidence[0].description
