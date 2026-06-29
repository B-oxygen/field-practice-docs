# 양식 만들기 · HOP 미리보기 · PDF final · 사람 검수

채워진 HWP를 **빈 양식(템플릿)**으로 만들고, mac에서 가능한 시각 표면(**HOP**, 렌더 PNG, PDF 뷰어)으로 **사람이 검수·수정**한 뒤, 기본 최종본은 **PDF**로 고정하는 흐름. 한컴은 네이티브 `.hwp` 제출이 강제될 때만 쓰는 선택 옵션이다.

## 1. 양식 만들기 (채워진 HWP → 빈 양식)
**화이트리스트** 방식: 구조(제목·라벨·표 헤더·날짜 골격)만 남기고 나머지 전부 비운다. 개인정보 누락 위험 0(블랙리스트와 반대).

1. 바이너리 `.hwp`면 먼저 HWPX로:
   ```bash
   node scripts/hwp_rhwp.mjs form.hwp form.hwpx
   ```
2. 텍스트 추출해 구조 파악(무엇이 라벨이고 무엇이 데이터인지):
   ```bash
   python scripts/hwpx_extract.py form.hwpx --out form.txt
   ```
3. keep 설정 작성 — **구조만** KEEP:
   ```json
   {
     "exact": ["예시 양식 제목", "성명", "학번", "주차", "날짜", "활동내역", "□ 법인등록 완료"],
     "regex": ["^○", "^\\d+주$", "^\\d{2}/\\d{1,2}/\\d{1,2}$", "\\(인\\)\\s*$"],
     "transform": [["v 법인등록 완료", "□ 법인등록 완료"], ["홍길동", ""]]
   }
   ```
   - `exact`: 그대로 둘 라벨/헤더(전체 일치)
   - `regex`: 날짜·주차·섹션헤더(`○…`)·서명란(`…(인)`) 등 패턴
   - `transform`: KEEP 라인에 박힌 이름 부분 제거, 체크박스 `v`→`□` 초기화 등(먼저 적용됨). 변환 후 남길 문자열은 `exact` 또는 `regex`에도 포함해야 한다.
4. 블랭킹 + 스캔 이미지(증명서 등 PII) 제거:
   ```bash
   python scripts/blank_form.py form.hwpx blank.hwpx --keep keep.json --blank-images-over 300000
   ```
   - `--blank-images-over 300000`: 300KB 넘는 `BinData` 이미지를 1x1 투명으로 교체(사업자등록증 스캔 같은 PII 이미지 제거). 작은 로고/배너는 유지.
5. 검증 — 추출해서 PII 0 + 구조 유지 확인:
   ```bash
   python scripts/hwpx_extract.py blank.hwpx | grep -nE "<지운 이름>|<학번>|<사업자번호>"   # 0 이어야 함
   python scripts/hwpx_extract.py blank.hwpx | grep -nE "성명|주차|활동내역"                  # 라벨 살아있어야 함
   ```

## 2. HOP으로 보여주기 (mac, 한컴 없이)
**HOP**(golbin/hop)은 rhwp 엔진 기반 GUI라, rhwp/엔진이 만든 HWP/HWPX를 **그대로 정확히 렌더**한다(한컴 보안게이트 없음, 검증됨).
```bash
brew install --cask hop          # 1회
open -a HOP blank.hwpx           # 띄우기 (.hwp/.hwpx 모두)
```
- 엔진에선 `field_practice.rhwp_backend.hop_status()`(설치확인) / `open_in_hop(path)`(실행).
- 빈 양식·중간 산출물을 **눈으로 확인**하고 가볍게 손보는 데 최적.
- mac 환경에 따라 HOP 프로세스와 recent-doc 로그는 생기지만 문서 창이 안 보일 수 있다. 먼저 외장 모니터/다른 Space/저장된 window-state를 확인한다.

창 확인/강제 이동:
```bash
osascript -e 'tell application "System Events" to tell process "HOP" to get {frontmost, count of windows, name of windows}'
osascript -e 'tell application "HOP" to activate'
osascript -e 'tell application "System Events" to tell process "HOP" to tell window 1 to set position to {120, 120}'
osascript -e 'tell application "System Events" to tell process "HOP" to tell window 1 to set size to {1100, 760}'
```

“프로세스는 뜨는데 안 보임”은 HOP 렌더 실패가 아니라 창 위치/디스플레이 관찰 문제일 수 있다. 위 확인 후에도 window count가 0이면 아래 `hwp_render.mjs` + QuickLook PNG 경로로 같은 rhwp 렌더 엔진을 검증한다.

## 3. 사람 검수 / 부족분 수정 (human-in-the-loop) — 필수 단계
자동 블랭킹·채움은 토큰 단위라 한국어 뉘앙스·레이아웃·과/부족 처리(라벨 과삭제, 다중행 셀, 표 깨짐)를 100% 못 잡는다. 그래서:
1. **HOP, 렌더 PNG, PDF 뷰어 중 가능한 표면으로 사람이 본다.**
2. 부족한 부분을 잡는다:
   - 덜 지워진 PII → `keep.json`에서 빼거나 `transform`에 추가 후 재실행
   - 과하게 지워진 라벨 → `exact`에 추가 후 재실행
   - 레이아웃/표 깨짐 → HOP에서 손으로 수정하거나 원본 HWPX를 다시 생성
3. 만족할 때까지 반복. **마지막 판단은 사람이 한다.**

