#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
# ─── How to run ───
# uv run scripts/init_run.py --root "$PWD"
# uv run scripts/init_run.py --root "$PWD" --run-id 20260629-143000
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

SCHEMA: Final = "field-practice.run.v1"
SUBDIRS: Final = ("inputs", "draft", "document", "qa", "final")


@dataclass(frozen=True, slots=True)
class RunLayout:
    schema: str
    run_id: str
    created_at: str
    workspace_root: str
    run_dir: str
    intake_json: str
    manifest_md: str
    inputs_dir: str
    draft_dir: str
    document_dir: str
    qa_dir: str
    final_dir: str


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create field-practice-out/<run-id>/ under a workspace root.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Workspace root for field-practice-out; defaults to current directory.",
    )
    parser.add_argument(
        "--run-id",
        default=_default_run_id(),
        help="Run directory name. Defaults to YYYYMMDD-HHMMSS in UTC.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable layout JSON.",
    )
    args = parser.parse_args()

    root = args.root.expanduser().resolve()
    run_dir = root / "field-practice-out" / args.run_id
    layout = _build_layout(root=root, run_dir=run_dir, run_id=args.run_id)
    _create_layout(layout)

    if args.json:
        sys.stdout.write(json.dumps(asdict(layout), ensure_ascii=False, indent=2))
        sys.stdout.write("\n")
    else:
        sys.stdout.write(f"{layout.run_dir}\n")
    return 0


def _default_run_id() -> str:
    return datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")


def _build_layout(root: Path, run_dir: Path, run_id: str) -> RunLayout:
    return RunLayout(
        schema=SCHEMA,
        run_id=run_id,
        created_at=datetime.now(tz=UTC).isoformat(timespec="seconds"),
        workspace_root=str(root),
        run_dir=str(run_dir),
        intake_json=str(run_dir / "intake.json"),
        manifest_md=str(run_dir / "manifest.md"),
        inputs_dir=str(run_dir / "inputs"),
        draft_dir=str(run_dir / "draft"),
        document_dir=str(run_dir / "document"),
        qa_dir=str(run_dir / "qa"),
        final_dir=str(run_dir / "final"),
    )


def _create_layout(layout: RunLayout) -> None:
    run_dir = Path(layout.run_dir)
    run_dir.mkdir(parents=True, exist_ok=False)
    for name in SUBDIRS:
        (run_dir / name).mkdir()
    Path(layout.intake_json).write_text(
        json.dumps(_intake_payload(layout), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    Path(layout.manifest_md).write_text(_manifest_text(layout), encoding="utf-8")


def _intake_payload(layout: RunLayout) -> dict[str, str]:
    return {
        "schema": layout.schema,
        "run_id": layout.run_id,
        "created_at": layout.created_at,
        "workspace_root": layout.workspace_root,
        "submission_format": "",
        "scenario": "",
        "template_paths": "",
        "evidence_paths": "",
        "human_review": "",
    }


def _manifest_text(layout: RunLayout) -> str:
    return (
        "# Field Practice Run Manifest\n\n"
        f"- schema: `{layout.schema}`\n"
        f"- run_id: `{layout.run_id}`\n"
        f"- created_at: `{layout.created_at}`\n"
        f"- workspace_root: `{layout.workspace_root}`\n\n"
        "## Outputs\n"
        "- draft: pending\n"
        "- document: pending\n"
        "- qa: pending\n"
        "- final: pending\n"
    )


if __name__ == "__main__":
    sys.exit(main())
