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


def _estimate_input_tokens_v2_fallback(messages: list[dict], system: str | None) -> int:
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
# Output estimator (Slice 13 Step 0a #51 — multivariate OLS fit)
# ============================================================
#
# 모델 진화:
# - Slice 11 (구모델, 단변량): tokens = chars × ratio. mean=5.11% P90=11.20% max=33.12%.
# - Slice 13 (신모델, 다변량 OLS): tokens = a + b × chars.
#   - (entry_point, model) 셀 N≥5 → 셀별 fit.
#   - (entry_point) fallback → EP-only fit.
#   - 미식별 → GLOBAL_OUTPUT_FIT.
#   백테스트 결과 (scripts/coach/backtest_output_estimator.py):
#     mean=4.40% P90=9.52% max=24.58% (e4_conversation 33.12 → 16.94 개선).
#
# 데이터 출처: docs/portfolio/coach/all_llm_calls.jsonl (200 entries, 8 진입점).
# 시그니처 유지: estimate_output_tokens(chars, entry_point, model). 내부만 교체.

# 구모델 baseline (Slice 11) — 회귀 추적용 보존, 신모델로 대체됨.
# ratio = output_tokens / output_chars (단변량 mean fit).
ENTRY_POINT_OUTPUT_RATIOS: dict[str, float] = {
    "e1": 0.8835,
    "e2": 0.8599,
    "e3": 0.7307,
    "e3_portfolio": 0.6764,
    "e4_conversation": 0.7233,
    "e5": 0.5006,
    "e6": 0.7881,
    "rationale": 0.9778,
}
GLOBAL_OUTPUT_RATIO: float = 0.7584  # 구모델 fallback (보존).


# Slice 13 신모델 (다변량 OLS): tokens = a + b × chars.
# all_llm_calls.jsonl N=200으로 fit. 재fit 트리거: 데이터셋 행 추가 시 backtest 재실행.
ENTRY_POINT_OUTPUT_FITS: dict[str, tuple[float, float]] = {
    "e1": (-20.2608, 0.971655),  # N=10
    "e2": (-32.9435, 0.905711),  # N=15
    "e3": (-14.1024, 0.753001),  # N=15
    "e3_portfolio": (283.1472, 0.177887),  # N=21
    "e4_conversation": (86.1065, 0.645782),  # N=83
    "e5": (8.9867, 0.468976),  # N=15
    "e6": (-39.4334, 0.819425),  # N=15
    "rationale": (171.0966, 0.676134),  # N=26
}

# (EP, model) 셀별 fit — N ≥ 5인 셀만 보유. 미존재 셀은 ENTRY_POINT_OUTPUT_FITS fallback.
ENTRY_POINT_MODEL_OUTPUT_FITS: dict[tuple[str, str], tuple[float, float]] = {
    ("e1", "claude-sonnet-4-5"): (-14.896, 0.947012),  # N=7
    ("e2", "claude-haiku-4-5"): (-72.5954, 0.954621),  # N=8
    ("e2", "claude-sonnet-4-5"): (-17.5885, 0.889633),  # N=7
    ("e3", "claude-haiku-4-5"): (-23.0666, 0.771894),  # N=8
    ("e3", "claude-sonnet-4-5"): (-0.1735, 0.724798),  # N=7
    ("e3_portfolio", "claude-haiku-4-5"): (314.2537, 0.119976),  # N=11
    ("e3_portfolio", "claude-sonnet-4-5"): (161.1528, 0.396841),  # N=10
    ("e4_conversation", "claude-haiku-4-5"): (15.5766, 0.698344),  # N=42
    ("e4_conversation", "claude-sonnet-4-5"): (167.552, 0.582211),  # N=41
    ("e5", "claude-haiku-4-5"): (14.1478, 0.474434),  # N=8
    ("e5", "claude-sonnet-4-5"): (10.1184, 0.43951),  # N=7
    ("e6", "claude-haiku-4-5"): (-95.855, 0.869372),  # N=8
    ("e6", "claude-sonnet-4-5"): (-26.98, 0.803866),  # N=7
    ("rationale", "claude-sonnet-4-5"): (171.0966, 0.676134),  # N=26
}

# 신모델 global fallback (전체 200 entries OLS).
GLOBAL_OUTPUT_FIT: tuple[float, float] = (65.9457, 0.673089)


def _model_short(model: str) -> str:
    """모델 ID에서 prefix 변형(haiku/sonnet 4-5)을 정규화.

    "claude-haiku-4-5" / "claude-haiku-4-5-20251001" → "claude-haiku-4-5"
    "claude-sonnet-4-5" → "claude-sonnet-4-5"
    Slice 13 fit 테이블 키와 매칭용.
    """
    parts = model.split("-")
    # claude-{name}-{major}-{minor}... → 앞 4 토큰만 사용
    if len(parts) >= 4:
        return "-".join(parts[:4])
    return model


def estimate_output_tokens(
    expected_output_chars: int | None = None,
    entry_point: str | None = None,
    model: str = DEFAULT_MODEL,
) -> int:
    """다변량 OLS 기반 output 토큰 추정 (Slice 13 Step 0a #51).

    공식: tokens = a + b × expected_output_chars.
    계수 lookup 우선순위:
      1. (entry_point, normalized_model) → ENTRY_POINT_MODEL_OUTPUT_FITS
      2. entry_point → ENTRY_POINT_OUTPUT_FITS
      3. GLOBAL_OUTPUT_FIT

    Args:
        expected_output_chars: 예상 응답 문자열 길이. None 또는 ≤ 0 → 0 반환.
        entry_point: 진입점 키 ("e1"~"e6", "e3_portfolio", "e4_conversation",
            "rationale"). 미식별 시 GLOBAL fallback.
        model: 모델 ID. 정규화 후 (EP, model) 셀 lookup. 미매칭 시 EP-only fallback.

    Returns:
        int(a + b × chars). 음수는 0으로 clip (안전).
    """
    if expected_output_chars is None or expected_output_chars <= 0:
        return 0
    ep = entry_point or ""
    fit = ENTRY_POINT_MODEL_OUTPUT_FITS.get((ep, _model_short(model)))
    if fit is None:
        fit = ENTRY_POINT_OUTPUT_FITS.get(ep, GLOBAL_OUTPUT_FIT)
    a, b = fit
    return max(0, int(a + b * expected_output_chars))


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
