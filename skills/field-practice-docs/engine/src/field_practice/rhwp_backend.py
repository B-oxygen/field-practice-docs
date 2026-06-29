from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

_BRIDGE = Path(__file__).resolve().parents[2] / "scripts" / "hwp_rhwp.mjs"


@dataclass(frozen=True, slots=True)
class RhwpStatus:
    available: bool
    note: str


@dataclass(frozen=True, slots=True)
class RhwpResult:
    ok: bool
    output: Path | None
    detail: str


@dataclass(frozen=True, slots=True)
class HopStatus:
    available: bool
    note: str


def _core_available(node_path: str) -> bool:
    probe = "try{require.resolve('@rhwp/core');process.exit(0)}catch(e){process.exit(1)}"
    result = subprocess.run(  # noqa: S603 - fixed local node probe
        [node_path, "-e", probe],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def rhwp_status() -> RhwpStatus:
    node_path = shutil.which("node")
    if node_path is None:
        return RhwpStatus(
            available=False,
            note=(
                "rhwp unavailable: Node.js not found. Install Node.js and run "
                "`npm install @rhwp/core` to enable .hwp/.hwpx read, edit and export."
            ),
        )
    if not _BRIDGE.exists():
        return RhwpStatus(available=False, note=f"rhwp bridge missing: {_BRIDGE}")
    if _core_available(node_path):
        return RhwpStatus(
            available=True,
            note="rhwp ready (@rhwp/core via Node): .hwp/.hwpx read, replaceAll, export.",
        )
    return RhwpStatus(
        available=False,
        note="rhwp bridge present; run `npm install @rhwp/core` to enable conversion.",
    )


def convert_hwp(
    source: Path,
    output: Path,
    mapping: dict[str, str] | None = None,
    *,
    node: str = "node",
) -> RhwpResult:
    node_path = shutil.which(node)
    if node_path is None:
        return RhwpResult(ok=False, output=None, detail="Node.js not found")
    if not _BRIDGE.exists():
        return RhwpResult(ok=False, output=None, detail=f"bridge missing: {_BRIDGE}")
    args = [node_path, str(_BRIDGE), str(source), str(output)]
    mapping_file: Path | None = None
    if mapping:
        mapping_file = output.with_name(output.name + ".rhwp-map.json")
        mapping_file.write_text(
            json.dumps(mapping, ensure_ascii=False), encoding="utf-8"
        )
        args.append(str(mapping_file))
    result = subprocess.run(  # noqa: S603 - fixed local rhwp bridge invocation
        args, capture_output=True, text=True, check=False
    )
    if mapping_file is not None:
        mapping_file.unlink(missing_ok=True)
    if result.returncode == 0 and output.exists() and output.stat().st_size > 0:
        return RhwpResult(ok=True, output=output, detail=result.stdout.strip())
    return RhwpResult(
        ok=False,
        output=None,
        detail=result.stderr.strip() or result.stdout.strip() or "rhwp conversion failed",
    )


def _hop_app_path() -> Path | None:
    for path in (
        Path("/Applications/HOP.app"),
        Path.home() / "Applications" / "HOP.app",
    ):
        if path.exists():
            return path
    return None


def hop_status() -> HopStatus:
    if _hop_app_path() is not None:
        return HopStatus(
            available=True,
            note="HOP.app detected: macOS GUI to view/edit .hwp/.hwpx.",
        )
    if shutil.which("brew") is not None:
        return HopStatus(
            available=False,
            note="HOP not installed; run `brew install --cask hop`.",
        )
    return HopStatus(
        available=False,
        note="HOP not installed; download from https://github.com/golbin/hop/releases.",
    )


def open_in_hop(path: Path) -> RhwpResult:
    if _hop_app_path() is None:
        return RhwpResult(
            ok=False,
            output=None,
            detail="HOP not installed; run `brew install --cask hop`",
        )
    opener = shutil.which("open")
    if opener is None:
        return RhwpResult(ok=False, output=None, detail="`open` not found (macOS only)")
    result = subprocess.run(  # noqa: S603 - fixed macOS HOP opener invocation
        [opener, "-a", "HOP", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return RhwpResult(ok=True, output=path, detail="opened in HOP")
    return RhwpResult(
        ok=False,
        output=None,
        detail=result.stderr.strip() or "failed to open HOP",
    )
