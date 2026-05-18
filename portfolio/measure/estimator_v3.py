"""Slice 10 Step 0 §2 — Token estimator v3 (#48 close).

기존 v2(`portfolio.llm.budget_estimator.estimate_input_tokens_v2`)는 섹션 합산
휴리스틱. Slice 9 한국어 rationale 호출에서 systematic underestimate 60.83% 발견 →
한국어 토크나이저 특성을 휴리스틱으로 흡수 불가.

v3 설계:
- **input**: Anthropic `count_tokens` API 실측 (±2% 정밀도, 무료)
- **output**: v2 char ratio 유지 (Slice 11 #51로 이연 — 신규 부채)
- **cache**: in-memory LRU (max 1000) — slice당 reset
- **fallback**: API 실패 시 v2 char/3 휴리스틱 (warn log)
- **backward-compat**: legacy `estimate_tokens()` = `input + output` wrapper

D-4 scope: input만 보정. output_tokens estimator는 Slice 11+ 부채(#51).
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections import OrderedDict
from typing import Any

try:
    from anthropic import Anthropic
except ImportError:  # pragma: no cover — dev 환경
    Anthropic = None  # type: ignore[misc,assignment]

from portfolio.llm.token_budgets import estimate_input_tokens as _v2_estimate_input

logger = logging.getLogger(__name__)


DEFAULT_MODEL = "claude-haiku-4-5"
CACHE_MAX_ENTRIES = 1000


# ============================================================
# Cache (in-memory LRU, slice reset 가능)
# ============================================================


_cache: "OrderedDict[str, int]" = OrderedDict()


def _hash_inputs(messages: list[dict], system: str | None, model: str) -> str:
    payload = json.dumps(
        {"messages": messages, "system": system or "", "model": model},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cache_get(key: str) -> int | None:
    val = _cache.get(key)
    if val is not None:
        _cache.move_to_end(key)
    return val


def _cache_set(key: str, value: int) -> None:
    _cache[key] = value
    _cache.move_to_end(key)
    while len(_cache) > CACHE_MAX_ENTRIES:
        _cache.popitem(last=False)


def reset_cache() -> None:
    """슬라이스 reset용 (CostGuard.reset_for_slice 패턴)."""
    _cache.clear()


def cache_stats() -> dict[str, int]:
    return {"size": len(_cache), "max": CACHE_MAX_ENTRIES}


# ============================================================
# Anthropic client (lazy + 주입 가능 — 테스트 친화)
# ============================================================


_client: Any = None


def _get_client() -> Any:
    global _client
    if _client is None:
        if Anthropic is None:
            raise RuntimeError("anthropic SDK not installed")
        _client = Anthropic()
    return _client


def set_client(client: Any) -> None:
    """테스트/mock 주입용."""
    global _client
    _client = client


# ============================================================
# Estimators
# ============================================================


def _estimate_input_tokens_v2_fallback(
    messages: list[dict], system: str | None
) -> int:
    """API 실패 시 v2 char/3 휴리스틱으로 fallback.

    messages 내 모든 string 컨텐츠 + system을 concat → estimate_input_tokens.
    """
    parts: list[str] = []
    if system:
        parts.append(system)
    for m in messages:
        content = m.get("content", "")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and "text" in block:
                    parts.append(block["text"])
    return _v2_estimate_input("\n".join(parts))


def estimate_input_tokens(
    messages: list[dict],
    system: str | None = None,
    model: str = DEFAULT_MODEL,
) -> int:
    """Anthropic `count_tokens` API로 input_tokens 실측.

    캐시 적중 시 즉시 반환. API 실패 시 v2 char/3 fallback (warn log).

    Args:
        messages: Anthropic messages 형식 list (role/content).
        system: system prompt (없으면 "").
        model: 모델 ID — 토크나이저 선택용.

    Returns:
        input 토큰 수 (실측 또는 fallback 추정).
    """
    cache_key = _hash_inputs(messages, system, model)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        client = _get_client()
        kwargs: dict[str, Any] = {"model": model, "messages": messages}
        if system:
            kwargs["system"] = system
        response = client.messages.count_tokens(**kwargs)
        result = int(response.input_tokens)
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        logger.warning("count_tokens API failed, fallback to v2: %s", e)
        return _estimate_input_tokens_v2_fallback(messages, system)


# ============================================================
# Output estimator (Slice 11 #51 본격 구현)
# ============================================================
#
# 진입점별 char ratio fitting — 데이터 출처: all_llm_calls.jsonl (200 entries,
# 8 진입점 그룹). 각 진입점의 (output_tokens / output_chars) 평균값을 ratio로 사용.
#
# Backtest 결과 (scripts/coach/backtest_output_estimator.py 참조):
# - global mean_delta = 5.11% / P90_delta = 11.20% / max_delta = 33.12% (1 outlier).
# - Fallback §1 적용: KPI 임계 P90 ≤ 15% 완화 + #51 keep_open (multivariate 미래 작업).

# 진입점별 char/token ratio (mean fit). 정의: ratio = output_tokens / output_chars.
ENTRY_POINT_OUTPUT_RATIOS: dict[str, float] = {
    "e1": 0.8835,           # Slice 1 one-line diagnosis (헤드라인+요약)
    "e2": 0.8599,           # Slice 3 diagnostic card (4요소)
    "e3": 0.7307,           # Slice 5 metric comments
    "e3_portfolio": 0.6764, # Slice 6 portfolio commentary
    "e4_conversation": 0.7233,  # Slice 7+8 conversation
    "e5": 0.5006,           # Slice 2 adjustments (JSON heavy)
    "e6": 0.7881,           # Slice 4 comparison
    "rationale": 0.9778,    # Slice 9 rationale (한국어 long-form)
}

# Fallback global ratio (200 entries 전체 평균) — 진입점 미식별/미등록 시 사용.
GLOBAL_OUTPUT_RATIO: float = 0.7584


def estimate_output_tokens(
    expected_output_chars: int | None = None,
    entry_point: str | None = None,
    model: str = DEFAULT_MODEL,
) -> int:
    """진입점별 char ratio 기반 output 토큰 추정 (Slice 11 #51).

    Args:
        expected_output_chars: 예상 응답 문자열 길이. None 또는 0 → 0 반환.
        entry_point: 진입점 키 ("e1"~"e6", "e3_portfolio", "e4_conversation",
            "rationale"). 미식별 또는 미등록 시 `GLOBAL_OUTPUT_RATIO` 사용.
        model: 미사용 (현재 단변량 fit; #51 keep_open으로 multivariate 후속).

    Returns:
        int(expected_output_chars × ratio). expected_output_chars가 음수면 0.
    """
    if expected_output_chars is None or expected_output_chars <= 0:
        return 0
    ratio = ENTRY_POINT_OUTPUT_RATIOS.get(entry_point or "", GLOBAL_OUTPUT_RATIO)
    return int(expected_output_chars * ratio)


def estimate_tokens(
    messages: list[dict],
    system: str | None = None,
    expected_output_chars: int | None = None,
    entry_point: str | None = None,
    model: str = DEFAULT_MODEL,
) -> dict[str, int]:
    """Legacy wrapper — input + output 합산 dict 반환.

    Slice 11: `entry_point` 옵션 추가 (output ratio 선택). 미지정 시 GLOBAL 사용.
    """
    inp = estimate_input_tokens(messages, system, model)
    out = estimate_output_tokens(expected_output_chars, entry_point, model)
    return {"input_tokens": inp, "output_tokens": out, "total": inp + out}
