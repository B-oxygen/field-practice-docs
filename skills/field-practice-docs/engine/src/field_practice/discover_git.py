from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from shutil import which
from typing import Final

GIT: Final = which("git") or "/usr/bin/git"
IGNORED_DIRS: Final = frozenset(
    {
        ".cache",
        ".next",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "venv",
    }
)


def discover_git_repos(root: Path, *, max_depth: int = 5) -> list[Path]:
    if not root.exists():
        sys.stderr.write(f"No git repositories found: root does not exist: {root}\n")
        return []
    repos = sorted(_walk_git_repos(root.resolve(), max_depth=max_depth))
    if len(repos) == 0:
        sys.stderr.write(f"No git repositories found under {root}\n")
    return repos


def _walk_git_repos(root: Path, *, max_depth: int) -> set[Path]:
    repos: set[Path] = set()
    pending: list[tuple[Path, int]] = [(root, 0)]
    while len(pending) > 0:
        current, depth = pending.pop()
        if _is_ignored(current):
            continue
        if _has_git_marker(current) and _is_git_worktree(current):
            repos.add(current)
        if depth >= max_depth:
            continue
        for child in _child_dirs(current):
            pending.append((child, depth + 1))
    return repos


def _child_dirs(path: Path) -> tuple[Path, ...]:
    return tuple(
        child
        for child in path.iterdir()
        if child.is_dir() and child.name not in IGNORED_DIRS and child.name != ".git"
    )


def _has_git_marker(path: Path) -> bool:
    return (path / ".git").exists()


def _is_git_worktree(path: Path) -> bool:
    result = subprocess.run(
        [GIT, "-C", str(path), "rev-parse", "--is-inside-work-tree"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def _is_ignored(path: Path) -> bool:
    return path.name in IGNORED_DIRS
