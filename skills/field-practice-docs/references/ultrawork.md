# Ultrawork 운영 기준

`doctor`, `draft`, `document` 모두 같은 실행 규칙을 따른다.

## 시작
- 목표를 한 문장으로 고정한다.
- 성공 기준을 2~4개로 둔다: happy path, 위험한 edge, 실제 표면 검증.
- 먼저 물을 정보는 최대 3개다. 파일 경로, 최종 형식, 검수 가능 여부가 우선이다.
- `references/io-contract.md`에 따라 사용자가 지정한 작업 디렉토리 안에 run directory를 정하고 `intake.json`, `inputs/`, `draft/`, `document/`, `qa/`, `final/`, `manifest.md` 중 필요한 경로를 먼저 잡는다. 새 실행은 가능하면 `scripts/init_run.py`로 시작한다.

## RED → GREEN
- 문서/설정 변경이면 grep 또는 JSON 검증으로 현재 빠진 항목을 먼저 증명한다.
- 코드 변경이면 가장 좁은 테스트나 CLI 실패를 먼저 잡는다.
- 구현 후 같은 명령이 통과해야 한다.

## 실제 표면
- `doctor`: `field-practice --help`, HOP/rhwp 상태, 템플릿 파싱 결과.
- `draft`: 생성된 CSV/Markdown 파일과 검증 리포트.
- `document`: `hwpx_extract.py` 재추출, `hwp_render.mjs` PNG, HOP 창 또는 PDF 뷰어.

## 종료
- 임시 GUI sheet, dev server, tmux/session, 큰 임시 venv는 닫거나 제거한다.
- 최종 답변에는 `manifest.md` 또는 동일한 수준의 산출물 경로와 통과한 검증만 쓴다.
- 한컴 없는 경로는 PDF final을 기본으로 하고, 네이티브 `.hwp`는 선택 검증으로 분리한다.
