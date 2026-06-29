# HWP / HWPX 편집

## 포맷
- **HWPX** = ZIP 컨테이너. 본문은 `Contents/section0.xml`, `section1.xml` …
  - 문단 = `<hp:p>`, 텍스트 런 = `<hp:run charPrIDRef="N"><hp:t>실제 텍스트</hp:t></hp:run>`.
  - 표 셀도 문단이지만 `charPrIDRef`가 본문과 다르다. 날짜/숫자 셀을 건드리지 않으려면 `<hp:t>` 단위 정확 일치 치환을 쓴다.
  - 특수문자는 XML escape: `<`→`&lt;`, `>`→`&gt;`, `&`→`&amp;`.
- **HWP**(바이너리, .hwp) = soffice/LibreOffice가 import 못 함. 가벼운 텍스트/구조 추출만 필요하면 `pyhwp`:
  ```bash
  uv run --with pyhwp --with olefile --with six hwp5txt form.hwp
  uv run --with pyhwp --with olefile --with six hwp5html --output out form.hwp
  ```
  바이너리 HWP를 **프로그램으로 읽기/편집/쓰기**하려면 아래 rhwp 사용(검증됨). 한글 수동 작성은 최후수단.

## rhwp — 바이너리 .hwp 읽기/편집/쓰기 + 변환 (검증됨)
`@rhwp/core`(Rust+WASM, MIT)는 바이너리 `.hwp`까지 프로그램 처리한다. 헤드리스 Node에서 실증: `.hwp`/`.hwpx` 파싱, `replaceAll`, `.hwp↔.hwpx` 변환, `exportHwp`/`exportHwpx` 전부 동작.

설치(wasm 5.6M이라 스킬에 번들 안 함):
```bash
npm install @rhwp/core
```

