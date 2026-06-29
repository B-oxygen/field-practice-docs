---
name: field-practice-docs
description: >-
  한국 대학/기관 제출용 HWP·HWPX·PDF 문서 자동화 end-to-end 플레이북 (동국대 창업현장실습/창업대체학점
  인정제 기준). 증빙(git/alog/calendar)→주차별·결과 보고서 생성, HWPX 텍스트 추출/치환, HWP 양식 채우기,
  외부근무사유서 주차별 작성, 제출 PDF 메모(코멘트) 제거, AI 문체 디슬롭, 제출 검증을 다룬다. Triggers:
  창업현장실습, 주차별활동보고서, 결과보고서, 외부근무사유서, HWP/HWPX 편집, 한글 문서 자동화, PDF 메모 제거,
  보고서 디슬롭, field practice report, 근무시간 보완.
---

# Field Practice Docs — 한국 대학 제출서류 자동화 플레이북

증빙 데이터에서 대학 제출 보고서를 만들고, HWP 양식을 채우고, 제출 전 정리(메모 제거·문체 디슬롭)·검증하는 end-to-end 워크플로. 동국대 창업현장실습이 기준 예시지만 다른 주차형 보고서/제출서류에 일반적으로 적용된다.

## 언제 쓰나
- 주차별활동보고서·결과보고서·외부근무사유서 작성/보완
- HWPX 텍스트 추출·치환, HWP 양식 채우기
- 채워진 HWP를 빈 양식(템플릿)으로 만들기(블랭킹), HOP으로 보기·사람 검수
- 제출 PDF에서 메모(코멘트) 제거
- AI가 쓴 듯한 보고서 문체를 사람 글로 디슬롭
- git/alog/calendar 증빙 → 근무시간 배분 → 보고서 초안

## 구성
- `engine/` — `field_practice` 파이썬 패키지(증빙→보고서→HWPX). CLI는 `doctor` / `draft` / `document` 3개 top-level 명령만 노출한다. 개인정보는 플레이스홀더로 일반화됨(`engine/configs/project.yaml`, `engine/src/field_practice/config.py`에서 본인 값으로 교체).
- `scripts/` — 의존성 가벼운 standalone 유틸(아래 표). `init_run.py`는 작업 디렉터리 내부 I/O 구조를 만드는 내부 도구다.
- `references/` — 단계별 상세 가이드.

## Public Commands
사용자에게는 세 가지 작업만 노출한다. 기존 엔진/스크립트 명령은 내부 구현 세부사항으로 라우팅한다.

| Command | 사용자 질문 | 포함 범위 |
|---|---|---|
| `doctor` | “이 머신/양식으로 지금 가능한가?” | HOP/rhwp/Node/Python/한컴 선택 여부, 템플릿 파싱, registry 노출 |
| `draft` | “보고서에 무엇을 쓸까?” | git/calendar/alog 증빙 수집, 시간 배분, 주차별·결과보고서 초안, 디슬롭 |
| `document` | “제출 파일을 만들고 검증하자” | HWP/HWPX 채움, 빈 양식 생성, 렌더/HOP/PDF 검수, PDF 메모 제거, 최종 체크 |

`document` 하위 의도는 필요할 때만 구분한다: `inspect`, `fill`, `cells`, `export`, `blank`, `render`, `clean-pdf`. top-level command로는 늘 `document`라고 부른다.

## 초기 정보 Intake
작업 시작 직후 필요한 정보만 묻는다. 사용자가 이미 제공한 값은 다시 묻지 않는다.

| Command | 먼저 확인할 최소 정보 |
|---|---|
| `doctor` | OS, HOP 설치 여부, 템플릿 경로, 최종 제출 형식(PDF/HWPX/HWP) |
| `draft` | 대상 기간, 목표 시나리오(480/640), 증빙 위치(git/calendar/alog), 부족 시간 허용 여부 |
| `document` | 입력 파일/템플릿 경로, 산출 디렉터리, 최종 형식, 사람 검수 가능 여부(HOP/PDF) |

질문은 최대 3개로 묶고, 답이 없어도 안전한 기본값이 있으면 그 기본값으로 진행한다. 개인정보는 config/placeholder로 주입하고 대화에 원문을 길게 붙이지 않는다.

