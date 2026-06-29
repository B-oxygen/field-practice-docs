from __future__ import annotations

import subprocess
from pathlib import Path

from field_practice.discover_git import discover_git_repos


def test_discover_git_repos_when_root_is_not_repo_then_finds_nested_repo(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "service"
    ignored_repo = tmp_path / "node_modules" / "ignored"
    repo.mkdir()
    ignored_repo.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "init"], cwd=ignored_repo, check=True, capture_output=True)

    repos = discover_git_repos(tmp_path)

    assert repos == [repo]


def test_discover_git_repos_when_repo_is_deeper_than_max_depth_then_skips(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "a" / "b" / "c"
    repo.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)

    repos = discover_git_repos(tmp_path, max_depth=1)

    assert repos == []
