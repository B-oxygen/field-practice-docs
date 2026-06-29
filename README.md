# Field Practice Docs

Codex/Claude skill and local Codex plugin for Korean university field-practice
HWP/HWPX/PDF document automation.

The default workflow does not require Hancom Office. HOP is preferred for GUI
review when available, and render PNG/PDF fallback is supported when HOP cannot
open a visible window.

## One-Line Install

```bash
curl -fsSL https://raw.githubusercontent.com/B-oxygen/field-practice-docs/main/install.sh | bash -s -- https://github.com/B-oxygen/field-practice-docs.git
```

Restart Codex or Claude after installation so the skill/plugin registry is
refreshed.

## What It Installs

- Plugin: `~/plugins/field-practice-docs`
- Personal marketplace entry: `~/.agents/plugins/marketplace.json`
- Claude skill symlink: `~/.claude/skills/field-practice-docs`
- Codex skill symlink: `~/.codex/skills/field-practice-docs`
- Optional Node dependency: `@rhwp/core`

## Public Commands

The engine exposes only three top-level commands:

```bash
cd ~/plugins/field-practice-docs/skills/field-practice-docs/engine
uv run field-practice --help
```

- `doctor`: check machine, templates, HOP/rhwp readiness
- `draft`: build reports from git/calendar/alog evidence
- `document`: fill, render, verify, clean PDF, and prepare final files

## Verify Install

```bash
python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py ~/plugins/field-practice-docs
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py ~/plugins/field-practice-docs/skills/field-practice-docs

cd ~/plugins/field-practice-docs/skills/field-practice-docs/engine
uv run field-practice --help
```

Full local E2E:

```bash
~/plugins/field-practice-docs/scripts/ci_e2e.sh
```

## Requirements

- macOS or Linux shell
- Python 3.11+ via `uv`
- Node.js for HWP/HWPX render and rhwp tooling
- Optional: HOP for GUI review on macOS
- Optional: Hancom Office only when native `.hwp` save-as submission is forced

## Safety

User inputs and outputs should stay under a workspace run directory:

```text
field-practice-out/<run-id>/
  intake.json
  inputs/
  draft/
  document/
  qa/
  final/
  manifest.md
```

The plugin install directory should not contain user documents, generated
outputs, virtualenvs, caches, or `field-practice-out/`.
