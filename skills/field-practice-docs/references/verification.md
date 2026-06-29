# 검증 (Verification)

제출 전 산출물이 정본과 일치하고 누락이 없는지 자동·수동으로 확인한다.

## 검증 harness 패턴
케이스별 기대값을 코드에 고정하고 CLI로 체크하는 방식(이번 세션 `supplement_verify.py` 패턴):
- `@dataclass(frozen=True, slots=True)`로 기대 사실(주차·일자·분) 정의.
- 산출 문서에서 마커/합계를 추출해 기대값과 대조, 불일치 시 `VerificationError`.
- `--check <name> --output <evidence.txt>` 형태로 체크별 증거 파일 출력.
- 문자열 마커 검사는 **공백에 강건**하게(표 정렬 패딩으로 깨지지 않도록 `re.sub(r" +"," ", text)` 정규화).

## 게이트 (코드 변경 시)
```bash
python -m py_compile scripts/*.py            # 구문
node --check scripts/hwp_rhwp.mjs scripts/hwp_render.mjs
cd engine && uv run pytest -q                 # 엔진 동작(51 tests)
uv run basedpyright / ruff check (엔진 설정)   # 타입/린트(strict)
```

## 핵심 원칙
- **최종 산출물 기준 검증.** 중간 in-memory 통과를 믿지 말 것 — 디스크의 개별 파일 개수·고유 파일명·합계를 확인. (이번 세션: 파일명 파싱 실패로 11개가 1개로 덮어써졌는데 in-memory 검증은 통과했었음.)
- **수치 독립 재계산.** 핸드오프/생성기가 준 합계를 그대로 믿지 말고 원문에서 재추출해 합산(예: 근무시간 분 합 = 정본 합).
- **사실 날조 금지.** 검증을 통과시키려 하드코딩/특수처리하지 않는다.
- **사람이 직접 사용해 확인.** HWP/HWPX는 가능한 시각 표면(HOP, `hwp_render.mjs` PNG, 또는 PDF 변환본)으로, PDF는 Preview/브라우저로 열어 레이아웃·서명·날인을 눈으로 본다. "should work"는 검증이 아니다.
- **좌표 채움은 재추출 + 렌더로 확인.** `field-practice document cells` 사용 후 `hwpx_extract.py`로 입력값이 해당 파일에 남았는지 확인하고, `hwp_render.mjs`/HOP에서 셀 밀림과 스타일 상속(파란/빨간 글자)을 본다.
- **HOP 창이 안 보이면 위치부터 확인.** `System Events`로 HOP window count/position을 읽고, 외장 모니터나 다른 Space에 있으면 내장 화면으로 옮긴다. 그래도 창이 없으면 `hwp_render.mjs`와 QuickLook PNG에서 한글 본문/표/빈칸을 본다. 네이티브 `.hwp`가 강제되는 경우에만 한컴 Save As 검증을 별도 선택 단계로 둔다.
- **PDF를 최종 시각 고정본으로 검수.** HOP export가 가능하면 HOP `File > Export PDF...`를 쓰고, HOP GUI가 막히면 렌더/별도 변환 경로로 만든 PDF를 PDF 뷰어에서 확인한다. AppleScript save panel 자동화는 불안정하므로 파일 생성까지 자동 보장하지 않는다. 제출처가 HWP/HWPX를 요구하면 원본도 보존한다.
- **렌더 PNG smoke test와 제출 품질을 분리.** synthetic HWPX에서 글자가 한 줄로 뭉쳐 보여도 엔진 smoke test는 통과일 수 있다. 실제 품질 판정은 원본 양식 파일 또는 PDF export 기준이다.
- **macOS BSD grep**: 검증 스크립트/명령은 `grep -nE`로 작성(rg 가정 금지).

## 제출 전 최종 체크리스트
- [ ] 보고서 합계 = 정본(제출리스트) 합계
- [ ] 외부근무사유서 합계 = 제출리스트 1~2쪽 합계, 주차별 날짜=일요일
- [ ] 제출 PDF에 메모 0건, 폼 내용 보존
- [ ] (디슬롭 시) 사실보존 게이트 통과 + 전수 정독
- [ ] 개인정보(학번·이름·사업자번호) 의도치 않은 노출 없음
- [ ] HOP 또는 렌더 PNG/PDF에서 줄 넘침/페이지/서명 확인
- [ ] 좌표 채움 산출물은 재추출 grep + 렌더 PNG/HOP 중 가능한 표면으로 셀 위치와 글자색 확인
- [ ] HOP 창이 안 보이면 `System Events`로 window count/position 확인 후 화면 안으로 이동
- [ ] PDF final을 만들고 PDF 뷰어에서 레이아웃/페이지/메모 0건 확인
- [ ] 네이티브 `.hwp` 강제 제출일 때만 한컴 앱에서 열고 `.hwp`로 다른 이름 저장
- [ ] 현재 세션에서 스킬이 안 보이면 `~/.codex/skills/field-practice-docs` 노출 여부 확인 후 새 세션에서 재확인
