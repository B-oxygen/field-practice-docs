from __future__ import annotations

from pathlib import Path
from typing import Protocol

from field_practice.config import COMPANY_NAME, DEPARTMENT, STUDENT_ID, STUDENT_NAME


class RowWithMinutes(Protocol):
    @property
    def minutes(self) -> int: ...


def render_final_source_markdown(
    final_draft: Path,
    monthly_draft: Path,
    rows: tuple[RowWithMinutes, ...],
    scenario: str,
) -> str:
    _ = final_draft.read_text(encoding="utf-8") if final_draft.exists() else ""
    _ = monthly_draft.read_text(encoding="utf-8") if monthly_draft.exists() else ""
    credit_label = "12학점(주전공)" if scenario == "640" else "9학점(주전공)"
    total_minutes = sum(row.minutes for row in rows)
    lines = [
        "# 창업현장실습 활동 결과보고서",
        "",
        "## 1. 신청자",
        "",
        "| 항목 | 내용 |",
        "| --- | --- |",
        f"| 성명 | {STUDENT_NAME} |",
        f"| 학부(과) | {DEPARTMENT} |",
        f"| 학번 | {STUDENT_ID} |",
        "| 대상학기 | 2026년도 1학기 |",
        f"| 신청학점 | {credit_label} |",
        "| 사업자등록번호 | 000-00-00000 |",
        f"| 상호 | {COMPANY_NAME} |",
        "| 개업일 | 2025.01.07 |",
        "| 법인설립 여부 | 법인등록 완료 |",
        "",
        "## 2. 사업체 인원현황",
        "",
        "주식회사 예시컴퍼니의 창업팀 및 개발·운영 인력이 서비스 기획, 개발, 고객 대응, 사업화 업무를 병행하며 창업현장실습을 수행하였다.",
        "",
        "## 3. 국가사업 및 기타 교내·외 창업유관 행사 참여 현황",
        "",
        "TIPS 및 IR 관련 미팅, 외부 협력 논의, 기관 고객 대응 일정을 바탕으로 서비스 사업화 가능성과 도입 요구사항을 검토하였다.",
        "",
        "## 4. 전공과의 연계성",
        "",
        "경영학 전공에서 학습한 창업, 전략경영, 마케팅, 운영관리, 조직관리 지식을 바탕으로 고객 요구사항 분석, 서비스 사업화, 기관 고객 도입, 제품/시장 적합성 검토, KPI 및 성과관리를 수행하였다.",
        "",
        "## 5. 창업현장실습 수행 실적",
        "",
        "| 항목 | 내용 |",
        "| --- | --- |",
        "| 아이템 | 대학 및 기관 대상 학생 커리어/역량 데이터 기반 서비스와 관리자 대시보드 |",
        "| 산업분야 | 교육·커리어테크 플랫폼 / SaaS 기반 데이터 관리 서비스 |",
        "| 창업단계 | 5단계: 프로토타입 생산 완료 |",
        f"| 주차 보고서 산정 활동시간 | {total_minutes}분 |",
        "",
        "## 6. 창업현장실습 월별 보고서",
        "",
        "### 3월",
        "",
        "오리엔테이션과 CTO 온보딩을 통해 개발 조직 운영 방식과 인프라를 파악하고, 초기 앱 및 관리자 대시보드 요구사항을 정리하였다. TIPS, IR, 외부 협력 일정과 연결하여 사업화 관점의 검토 자료도 병행하였다.",
        "",
        "### 4월",
        "",
        "기관 고객 요구사항을 반영해 대시보드, API, 앱 기능 개발을 진행하고 프로토타입 QA를 수행하였다. 사업 프로그램과 외부 미팅에서 확인한 피드백을 제품 개선 항목으로 정리하였다.",
        "",
        "### 5월",
        "",
        "집중 개발 스프린트를 통해 운영 테스트, 고객 대응, 서비스 안정화, 사업·운영 프로세스 정비를 수행하였다.",
        "",
        "### 6월",
        "",
        "최종 QA와 개발 산출물 정리, 월별 지표 검토, 결과보고서 및 주차별 보고서 패킷 작성으로 학기 실습 결과를 정리하였다.",
        "",
        "## 7. 창업현장실습 참여 결과",
        "",
        "개발, 사업화, 조직 운영 업무를 통합적으로 경험하며 GitHub, Calendar, aLog 증빙에 기반해 앱과 관리자 대시보드 구현, QA, 운영 검토를 수행하였다. 기관 고객 대응과 사업 문서 작성 과정에서 경영학 전공 지식을 실제 창업 서비스의 제품/시장 적합성 검토와 성과관리 업무에 적용하였다.",
        "",
        "## 8. 별첨 안내",
        "",
        "주차별 활동 보고서, 증빙 원장, 시간 원장, HWPX 변환 검증 보고서를 별첨 자료로 관리한다.",
    ]
    return "\n".join(lines) + "\n"
