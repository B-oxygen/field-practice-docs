# Pipeline — 증빙에서 보고서 생성 (engine)

`engine/`의 `field_practice` 패키지는 증빙을 통합해 주차별 활동보고서와 결과보고서 초안을 만든다.

## 설치 / 실행
```bash
cd engine
uv run field-practice --help          # 또는: uv run python -m field_practice.cli --help
uv run pytest -q                      # 52개 테스트
```

## 본인 정보 주입 (일반화 해제)
스킬은 플레이스홀더로 배포된다. 실제 사용 전 교체:
- `engine/configs/project.yaml` — name, department, student_id, company, registration_number, semester, period
- `engine/src/field_practice/config.py` — `STUDENT_NAME`, `DEPARTMENT`, `STUDENT_ID`, `COMPANY_NAME`, 기간/상한/타깃 상수

## 데이터 준비 (`data/` 직접 구성)
1. GitHub commits/PRs/issues export → `data/raw/github/`
2. Google Calendar export (기간) → `data/raw/calendar/`
3. aLog 일/주 근무기록 → `data/raw/alog/`
4. 로컬 git 이력: `uv run field-practice draft ingest-local-git --repo-root <repo> --since <YYYY-MM-DD> --until "<YYYY-MM-DD HH:MM:SS>" --out data/intermediate/...csv`

## 파이프라인
```bash
uv run field-practice draft run --scenario both --repo-root <repo> \
  --github data/raw/github --calendar data/raw/calendar/...csv \
  --alog data/raw/alog/alog_daily.csv --out reports
```
산출: `reports/weekly_report_{480,640}.csv`, `evidence_ledger.csv`, `validation_report.md`, `final_result_report_draft.md`.

## 주요 명령
- `doctor` — 현재 머신의 rhwp/HOP 상태와 선택 템플릿 파싱 점검
- `draft run` — 분류→시간배분→보고서
- `draft ingest-github` / `draft ingest-calendar` / `draft ingest-local-git` — 증빙 정규화
- `draft validate` — 주차 CSV ↔ 증빙 대조 (`validation_report.md`)
- `draft enrich-weekly` — 활동내역 문장 보강
- `document inspect` / `document fill` / `document cells` / `document export` — HWP/HWPX 출력 (→ `references/hwpx-editing.md`)

## 규칙 (engine이 강제)
- 모든 날짜 Asia/Seoul 정규화.
- 활동 행은 증빙 1개 이상 없으면 `needs_review=true`.
- `confidence=D` 증빙은 자동 제출 시나리오 제외.
- 일 600분 / 주 3,120분 상한.
- 목표 시간을 증빙으로 못 채우면 만들지 않고 `validation_report.md`에 부족분 기록.

## 시나리오
- `480` = 28,800분, `640` = 38,400분. `validation_report.md`를 먼저 검토하고 `needs_review` 행을 보완한 뒤 채택한다.
