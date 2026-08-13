"""CS-P2-8K: 8-K 상대 기업 추출 + 분류 (Gemini 2.5 Flash).

item 1.01(중요계약)/2.01(인수·처분) 본문에서 외부 상대 기업을 추출하고 관계를 분류.
분류 목적 = 금융계약(상대=은행/대주/수탁자) 노이즈를 상업/공급/M&A 실관계와 구분.

카테고리:
  commercial  → 상업 파트너십/협업/JV/유통    → PARTNER_WITH (착지)
  supply      → 공급/제조/구매 계약           → SUPPLIES_TO  (착지)
  acquisition → 인수/합병/스핀오프/처분(2.01)  → ACQUIRED     (착지, 신규 유형)
  financing   → 신용/대출/채권/인수주선(은행)  → (미착지, 원문만 보존)
  unclear     → 지목되나 관계 애매             → (미착지, 카운트만 — 강행 착지 금지)

순수 파싱(item 본문 추출)은 DB·LLM 무의존 → 단위 테스트 대상.
LLM 호출은 기존 Track A extractor 패턴 IDENTICAL(complete() 경유, thinking_budget=0, json).
"""

import json
import logging
import re

logger = logging.getLogger(__name__)

LAND_CATEGORIES = {"commercial", "supply", "acquisition"}
CATEGORY_TO_RELATION = {
    "commercial": "PARTNER_WITH",
    "supply": "SUPPLIES_TO",
    "acquisition": "ACQUIRED",
}
VALID_CATEGORIES = LAND_CATEGORIES | {"financing", "unclear"}

# item 마커: "Item 1.01" ~ 다음 "Item N.NN" 직전
_ITEM_RE = re.compile(r"Item\s+(\d\.\d{2})", re.IGNORECASE)


def extract_item_bodies(text, target_items):
    """8-K 원문에서 target_items 각 item 본문 발췌 → {item_code: body_text}.

    "Item X.XX" 마커부터 다음 "Item Y.YY" 마커 직전까지. 순수 함수(DB·LLM 무의존).
    """
    text = " ".join(text.split())  # 공백 정규화
    marks = [(m.group(1), m.start()) for m in _ITEM_RE.finditer(text)]
    bodies = {}
    for i, (code, start) in enumerate(marks):
        if code not in target_items:
            continue
        end = marks[i + 1][1] if i + 1 < len(marks) else len(text)
        body = text[start:end].strip()
        # 같은 item이 여러 번(드묾) 나오면 이어붙임
        bodies[code] = (bodies.get(code, "") + "\n" + body).strip() if code in bodies else body
    return bodies


PROMPT = """You are analyzing sections of an SEC Form 8-K filed by {company_name} (ticker: {symbol}).
Identify each EXTERNAL counterparty company named in a material relationship, and classify it.

Category definitions (choose exactly one per counterparty):
- "commercial": partnership, collaboration, joint venture, distribution, licensing, or a general commercial agreement.
- "supply": supply, manufacturing, procurement, or purchase agreement (a supplier/customer relationship).
- "acquisition": M&A, merger, acquisition, spin-off, or disposition of a business (typically Item 2.01).
- "financing": credit agreement, term loan, revolving facility, notes/bond issuance, indenture, or underwriting — where the counterparty is a BANK, LENDER, ADMINISTRATIVE/SYNDICATION AGENT, TRUSTEE, or UNDERWRITER. Classify ALL banks/lenders/agents/trustees here, never as commercial/supply.
- "unclear": a company is named but the relationship type cannot be confidently determined.

Rules:
- Only EXTERNAL companies. Exclude the filer ({company_name}) itself. For a spin-off, the spun-off entity IS a valid "acquisition" counterparty.
- Exclude individuals (people), governments, and stock exchanges.
- For each counterparty give a confidence 0.0-1.0 that your category is correct.
- evidence must be a <=200 character verbatim quote naming the counterparty.

Return ONLY JSON:
{{"counterparties":[{{"name":"<company>","category":"<category>","confidence":<0-1>,"item":"<1.01|2.01>","evidence":"<quote>"}}]}}
If none, return {{"counterparties":[]}}.

Filing sections:
{sections}
"""


def extract_counterparties(symbol, company_name, item_bodies, complete_fn=None):
    """item_bodies({code:text}) → LLM → 분류된 counterparties 리스트.

    complete_fn 주입 가능(테스트 mock). 기본 = packages.shared.llm.complete.
    반환: {"counterparties":[{name,category,confidence,item,evidence}...]} 또는 error.
    """
    if not item_bodies:
        return {"counterparties": []}
    sections = "\n\n---\n\n".join(
        f"[Item {code}]\n{body[:6000]}" for code, body in item_bodies.items()
    )
    prompt = PROMPT.format(company_name=company_name, symbol=symbol, sections=sections)

    try:
        if complete_fn is None:
            from google.genai import types

            from packages.shared.llm import complete

            def complete_fn(p):
                return complete(
                    p,
                    provider="gemini",
                    model="gemini-2.5-flash",
                    temperature=0.1,
                    response_format="json",
                    extra={"thinking_config": types.ThinkingConfig(thinking_budget=0)},
                )

        response = complete_fn(prompt)
        text = response.text if getattr(response, "text", None) else "{}"
        result = json.loads(text)
        cps = result.get("counterparties", []) if isinstance(result, dict) else []
        # 정규화 + 검증
        clean = []
        for c in cps:
            if not isinstance(c, dict):
                continue
            name = (c.get("name") or "").strip()
            cat = (c.get("category") or "unclear").strip().lower()
            if not name:
                continue
            if cat not in VALID_CATEGORIES:
                cat = "unclear"
            clean.append(
                {
                    "name": name,
                    "category": cat,
                    "confidence": float(c.get("confidence") or 0.0),
                    "item": (c.get("item") or "").strip(),
                    "evidence": (c.get("evidence") or "")[:200],
                }
            )
        return {"counterparties": clean}
    except json.JSONDecodeError as e:
        logger.error(f"{symbol}: 8-K JSON parse error: {e}")
        return {"counterparties": [], "error": f"JSON parse: {e}"}
    except Exception as e:
        logger.error(f"{symbol}: 8-K extraction error: {e}")
        return {"counterparties": [], "error": str(e)}
