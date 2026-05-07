"""진입점별 LLM input token budget 상수 (Slice 2 백로그 #5, Slice 3 Step 9).

Step 7 토큰 측정 결과 기반:
  - Slice 1 (E1 글쓰기):       ~3,700 tokens → budget 5,000
  - Slice 2 (E5 추출):         ~900 tokens   → budget 2,000  (P90 × 1.5)
  - Slice 3 (E2 4요소 카드):    ~620 tokens   → budget 1,500 (P90 × 1.5)
  - Slice 4 (E6 비교 해설):     ~768 tokens   → budget 1,500 (P90=845 × 1.5 → round-up 500)

새 진입점 추가 시 (e3/e4 등) ENTRYPOINT_TOKEN_BUDGETS dict에 등록.
"""

from __future__ import annotations

# 진입점별 input token budget
ENTRYPOINT_TOKEN_BUDGETS: dict[str, int] = {
    "e1": 5000,  # Slice 1 결정값
    "e5": 2000,  # Slice 2 Step 7 (P90=756 × 1.5 → round-up 2000)
    "e2": 1500,  # Slice 3 Step 7 (P90=686 × 1.5 → round-up 1500)
    "e6": 1500,  # Slice 4 Step 7 (P90=845 × 1.5=1267.5 → round-up 500 = 1500, E2와 동일)
    # Slice 5+: e3/e4 추가 시 등록
}


def get_token_budget(entrypoint: str) -> int:
    """진입점별 budget 반환.

    Raises:
        ValueError: 미등록 진입점
    """
    if entrypoint not in ENTRYPOINT_TOKEN_BUDGETS:
        raise ValueError(
            f"Unknown entrypoint: {entrypoint!r}. "
            f"Available: {list(ENTRYPOINT_TOKEN_BUDGETS.keys())}"
        )
    return ENTRYPOINT_TOKEN_BUDGETS[entrypoint]


def estimate_input_tokens(prompt: str) -> int:
    """프롬프트 입력 토큰 보수적 추정 (한국어/영어 평균 3 char/token).

    정확한 카운트가 필요하면 anthropic count_tokens API 사용.
    런타임 가드레일 용도 — 빠른 휴리스틱.
    """
    return len(prompt) // 3
