"""MP2-ANALOG Slice C-L3 — 톤가드(결정론 스캔, LLM 무의존).

역할: L3 생성물(한국어 1문장)이 맥락 서술 톤을 지키는지 결정론 검증. 생성 직후 자동 실행 →
  실패 시 1회 재생성 → 재실패면 저장 안 함(why=null 유지).
금지(지시서 §3 톤가드): ⑴ 원인 단정("X 때문에 하락") ⑵ 시세 방향 예측("오를 것") ⑶ 투자 조언("매수").
  허용: 사실 맥락 서술("X 발표가 있던 국면", "규제 우려가 부각된 날").
분리 이유: 생성(LLM)과 독립한 순수 함수 → 모킹 없이 단위 테스트. 프롬프트가 1차 방어, 가드가 안전망.
"""

from __future__ import annotations

# ⑴ 원인 단정 — 헤드라인→시세의 인과를 단정하는 접속.
CAUSAL_PATTERNS: tuple[str, ...] = (
    "때문에", "때문", "탓에", "탓으로", "덕분에", "여파로", "여파에",
    "로 인해", "으로 인해", "로 인한", "으로 인한", "영향으로", "영향에",
)
# ⑵ 시세 방향 예측 — 미래 방향 단정(사실 과거 서술은 허용).
DIRECTION_PREDICT_PATTERNS: tuple[str, ...] = (
    "오를 것", "내릴 것", "상승할 것", "하락할 것", "상승할 전망", "하락할 전망",
    "급등할", "급락할", "오를 전망", "내릴 전망", "반등할 것", "조정받을 것",
)
# ⑶ 투자 조언 어투.
ADVICE_PATTERNS: tuple[str, ...] = (
    "매수", "매도", "사야", "팔아야", "추천", "비중 확대", "비중 축소",
    "손절", "익절", "담아야", "들어가야", "매집",
)

_ALL_BANNED: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("causal", CAUSAL_PATTERNS),
    ("direction_predict", DIRECTION_PREDICT_PATTERNS),
    ("advice", ADVICE_PATTERNS),
)

MAX_SENTENCES = 2  # "1문장" 목표 — 마침표 2개까지 관용(마지막 마침표 허용), 그 이상은 위반.


def check_tone(text: str) -> tuple[bool, str | None]:
    """(통과, 위반사유). 위반사유 = 'causal:때문에' 형태(디버그용). 통과 시 (True, None).

    빈 문자열/공백만 = 위반(empty). 금지 패턴 매칭 = 위반. 문장 수 초과 = too_many_sentences.
    """
    stripped = (text or "").strip()
    if not stripped:
        return False, "empty"

    for category, patterns in _ALL_BANNED:
        for p in patterns:
            if p in stripped:
                return False, f"{category}:{p}"

    # 문장 수 근사(마침표/물음표/느낌표). 마지막 종결부호 1개는 관용.
    terminators = sum(stripped.count(c) for c in (".", "。", "!", "?"))
    if terminators > MAX_SENTENCES:
        return False, "too_many_sentences"

    return True, None
