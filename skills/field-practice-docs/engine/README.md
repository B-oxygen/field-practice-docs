# Field Practice Reconstructor

예시대학교 2026-1학기 창업현장실습 활동보고서 재구성을 위한 로컬 CLI입니다. GitHub 개발 이력, Google Calendar 내보내기, aLog 근무시간, 문서 템플릿을 증빙 원장으로 통합한 뒤 주차별 활동보고서와 최종 결과보고서 초안을 생성합니다.

## Workflow

1. Export GitHub commits, PRs, and issues.
2. Export Google Calendar events between 2026-03-02 and 2026-06-21.
3. Prepare aLog daily or weekly records.
4. Run the pipeline.
5. Review `validation_report.md`.
6. Edit entries marked `needs_review`.
7. Use `weekly_report_480.csv` first.
8. If evidence is sufficient, use `weekly_report_640.csv`.
9. Fill official HWPX form cells with `document fill` or `document cells`.
10. Open the filled HWPX in HOP, visually verify layout, then export PDF manually.

## Usage

Use an explicit run directory inside the working directory so inputs, drafts, document outputs, QA evidence, and final files stay together:

```bash
RUN_DIR="$PWD/field-practice-out/20260629-143000"
uv run ../scripts/init_run.py --root "$PWD" --run-id 20260629-143000
```

```bash
uv run python -m field_practice.cli draft run \
  --scenario both \
  --repo-root . \
  --github data/raw/github \
  --calendar data/raw/calendar/calendar_seed_events.csv \
  --alog data/raw/alog/alog_daily.csv \
  --alog-weekly data/raw/alog/alog_weekly_summary.csv \
  --alog-baselines data/raw/alog/alog_baselines.csv \
  --alog-fill-strategy data/raw/alog/alog_fill_strategy.csv \
  --out "$RUN_DIR/draft"
```

```bash
uv run python -m field_practice.cli draft ingest-local-git \
  --repo-root . \
  --since 2026-03-02 \
  --until "2026-06-21 23:59:59" \
  --out data/intermediate/github_local_evidence.csv

uv run python -m field_practice.cli draft ingest-github \
  --input data/raw/github \
  --out data/intermediate/github_evidence.csv

uv run python -m field_practice.cli draft ingest-calendar \
  --input data/raw/calendar/calendar_events_2026-1.csv \
  --out data/intermediate/calendar_evidence.csv

uv run python -m field_practice.cli draft validate \
  --weekly reports/weekly_report_640.csv \
  --evidence reports/evidence_ledger.csv \
  --out reports/validation_report.md
```

```bash
uv run field-practice document cells \
  --template official_form.hwpx \
  --cells cells.json \
  --out filled_form.hwpx
```

```bash
uv run field-practice document render --input filled_form.hwpx --out page0.svg
uv run field-practice document blank --input filled_form.hwpx --out blank.hwpx --keep keep.json
uv run --with pymupdf field-practice document clean-pdf --input submitted.pdf --out-dir clean-pdf
```

## Evidence Rules

- 모든 날짜는 Asia/Seoul 기준으로 정규화됩니다.
- 활동 행은 최소 하나 이상의 증빙을 가져야 하며, 그렇지 않으면 `needs_review=true`로 남습니다.
- `confidence=D` 증빙은 자동 제출 시나리오에 사용하지 않습니다.
- 일일 600분, 주간 3,120분 상한을 초과하지 않습니다.
- 증빙으로 목표 시간을 채울 수 없으면 시간을 만들지 않고 `validation_report.md`에 부족분을 기록합니다.
- 모든 출력 학번은 `0000000000`로 통일됩니다.
