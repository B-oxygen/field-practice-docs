#!/usr/bin/env bash
set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_ROOT="$PLUGIN_ROOT/skills/field-practice-docs"
ENGINE_ROOT="$SKILL_ROOT/engine"
WORKSPACE_ROOT="${FIELD_PRACTICE_E2E_ROOT:-$PWD}"
RUN_ID="${FIELD_PRACTICE_E2E_RUN_ID:-ci-e2e-$(date -u +%Y%m%d-%H%M%S)}"
RUN_DIR="$WORKSPACE_ROOT/field-practice-out/$RUN_ID"
QA_DIR="$RUN_DIR/qa"
export UV_PROJECT_ENVIRONMENT="$QA_DIR/uv-venv"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPYCACHEPREFIX="$QA_DIR/pycache"
export RUFF_CACHE_DIR="$QA_DIR/ruff-cache"

uv run "$SKILL_ROOT/scripts/init_run.py" --root "$WORKSPACE_ROOT" --run-id "$RUN_ID" --json > /tmp/field-practice-ci-layout.json
mkdir -p "$QA_DIR"
cp /tmp/field-practice-ci-layout.json "$QA_DIR/layout.json"

python3 "$HOME/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py" "$PLUGIN_ROOT" \
  > "$QA_DIR/plugin-validate.log"
python3 "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" "$SKILL_ROOT" \
  > "$QA_DIR/skill-validate.log"

python3 -m py_compile "$SKILL_ROOT"/scripts/*.py "$ENGINE_ROOT"/src/field_practice/*.py
node --check "$SKILL_ROOT/scripts/hwp_rhwp.mjs" "$SKILL_ROOT/scripts/hwp_render.mjs"

(
  cd "$ENGINE_ROOT"
  uv run field-practice --help > "$QA_DIR/field-practice-help.txt"
  uv run field-practice document --help > "$QA_DIR/field-practice-document-help.txt"
  if uv run field-practice run --help > "$QA_DIR/field-practice-run-help.txt" 2>&1; then
    echo "legacy top-level command unexpectedly succeeded" >&2
    exit 1
  fi
  grep -q "No such command 'run'" "$QA_DIR/field-practice-run-help.txt"
  uv run pytest -q -p no:cacheprovider > "$QA_DIR/pytest.log"
  uv run ruff check --no-cache src tests > "$QA_DIR/ruff.log"
  uv run basedpyright src tests > "$QA_DIR/basedpyright.log"
)

TEMPLATE_DIR="${FIELD_PRACTICE_TEMPLATE_DIR:-$HOME/Downloads/field-practice-templates}"
if [[ -d "$TEMPLATE_DIR" ]]; then
  templates=()
  while IFS= read -r template; do
    templates+=("$template")
  done < <(find "$TEMPLATE_DIR" -maxdepth 1 -type f \( -name '*.hwpx' -o -name '*.hwp' \) | sort | head -2)
  if [[ "${#templates[@]}" -eq 2 ]]; then
    (
      cd "$ENGINE_ROOT"
      uv run field-practice doctor \
        --weekly-template "${templates[0]}" \
        --final-template "${templates[1]}" \
        --out "$QA_DIR/doctor-real-template" \
        > "$QA_DIR/doctor-real-template.log"
    )
  fi
  if [[ "${#templates[@]}" -ge 1 ]]; then
    (
      cd "$ENGINE_ROOT"
      uv run field-practice document render \
        --input "${templates[0]}" \
        --out "$QA_DIR/render-real-page0.svg" \
        > "$QA_DIR/render-real-page0.log"
    )
    if command -v qlmanage >/dev/null 2>&1; then
      qlmanage -t -s 1200 -o "$QA_DIR" "$QA_DIR/render-real-page0.svg" \
        > "$QA_DIR/render-real-page0-png.log" 2>&1
    fi
  fi
fi

if find "$PLUGIN_ROOT" -path '*/field-practice-out/*' -print -quit | grep -q .; then
  echo "field-practice output leaked into plugin install directory" >&2
  exit 1
fi

cat > "$RUN_DIR/manifest.md" <<EOF
# Field Practice CI E2E

- plugin_validate: qa/plugin-validate.log
- skill_validate: qa/skill-validate.log
- cli_help: qa/field-practice-help.txt
- pytest: qa/pytest.log
- ruff: qa/ruff.log
- basedpyright: qa/basedpyright.log
- render_fallback: qa/render-real-page0.svg
EOF

printf 'PASS %s\n' "$RUN_DIR"