## I/O 관리
원본은 읽기 전용으로 두고, 모든 입력/출력은 사용자가 지정한 작업 디렉토리 안에서 관리한다. 별도 지정이 없으면 에이전트가 실행되는 현재 workspace directory를 작업 루트로 보고, 그 아래 `field-practice-out/<YYYYMMDD-HHMMSS>/`를 사용한다. 플러그인/스킬 설치 디렉토리에는 산출물을 만들지 않는다.

권장 구조는 `intake.json`, `inputs/`, `draft/`, `document/`, `qa/`, `final/`, `manifest.md`다. CLI 실행 시 `--out`, `--out-dir`, `--output`을 명시해서 engine 기본 `reports/`에 산출물이 흩어지지 않게 한다. 자세한 입력/출력/보관 규칙은 `references/io-contract.md`를 따른다.

내부 도구:

```bash
uv run scripts/init_run.py --root "$PWD"
```

이 명령은 `$PWD/field-practice-out/<run-id>/` 아래 표준 구조를 만들고 run directory 경로를 출력한다. 에이전트는 이후 `--out` 계열 옵션을 이 run directory 하위로 고정한다.

## Ultrawork 실행 모드
사용자가 “ultrawork”, “끝까지 검증”, “prod 수준”, “제출 가능하게”라고 말하면 evidence-driven으로 진행한다.

1. 시작 시 목표와 성공 기준을 고정한다.
2. 가능한 가장 싼 RED proof를 먼저 잡는다(예: grep/test/CLI가 현재 실패함).
3. 구현 후 GREEN proof를 기록한다.
4. 실제 표면을 반드시 한 번 통과시킨다: CLI stdout, HOP/렌더 PNG, PDF 뷰어, 또는 파일 재추출.
5. 최종 답변에는 산출물 경로, 검증 명령, 통과/미검증 항목을 짧게 남긴다.

자세한 기준은 `references/ultrawork.md`를 따른다.

## 노출/호출
- Claude/OpenCode 경로: `~/.claude/skills/field-practice-docs`.
- Codex 경로: `~/.codex/skills/field-practice-docs`가 필요하다. 원본 중복을 피하려면 Claude 경로로 symlink한다.
- 스킬 registry는 세션 시작 시점 스냅샷일 수 있다. 파일이 유효해도 현재 세션에 안 보이면 새 세션/재시작에서 확인한다.

## 워크플로 & 라우팅
| 단계 | 무엇 | 참조 / 도구 |
|---|---|---|
| 1 | 증빙→보고서 생성 | `references/pipeline.md` · `engine` CLI |
| 2 | HWP/HWPX 편집 | `references/hwpx-editing.md` · `scripts/hwpx_extract.py`, `hwpx_replace.py`, `hwp_rhwp.mjs`, engine `document cells` |
| 3 | 외부근무사유서 | `references/external-work-reason.md` |
| 4 | 제출 PDF 메모 제거 | `references/pdf-memo-removal.md` · `scripts/pdf_remove_memos.py` |
| 5 | 디슬롭(AI 문체 제거) | `references/deslop.md` · `scripts/deslop_analyze.py`, `verify_fact_preservation.py` |
| 6 | 제출 검증 | `references/verification.md` |
| 7 | 양식 만들기·HOP 검수 | `references/blanking-review-hop.md` · `scripts/blank_form.py`, `hwp_render.mjs` |
| 8 | 입력/출력 관리 | `references/io-contract.md` |

## 스크립트 빠른 참조
| 스크립트 | 용도 | 의존성 |
|---|---|---|
| `hwpx_extract.py` | HWPX 문단 텍스트 추출 | stdlib |
| `hwpx_replace.py` | HWPX 텍스트 치환 + 올바른 재패키징 | stdlib |
| `hwp_rhwp.mjs` | 바이너리 .hwp/.hwpx 읽기·치환·변환(rhwp) | Node + `@rhwp/core` |
| `blank_form.py` | 채워진 HWP→빈 양식(화이트리스트 블랭킹+이미지 strip) | stdlib |
| `hwp_render.mjs` | 페이지→SVG 렌더(시각 QA, HOP과 동일 엔진) | Node + `@rhwp/core` |
| `pdf_remove_memos.py` | PDF 메모/주석 제거 | pymupdf (`uv run --with pymupdf`) |
| `deslop_analyze.py` | AI 문체 정량 분석 + risk band(im-not-ai 신호) | stdlib |
| `verify_fact_preservation.py` | 디슬롭 사실보존 게이트 | stdlib |
| `init_run.py` | 작업 디렉터리 내부 표준 I/O 구조 생성 | stdlib |

