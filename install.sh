#!/usr/bin/env bash
set -euo pipefail

PLUGIN_NAME="field-practice-docs"
SOURCE="${1:-}"
PLUGIN_HOME="${PLUGIN_HOME:-$HOME/plugins}"
PLUGIN_DIR="$PLUGIN_HOME/$PLUGIN_NAME"
MARKETPLACE="${MARKETPLACE:-$HOME/.agents/plugins/marketplace.json}"
CLAUDE_SKILL="$HOME/.claude/skills/$PLUGIN_NAME"
CODEX_SKILL="$HOME/.codex/skills/$PLUGIN_NAME"

need() {
  command -v "$1" >/dev/null 2>&1 || {
    printf '%s\n' "missing required command: $1" >&2
    exit 69
  }
}

backup_path() {
  printf '%s.backup-%s\n' "$1" "$(date -u +%Y%m%d%H%M%S)"
}

link_skill() {
  src="$1"
  dest="$2"
  mkdir -p "$(dirname "$dest")"
  if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$src" ]; then
    return
  fi
  if [ -e "$dest" ] || [ -L "$dest" ]; then
    mv "$dest" "$(backup_path "$dest")"
  fi
  ln -s "$src" "$dest"
}

install_from_local() {
  source_dir="$1"
  need rsync
  mkdir -p "$PLUGIN_HOME"
  rsync -a --delete \
    --exclude '.git/' \
    --exclude '.venv/' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '.pytest_cache/' \
    --exclude '.ruff_cache/' \
    --exclude 'field-practice-out/' \
    "$source_dir/" "$PLUGIN_DIR/"
}

install_from_git() {
  source_url="$1"
  need git
  mkdir -p "$PLUGIN_HOME"
  if [ -d "$PLUGIN_DIR/.git" ]; then
    git -C "$PLUGIN_DIR" pull --ff-only
    return
  fi
  if [ -e "$PLUGIN_DIR" ]; then
    printf '%s\n' "destination exists and is not a git checkout: $PLUGIN_DIR" >&2
    printf '%s\n' "move it aside or set PLUGIN_HOME to another directory" >&2
    exit 73
  fi
  git clone "$source_url" "$PLUGIN_DIR"
}

write_marketplace() {
  mkdir -p "$(dirname "$MARKETPLACE")"
  MARKETPLACE="$MARKETPLACE" python3 - <<'PY'
from __future__ import annotations

import json
import os
from pathlib import Path

marketplace = Path(os.environ["MARKETPLACE"])
entry = {
    "name": "field-practice-docs",
    "source": {"source": "local", "path": "./plugins/field-practice-docs"},
    "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
    "category": "Productivity",
}
if marketplace.exists():
    data = json.loads(marketplace.read_text(encoding="utf-8"))
else:
    data = {"name": "personal", "interface": {"displayName": "Personal"}, "plugins": []}
plugins = [p for p in data.get("plugins", []) if p.get("name") != entry["name"]]
plugins.append(entry)
data["plugins"] = plugins
data.setdefault("name", "personal")
data.setdefault("interface", {}).setdefault("displayName", "Personal")
marketplace.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
}

install_node_deps() {
  if command -v npm >/dev/null 2>&1; then
    (cd "$PLUGIN_DIR/skills/$PLUGIN_NAME" && npm ci --omit=dev --ignore-scripts >/dev/null)
  fi
}

if [ -z "$SOURCE" ]; then
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [ -f "$script_dir/.codex-plugin/plugin.json" ]; then
    SOURCE="$script_dir"
  else
    printf '%s\n' "usage: install.sh <git-url-or-local-plugin-dir>" >&2
    exit 64
  fi
fi

need python3
if [ -d "$SOURCE/.codex-plugin" ]; then
  install_from_local "$SOURCE"
else
  install_from_git "$SOURCE"
fi

write_marketplace
link_skill "$PLUGIN_DIR/skills/$PLUGIN_NAME" "$CLAUDE_SKILL"
link_skill "$CLAUDE_SKILL" "$CODEX_SKILL"
install_node_deps

printf '%s\n' "installed $PLUGIN_NAME"
printf '%s\n' "plugin: $PLUGIN_DIR"
printf '%s\n' "marketplace: $MARKETPLACE"
printf '%s\n' "restart Codex or Claude to refresh the skill/plugin registry"
