"""
Theme Heat 성분 이름표 사전 (TH-15, 결정25=③) — 설계 문서 §2 정본의 코드 미러.

API·프론트가 참조하는 **단일 소스**. 성분 라벨을 뷰/직렬화기에 하드코딩 금지 —
반드시 이 모듈만 참조한다. 설계 문서 theme_heat_design.md §2 표와 1:1 정합
(불일치 시 설계 문서가 진실, 코드를 맞춘다).

형식: id → {label_technical, label_surface}
  - label_technical: 지표 정식 명칭(툴팁·기술 표기)
  - label_surface: 일반 사용자 표면 라벨(카드 표시)
"""

COMPONENT_LABELS = {
    "C1": {"label_technical": "밸류에이션", "label_surface": "몸값 부담"},
    "C2": {"label_technical": "내부자·증자 신호", "label_surface": "내부자 이탈"},
    "C3": {"label_technical": "뉴스 밀도", "label_surface": "이야기 밀도"},
    "C4": {"label_technical": "ETF 자금흐름", "label_surface": "ETF 돈줄"},
    "C5": {"label_technical": "레버리지 투기", "label_surface": "빚투 강도"},
    "C6": {"label_technical": "상관 동조화", "label_surface": "같이 움직임"},
    "C7": {"label_technical": "거래량 급증", "label_surface": "거래 열기"},
    "C8": {"label_technical": "추정치 괴리", "label_surface": "실적 안 따라옴"},
}

# 성분 순서 (C1~C8 고정 — components 배열 정렬용)
COMPONENT_ORDER = ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"]


def component_label(component_id: str) -> dict:
    """성분 id → 라벨 dict. 미지 id는 id 자체를 폴백 라벨로."""
    return COMPONENT_LABELS.get(
        component_id, {"label_technical": component_id, "label_surface": component_id}
    )
