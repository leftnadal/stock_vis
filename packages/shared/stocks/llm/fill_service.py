"""캐러셀 추천 LLM 채움 서비스. [D-LLMFILL ⑶⑷⑸⑹]

fill_recommendations(items, materials): 카드별 개별 호출(부분 성공 허용, ⑸).
성공 + 타입 계약 통과 시에만 3키(thesis/perspectives/risk) 주입(⑹). 호출 실패·
파싱 실패·타입 불일치 = 그 카드 placeholder null 유지 + 사유 수집(⑶). 7 core 키 무변경.
비용/토큰은 shared/llm 래퍼의 cost_track으로 집계(⑷).
"""

from __future__ import annotations

import json
import logging
import re

from packages.shared.llm import LLMError, complete
from packages.shared.stocks.llm.card_fill_prompt import build_card_fill_prompt

logger = logging.getLogger(__name__)

# 코드펜스(```json ... ```) 제거용.
_FENCE_OPEN = re.compile(r"^\s*```(?:json)?\s*", re.IGNORECASE)
_FENCE_CLOSE = re.compile(r"\s*```\s*$")


def _strip_fences(text: str) -> str:
    """응답에서 감싼 코드펜스를 제거한다(strict 파싱 전처리)."""
    t = (text or "").strip()
    t = _FENCE_OPEN.sub("", t)
    t = _FENCE_CLOSE.sub("", t)
    return t.strip()


def _is_str_or_none(v) -> bool:
    return v is None or isinstance(v, str)


def _validate_fill(parsed) -> bool:
    """3키 타입 계약 검증. [D-LLMFILL ⑹]

    {thesis: str|None, perspectives: {technical, fundamental, news_context: str|None},
     risk: str|None}. 필수 키 존재 + 타입만 검사(여분 키는 무시하고 추출 시 배제).
    """
    if not isinstance(parsed, dict):
        return False
    if not _is_str_or_none(parsed.get("thesis")):
        return False
    if not _is_str_or_none(parsed.get("risk")):
        return False
    persp = parsed.get("perspectives")
    if not isinstance(persp, dict):
        return False
    for key in ("technical", "fundamental", "news_context"):
        if not _is_str_or_none(persp.get(key)):
            return False
    return True


def fill_recommendations(items: list[dict], materials: list[dict]) -> tuple[list[dict], dict]:
    """추천 카드 3키를 LLM으로 채운다(카드별 격리, 부분 성공 허용).

    Args:
        items: 추천 리스트(7 core 키 + 3 placeholder 키). in-place 변형 + 반환.
        materials: signals_data(프롬프트 재료). ticker(=stock_id)로 매칭.

    Returns:
        (items, meta). meta = {attempted, filled, failed:[{rank, reason}], cost_usd, tokens}.
    """
    material_by_ticker: dict[str, dict] = {}
    for mat in materials or []:
        key = str(mat.get("stock_id") or mat.get("ticker") or "").upper()
        if key:
            material_by_ticker.setdefault(key, mat)

    attempted = 0
    filled = 0
    failed: list[dict] = []
    total_cost = 0.0
    total_tokens = 0

    for item in items or []:
        rank = item.get("rank")
        ticker = str(item.get("ticker") or "").upper()

        material = dict(material_by_ticker.get(ticker, {}))
        material.setdefault("ticker", ticker)
        if item.get("company_name"):
            material["company_name"] = item["company_name"]

        attempted += 1
        try:
            prompt = build_card_fill_prompt(material)
            resp = complete(
                prompt,
                provider="gemini",
                fallback="anthropic",
                retries=1,
                cost_track=True,
            )
            total_cost += float(resp.cost_usd or 0.0)
            total_tokens += int(resp.input_tokens or 0) + int(resp.output_tokens or 0)
            parsed = json.loads(_strip_fences(resp.text))
        except (LLMError, ValueError, TypeError) as exc:
            failed.append({"rank": rank, "reason": f"{type(exc).__name__}: {exc}"[:200]})
            continue
        except Exception as exc:  # noqa: BLE001 — 카드 격리(전체 bake 보호)
            failed.append({"rank": rank, "reason": f"unexpected {type(exc).__name__}"[:200]})
            continue

        if not _validate_fill(parsed):
            failed.append({"rank": rank, "reason": "type_contract_violation"})
            continue

        persp = parsed["perspectives"]
        item["thesis"] = parsed.get("thesis")
        item["perspectives"] = {
            "technical": persp.get("technical"),
            "fundamental": persp.get("fundamental"),
            "news_context": persp.get("news_context"),
        }
        item["risk"] = parsed.get("risk")
        filled += 1

    meta = {
        "attempted": attempted,
        "filled": filled,
        "failed": failed,
        "cost_usd": round(total_cost, 6),
        "tokens": total_tokens,
    }
    return items, meta
