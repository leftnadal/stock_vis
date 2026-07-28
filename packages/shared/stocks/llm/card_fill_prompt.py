"""캐러셀 카드 1장 재료 → 단일 채움 프롬프트. [D-LLMFILL ⑴⑺]

재료 = signals_data 항목(+ 추천 항목의 표시 필드 병합). 방어적 `.get()`으로
누락 필드는 생략. 출력 계약 = JSON only 3키
{thesis, perspectives:{technical, fundamental, news_context}, risk}. 한국어.
v1 재료 범위 = signals_data(news_context·tag_details·mini_chart 등) — RelationConfidence
편입은 후속 슬라이스. [D-LLMFILL ⑺]
"""

from __future__ import annotations

import json


def build_card_fill_prompt(material: dict) -> str:
    """카드 1장 재료 → 채움 프롬프트(한국어, JSON-only 출력 계약).

    Args:
        material: signals_data 항목. ticker/stock_id·company_name·sector·close·
            change_pct·composite_score·signals·tag_details·news_context 등.

    Returns:
        단일 프롬프트 문자열.
    """
    news = material.get("news_context") or {}
    signals = material.get("signals") or []
    signal_lines = [
        f"- {s.get('label') or s.get('id', '')}: "
        f"방향={s.get('direction', '')} 값={s.get('value', '')}"
        for s in signals
        if isinstance(s, dict)
    ]

    facts = {
        "ticker": material.get("ticker") or material.get("stock_id", ""),
        "company_name": material.get("company_name", ""),
        "sector": material.get("sector", ""),
        "close": material.get("close", material.get("close_price", "")),
        "change_pct": material.get("change_pct", material.get("change_percent", "")),
        "signal_tag": (material.get("tag_details") or {}).get("primary", ""),
        "composite_score": material.get("composite_score", ""),
        "news_headline": news.get("headline", ""),
        "news_match_type": news.get("match_type", "none"),
        "news_age_days": news.get("age_days", ""),
    }
    facts_block = json.dumps(facts, ensure_ascii=False, indent=2)
    signals_block = "\n".join(signal_lines) if signal_lines else "(시그널 없음)"

    return (
        "당신은 주식 EOD 신호 카드를 설명하는 한국어 투자 애널리스트입니다.\n"
        "아래 사실만 근거로 카드 1장의 요약을 작성하세요. "
        "사실에 없는 수치·사건을 지어내지 마세요.\n\n"
        f"[사실]\n{facts_block}\n\n"
        f"[시그널]\n{signals_block}\n\n"
        "[작성 규칙]\n"
        "- 출력은 JSON 하나만. 코드펜스·설명 문장 금지.\n"
        "- thesis: 이 종목이 왜 지금 주목되는지 2문장 이하.\n"
        "- perspectives.technical: 기술적 관점 1문장 이하.\n"
        "- perspectives.fundamental: 펀더멘털 관점 1문장 이하.\n"
        "- perspectives.news_context: 뉴스 맥락 1문장 이하"
        "(news_match_type이 none이면 null).\n"
        '- risk: 이 논지가 틀릴 구체적 조건 1문장'
        '("투자 판단은 신중히" 류 막연한 면책 문구 금지).\n'
        "- 사실이 부족해 확실치 않은 관점은 반드시 JSON null(문자열 \"null\" 아님).\n\n"
        "[출력 스키마]\n"
        '{"thesis": string|null, "perspectives": {"technical": string|null, '
        '"fundamental": string|null, "news_context": string|null}, '
        '"risk": string|null}\n'
    )