엔진: `cd engine && uv run field-practice --help`

## 불변 원칙 (CRITICAL)
- **사실/시간 날조 금지.** 증빙으로 못 채우면 시간을 만들지 말고 부족분으로 기록한다.
- **상한**: 일 600분, 주 3,120분.
- **HWPX = zip + XML.** 재패키징 시 `mimetype`이 첫 항목이고 STORED(무압축)여야 한글이 연다 — `hwpx_replace.py`/engine writer가 처리.
- **빈 셀 양식 채움은 좌표 매핑.** 실제 동국대 양식처럼 빈 칸이 `<hp:t></hp:t>`이면 `replaceAll`로는 못 채운다. `engine`의 `document cells`로 `section_path/table_index/row_index/cell_index/text/char_pr_id`를 명시하고, HOP/렌더 PNG로 스타일 상속(파란/빨간 글자)을 확인한다.
- **시각 검증은 필수, HOP은 선호 옵션**이다. 가능하면 `brew install --cask hop` 후 `open -a HOP file.hwpx`로 레이아웃(linesegarray reflow)을 눈으로 확인하고 PDF를 만든다. HOP 프로세스가 떠도 문서 창이 안 보이면 외장 모니터/Space 쪽 열린 창을 `osascript`로 확인·이동한다. 그래도 안 되면 `hwp_render.mjs` + QuickLook PNG/PDF 뷰어 검수로 대체한다.
- **디슬롭은 사실 100% 보존**(영문·숫자·고유명사). 반드시 `verify_fact_preservation.py`로 게이트.
- **바이너리 HWP**: soffice 불가. 가벼운 추출은 `pyhwp`, 프로그램 읽기/편집/쓰기·`.hwp↔.hwpx` 변환은 `scripts/hwp_rhwp.mjs`(`@rhwp/core`, 검증됨).
- **한컴은 선택 옵션**이다. 제출처가 네이티브 `.hwp`를 강제할 때만 한컴에서 열어 "다른 이름으로 저장"한다. 일반 검수·보관·공유·PDF 제출은 한컴 없이 HOP/PDF 경로로 끝낸다. rhwp/HOP의 `.hwp` 쓰기는 한컴 규격과 안 맞을 수 있음(hop #73); LibreOffice+H2Orestart는 import 전용.
- **mac 미리보기·검수 = HOP 또는 렌더 PNG/PDF** (`brew install --cask hop` → `open -a HOP file`; 창이 안 보이면 외장 모니터/Space 위치 확인; 실패 시 `hwp_render.mjs` → `qlmanage`). 자동 블랭킹/채움 후엔 HOP 또는 렌더 PNG/PDF로 띄워 **사람이 부족분 수정**(human-in-the-loop) — 토큰 단위 자동검증은 레이아웃·뉘앙스를 못 잡음.
- **PDF가 기본 최종본**이다. 제출처가 HWP/HWPX를 요구하면 원본도 보존하되, 검수·보관·공유용 final은 가능한 시각 경로(HOP export, 렌더 기반 PDF, 또는 별도 PDF 변환)를 눈으로 확인한다. 한컴 PDF export는 선택 옵션이다.
- **macOS 기본 grep은 BSD** — `grep -nE` 사용. `rg` 설치 가정 금지.
- **검증은 최종 산출물(디스크의 개별 파일·개수) 기준**으로. 중간 in-memory 통과만 믿지 말 것.
- **개인정보**: 이 스킬은 일반화돼 있다. 사용 시 config로 본인 정보를 주입하고, 산출물에 학번·이름·사업자번호 등이 노출되지 않게 확인한다.