사용:
```bash
# .hwp → .hwpx 변환 → 이후 hwpx_extract.py로 텍스트 추출 (pyhwp 불필요)
node scripts/hwp_rhwp.mjs form.hwp form.hwpx

# 필요 시 .hwp도 생성(기본 final은 PDF)
node scripts/hwp_rhwp.mjs filled.hwpx final.hwp

# 매핑 치환 (문서 모델 단위 replaceAll; .hwp/.hwpx 양쪽)
node scripts/hwp_rhwp.mjs in.hwpx out.hwpx mapping.json
# mapping.json = {"기존 문구": "새 문구"}; 출력 포맷은 출력 확장자(.hwp/.hwpx)로 결정
```
- 엔진에선 `field_practice.rhwp_backend`: `rhwp_status()`(가용성), `convert_hwp(src, out, mapping)`(실행).
- `replaceAll`은 문서 모델 치환이라 `<hp:t>` 정확일치가 불필요(부분 텍스트도 잡힘) → **과치환 방지로 고유 문자열 사용**.
- 0.x API라 시그니처 변동 가능. `.hwp` 출력은 `exportHwpx`의 `styleIDRef` 엣지 실패를 회피한다(HWPX 출력만 그 이슈 있음).
- **편집 원본은 `.hwpx` 우선, 필요 시 `.hwp`도 생성**: `node scripts/hwp_rhwp.mjs filled.hwpx final.hwp` → 바이너리 `.hwp`(CFB) 생성, rhwp 라운드트립·치환 영속 실측됨.
- **한컴 호환 미보장(중요)**: rhwp/hop이 만든 `.hwp`는 rhwp 재파싱은 되어도 한컴에서 안 열릴 수 있음(hop [#73](https://github.com/golbin/hop/issues/73) 동일 증상). 기본 최종본은 HOP에서 검수한 PDF이고, 한컴 확인/재저장은 네이티브 `.hwp` 제출이 강제될 때만 선택한다.
- **사실 보존·편집 후 HOP/PDF 시각확인도 동일하게 필수.** 한컴 확인은 네이티브 `.hwp` 강제 제출일 때만 선택한다.

## hop — macOS GUI로 보고 수정 (한컴 없을 때)
mac엔 한컴오피스가 없어도 된다. **hop**(golbin/hop, MIT, rhwp 기반 데스크탑 앱)이 macOS에서 `.hwp`/`.hwpx`를 **열어 보고 직접 수정**하며 PDF final을 만들 수 있다.

설치(63MB GUI 앱이라 스킬엔 번들 안 하고 brew로):
```bash
brew install --cask hop
```

실행:
```bash
open -a HOP report.hwpx
open -a HOP
```

용도 구분 (중요):
- **뷰어/시각검증** ← 주 용도. 편집 후 레이아웃·줄넘침·페이지분할을 눈으로 확인. mac에서 한컴 대체.
- **PDF export**: HOP `File > Export PDF...`로 검수된 PDF final 생성.
- **가벼운 수동 수정**: GUI에서 직접 편집.
- **저장 주의**: hop은 **HWPX 원본 저장 막힘**(다른이름으로 `.hwp` 저장만 가능). 기본 최종본은 PDF로 두고, `.hwpx` 원본은 스크립트가 생성한 파일을 보존한다. HOP/rhwp가 저장한 `.hwp`는 한컴 호환이 불확실하므로 네이티브 `.hwp` 강제 제출일 때만 한컴 재저장으로 정리한다.

엔진: `field_practice.rhwp_backend.hop_status()`(설치 확인), `open_in_hop(path)`(실행).

> **한컴은 선택 옵션**: rhwp가 만든 `.hwpx`를 한컴에서 직접 열면 "문서가 손상/변조 가능성" 경고가 뜨고 **`문서 보안 설정 [낮음]`에서만 열릴 수 있다**(내용은 정상). 깨끗한 네이티브 `.hwp`가 필요할 때만 한컴에서 열어 **다른 이름으로 저장**한다. 한컴 없는 기본 흐름은 `references/blanking-review-hop.md`의 HOP/PDF final 경로를 따른다.

## 텍스트 추출
```bash
python scripts/hwpx_extract.py report.hwpx --out report.txt
```
문단당 한 줄. 표·근무시간 합계 검산, 디슬롭 분석 입력 등에 사용.

## 텍스트 치환 + 재패키징
```bash
python scripts/hwpx_replace.py in.hwpx out.hwpx mapping.json
# mapping.json = {"기존 문장.": "새 문장."}
# --raw : <hp:t> 래핑 없이 런 내부 부분일치 치환(템플릿 토큰 채우기)
```
- 기본은 `<hp:t>전체문장</hp:t>` 정확 일치(문장 통째 교체에 안전). 각 old는 고유해야 함.
- **재패키징은 반드시 `mimetype`을 첫 항목·STORED**로(스크립트가 처리). 일반 zip으로 다시 묶으면 한글이 거부할 수 있다.

## 빈 셀 좌표 채움 (실제 양식)
실제 학교 양식은 플레이스홀더가 아니라 빈 셀(`<hp:t></hp:t>`)이 많다. 이 경우 `replaceAll`/텍스트 치환으로는 채울 대상 문자열이 없으므로, 표 좌표를 고정한 JSON 매핑을 사용한다.

```json
[
  {
    "section_path": "Contents/section0.xml",
    "table_index": 1,
    "row_index": 1,
    "cell_index": 3,
    "text": "480",
    "char_pr_id": "12"
  },
  {
    "section_path": "Contents/section0.xml",
    "table_index": 1,
    "row_index": 1,
    "cell_index": 4,
    "text": "사업 아이템 검증 인터뷰 정리",
    "char_pr_id": "12"
  }
]
```

```bash
cd engine
uv run field-practice document cells \
  --template input.hwpx \
  --cells cells.json \
  --out filled.hwpx
```

- `table_index`/`row_index`/`cell_index`는 0부터 센다. `document inspect` 또는 XML 표 덤프로 먼저 확인한다.
- 같은 양식이라도 병합 셀 때문에 첫 행과 다음 행의 cell index가 다를 수 있다. 주차별 양식은 월요일 행이 5셀, 화~일 행이 4셀이다.
- `char_pr_id`를 지정하면 기존 빈 런의 색상/강조 스타일을 덮어쓴다. 실제 테스트에서 일부 빈 칸이 파란 글자 스타일을 상속했으므로, 주차별 본문/활동내역은 정상 스타일 ID를 명시하고 HOP/렌더 PNG로 확인한다.
- 장문은 셀 폭에 맞게 짧은 문장/줄로 넣는다. 자동 삽입 뒤 `<hp:linesegarray>`가 stale일 수 있으므로 HOP/PDF에서 줄넘침을 본다.

## 사후 주의
- `<hp:linesegarray>`는 줄바꿈 레이아웃 캐시다. 텍스트 길이가 바뀌면 stale 해지지만 한글이 열 때 reflow한다. **편집 후 반드시 한글(또는 mac이면 hop)에서 열어 줄 넘침/페이지 분할을 눈으로 확인**한다.
- `Preview/PrvText.txt`, `Preview/PrvImage.png`는 미리보기 캐시(편집 후 stale). 한글 저장 시 갱신됨.
- **원본을 덮어쓰지 말고 사본**(`*_edited.hwpx`)으로 저장한다.

## 검증
```bash
python scripts/hwpx_extract.py out.hwpx | grep -nE "<검산 키워드>"
```
- 치환 전후 합계(예: 근무시간 분 합)가 동일한지 재추출해서 확인.
- 표의 날짜/숫자 셀이 그대로인지 확인(치환 대상에서 제외됐는지).
