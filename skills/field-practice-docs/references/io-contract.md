# Input/Output 관리 계약

플러그인은 원본을 수정하지 않고, 모든 입력/출력을 사용자가 지정한 작업 디렉토리 안에서 관리한다. 사용자가 작업 루트나 `out_dir`를 주면 그 경로를 쓰고, 없으면 에이전트가 실행되는 현재 workspace directory를 작업 루트로 본다. run directory는 항상 그 작업 루트 아래 `field-practice-out/<YYYYMMDD-HHMMSS>/`로 만든다. 플러그인/스킬 설치 디렉토리에는 산출물을 만들지 않는다. CLI를 직접 호출할 때도 가능한 한 `--out`/`--out-dir`/`--output`을 명시한다.

새 실행은 번들 initializer로 시작한다.

```bash
uv run scripts/init_run.py --root "$PWD"
```

출력된 run directory를 이후 모든 `--out`, `--out-dir`, `--output`의 부모로 쓴다.

## Intake
처음에 묻는 값은 최대 3개다. 이미 제공된 값은 다시 묻지 않는다.

| Command | 필수 입력 | 없으면 기본값 |
|---|---|---|
| `doctor` | 템플릿 경로, 최종 제출 형식, HOP/PDF 검수 가능 여부 | 템플릿 없이는 환경 점검만 실행 |
| `draft` | 대상 기간, 증빙 위치(git/calendar/alog), 목표 시나리오 | 기간은 config 값, 시나리오는 `both` |
| `document` | 템플릿/입력 파일, 초안/CSV 경로, 최종 형식 | PDF final + HWPX 원본 보존 |

개인정보는 대화에 길게 붙이지 않고 config/placeholder 파일로 주입한다. 제출 전에는 산출물 기준으로 PII scan을 수행한다.

## Directory Layout
권장 작업 루트와 run directory:

```text
<workspace-or-user-root>/
  field-practice-out/
    <run-id>/
      intake.json          # 사용자가 준 경로/형식/검수 가능 여부
      inputs/              # 복사본 또는 symlink, 원본은 수정 금지
      draft/               # CSV/Markdown 초안
      document/            # filled/blank HWPX, mapping CSV
      qa/                  # extract txt, render svg/png, validation reports
      final/               # 제출 후보 PDF/HWPX/HWP
      manifest.md          # 무엇을 만들었고 무엇을 검증했는지
```

현재 engine 기본값은 `reports/`이므로, 에이전트가 실행할 때는 `--out <run-dir>/draft` 또는 `--out <run-dir>/document`처럼 명시해서 흩어지지 않게 한다.

## Inputs
- 원본 템플릿: `inputs/templates/` 아래에 보관하거나 원본 경로를 `intake.json`에 기록한다.
- 증빙: git/calendar/alog 원본은 `inputs/evidence/` 또는 외부 경로로 두고, 정규화 결과만 `draft/`에 쓴다.
- 설정: 이름, 학번, 사업자번호 같은 PII는 config/placeholder로 주입한다. 채팅 본문에 전체 원문을 붙이지 않는다.
- 수동 보완: 사람이 수정한 파일은 `inputs/manual/`에 별도 파일로 저장하고 자동 산출물 위에 덮어쓰지 않는다.
- 외부 파일을 참조할 때도 최종 산출물과 검증 증거는 작업 루트 내부 run directory에 만든다.

## Outputs
`draft` 산출물:
- `weekly_report_<scenario>.csv`
- `weekly_report_<scenario>.md`
- `evidence_ledger.csv`
- `time_ledger.csv`
- `validation_report.md`
- `monthly_report_draft.md`
- `final_result_report_draft.md`

`document` 산출물:
- filled HWPX/HWPX source
- `weekly_cell_mapping.csv`, `final_cell_mapping.csv`
- `direct_fill_validation.md`
- blank HWPX
- rendered SVG/PNG
- cleaned PDF

`final` 산출물:
- 제출 후보 파일만 둔다.
- PDF가 기본 final이다. 제출처가 HWP/HWPX를 요구하면 같은 run의 HWPX도 보존한다.
- 네이티브 `.hwp`는 한컴 Save As가 가능한 경우에만 final로 승격한다.

## Manifest
작업 종료 시 `manifest.md` 또는 최종 답변에 아래 항목을 남긴다.

```text
run_id:
inputs:
  templates:
  evidence:
outputs:
  draft:
  document:
  final:
verification:
  cli:
  extract:
  render:
  pdf:
not_verified:
  - Hancom Save As .hwp (Hancom not installed)
```

## Retention
- run directory는 사용자가 제출/보관 여부를 판단할 때까지 유지한다.
- `/tmp`는 CI/E2E 임시 검증에만 쓴다. 사용자 작업 산출물은 작업 루트 내부 run directory에 다시 생성한다.
- 패키지/스킬 설치 디렉토리에는 `.venv`, `.pytest_cache`, `.ruff_cache`, `__pycache__`, `*.pyc`, 대용량 E2E 산출물, 사용자 입력/출력물을 남기지 않는다.

## Failure Handling
- 원본 파일은 절대 덮어쓰지 않는다.
- 실패한 단계도 stdout/stderr와 부분 산출물 경로를 `qa/`에 남긴다.
- HOP GUI가 안 뜨면 HOP 상태, rhwp render SVG, QuickLook PNG를 대체 검증으로 기록한다.
- 한컴이 없으면 `.hwp` final은 `not_verified`에 남기고 PDF/HWPX 경로를 완결한다.