## 4. 최종본 정책: 한컴 없이 끝내기
기본 산출물은 세 가지다:
```
편집 원본                 = .hwpx 또는 .hwp
사람 검수                 = HOP 또는 렌더 PNG/PDF
최종 시각 고정본           = PDF
네이티브 한컴 .hwp 재저장   = 선택(제출처가 강제할 때만)
```

HOP는 File 메뉴에 `Export PDF...`가 있다. 한컴 없이 제출/공유 가능한 고정본이 필요하면 HOP에서 열어 검수한 뒤 PDF로 내보낸다. HOP GUI가 막히면 렌더/별도 변환 경로로 PDF를 만들고, PDF를 Preview/브라우저로 다시 열어 페이지 수, 표 깨짐, 메모 0건, PII 노출을 확인한다.

한컴이 필요한 경우는 좁다:
- 제출처가 `.hwp` 네이티브 파일만 받는 경우
- 한컴에서 경고 없이 열리는 `.hwp` 호환성이 계약상 필요한 경우
- 한컴 전용 기능(특정 매크로/서식/보안 설정)을 요구하는 경우

그때만 한컴에서 `.hwpx`/`.hwp`를 열고 **다른 이름으로 저장 → `.hwp`** 한다. 한컴이 없으면 이 선택 단계만 생략하고 PDF final을 정본으로 둔다.

주의:
- rhwp/HOP은 HWP를 읽기·렌더는 잘하지만 `.hwp` 쓰기는 한컴 규격과 안 맞을 수 있다(hop #73).
- rhwp `.hwpx`를 한컴에서 직접 열면 "문서가 손상/변조 가능성" 경고가 뜰 수 있고, 한컴 `문서 보안 설정 [낮음]`에서만 열릴 수 있다(내용은 정상).
- LibreOffice + H2Orestart는 import(읽기) 전용이라 HWP 쓰기 경로로 쓰지 않는다.

## 5. 에이전트 시각 검증 (렌더 → 이미지)
HOP은 사람용. 에이전트가 결과를 스스로 확인하려면 페이지를 렌더해 본다(텍스트 추출만으론 레이아웃·다중행 셀을 놓침):
```bash
node scripts/hwp_render.mjs blank.hwpx 0 page0.svg
qlmanage -t -s 1200 -o . page0.svg          # macOS: SVG -> page0.svg.png
```
그 PNG를 멀티모달로 읽어 표·라벨·빈칸이 맞는지 확인한다. **편집 후에는 반드시 이렇게(또는 HOP으로) 눈으로 본다.**

주의: 렌더 PNG에서 한글이 보인다는 것은 “엔진이 텍스트를 그렸다”는 smoke test일 뿐이다. synthetic HWPX나 최소 fixture는 표/문단/줄바꿈 정보가 빈약해서 글자가 한 줄에 뭉쳐 보일 수 있다. 실제 제출 품질은 원본 양식 기반 파일이나 PDF export를 열어 판단한다.

이번 E2E에서 확인한 최소 렌더 게이트:
- `node scripts/hwp_render.mjs file.hwpx 0 page0.svg` 성공.
- `qlmanage -t -s 1200 -o . page0.svg`로 생성한 `page0.svg.png`에서 한글 본문이 실제로 보임.
- 큰 스캔 이미지는 `blank_form.py --blank-images-over ...` 후 1x1 transparent PNG로 대체됨(예: 2048B 이미지 → 68B).

## 6. PDF 고정본
최종 제출/보관은 기본적으로 PDF를 만든다. PDF는 레이아웃이 고정되고, 받는 쪽 환경의 한컴/HOP/rhwp 차이를 덜 탄다.

권장 순서:
1. 편집 원본은 `.hwp`/`.hwpx`로 보존한다.
2. HOP 또는 렌더 PNG/PDF에서 줄넘침·표·서명란을 확인한다.
3. 가능하면 HOP `File > Export PDF...`로 저장/내보내기하고, HOP GUI가 막히면 렌더/별도 변환 경로를 쓴다.
4. 생성된 PDF를 Preview/브라우저로 열어 페이지 수, 표 깨짐, 메모 0건, PII 노출을 다시 확인한다.

제출처가 HWP/HWPX 원본을 요구하면 원본도 함께 보낸다. 그래도 검수 기준은 PDF 시각 고정본으로 삼는 것이 안전하다. 한컴 PDF export는 한컴이 있는 환경의 선택 경로다.

## 함정
- **블랭킹은 화이트리스트로.** 블랙리스트(지울 것 나열)는 PII 누락 위험. 구조만 KEEP하고 나머지 비우면 새 PII가 들어와도 자동으로 비워진다.
- **스캔 이미지 = PII.** 텍스트만 지우면 사업자등록증·신분증 이미지가 남는다. `--blank-images-over`로 처리.
- **mimetype 우선·STORED 유지**는 `blank_form.py`/`hwp_rhwp.mjs`가 처리(한컴 OPC 규격).
- **rhwp 산출물 = 한컴 네이티브 호환 미보장** 전제. 네이티브 `.hwp` 강제 제출일 때만 한컴 재저장을 선택 단계로 둔다.
- **렌더 PNG의 한 줄 뭉침 = fixture 한계일 수 있음.** 이 경우 제출물 실패로 단정하지 말고 원본 양식 기반 파일/PDF export를 확인한다.
- **HOP 창 안 보임 = 먼저 창 위치 문제를 의심.** `System Events`가 window 1을 보면 HOP은 열린 것이다. 내장 화면으로 이동시켜 검수한다.
- `transform`으로 체크박스/라벨을 바꾼 뒤 결과 문자열도 `exact` 또는 `regex` KEEP 목록에 넣는다. 예: `v 법인등록 완료` → `□ 법인등록 완료`.
