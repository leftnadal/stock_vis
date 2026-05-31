"""
SEC-PR-10: 관계 병합 로직.

같은 (source, target) 쌍에 대해 여러 source(sec_10k, news, peer_of 등)에서
관계가 발견되면 병합 규칙 적용.

⚠️ Phase 1에서 Neo4j에 직접 쓰지 않음. dirty sync가 sole writer.
⚠️ DQS 반환값에 내부용/사용자용 키 분리 (원칙 6).
"""

import logging

logger = logging.getLogger(__name__)

# 관계 구체성 점수 (높을수록 구체적)
RELATIONSHIP_SPECIFICITY = {
    "DEPENDS_ON": 1,
    "PARTNER_WITH": 2,
    "COMPETES_WITH": 3,
    "CUSTOMER_OF": 4,
    "SUPPLIES_TO": 5,
}

# 소스 신뢰도
SOURCE_RELIABILITY = {
    "sec_10k": 0.95,
    "institutional_holding": 0.90,
    "etf_peer": 0.85,
    "supply_chain_manual": 0.85,
    "llm_relation": 0.70,
    "co_mention_news": 0.65,
    "marketaux_news": 0.60,
}


def merge_relationship(existing: dict, new: dict) -> dict:
    """
    기존 관계와 새 관계 병합.

    Args:
        existing: {'rel_type': str, 'confidence': float, 'sources': list, ...}
        new: {'rel_type': str, 'confidence': float, 'source': str, ...}

    Returns:
        병합된 관계 dict
    """
    merged = dict(existing)

    # source 목록 축적
    sources = set(merged.get("sources", []))
    sources.add(new.get("source", ""))
    merged["sources"] = sorted(sources)

    # primary_type: 더 구체적인 타입 선택
    existing_spec = RELATIONSHIP_SPECIFICITY.get(merged.get("rel_type", ""), 0)
    new_spec = RELATIONSHIP_SPECIFICITY.get(new.get("rel_type", ""), 0)
    if new_spec > existing_spec:
        merged["rel_type"] = new["rel_type"]

    # confidence: bounded boosting (최대 0.99)
    existing_conf = merged.get("confidence", 0.5)
    new_conf = new.get("confidence", 0.5)
    boosted = existing_conf + (1 - existing_conf) * new_conf * 0.3
    merged["confidence"] = min(boosted, 0.99)

    # evidence facets 보존
    facets = merged.get("relation_facets", [])
    new_evidence = new.get("evidence_text", "")
    if new_evidence and new_evidence not in facets:
        facets.append(new_evidence)
    merged["relation_facets"] = facets[-5:]  # 최대 5개

    return merged


def calculate_edge_dqs(source_ticker: str, target_ticker: str) -> dict:
    """
    Edge Data Quality Score 계산.

    Returns:
        {
            # 내부용 (Admin/Intelligence만)
            '_sufficiency': float,
            '_diversity': float,
            '_reliability': float,
            '_dqs_total': float,
            # 사용자용 (API 노출)
            'source_count': int,
            'source_types': list[str],
        }
    """
    from .models import SupplyChainEvidence

    evidences = SupplyChainEvidence.objects.filter(
        source_company_id=source_ticker,
        target_company_id=target_ticker,
    )

    sources = set()
    total_reliability = 0.0

    for ev in evidences:
        source = "sec_10k"  # 현재 SEC pipeline만 있음
        sources.add(source)
        total_reliability += SOURCE_RELIABILITY.get(source, 0.5)

    count = evidences.count()
    if count == 0:
        return {
            "_sufficiency": 0,
            "_diversity": 0,
            "_reliability": 0,
            "_dqs_total": 0,
            "source_count": 0,
            "source_types": [],
        }

    # 충분성: evidence 개수 기반 (3개 이상이면 1.0)
    sufficiency = min(count / 3.0, 1.0)

    # 다양성: 소스 종류 기반 (3종류 이상이면 1.0)
    diversity = min(len(sources) / 3.0, 1.0)

    # 신뢰성: 평균 source reliability
    reliability = total_reliability / count if count else 0

    # 종합 DQS
    dqs_total = sufficiency * 0.3 + diversity * 0.3 + reliability * 0.4

    return {
        # 내부용
        "_sufficiency": round(sufficiency, 3),
        "_diversity": round(diversity, 3),
        "_reliability": round(reliability, 3),
        "_dqs_total": round(dqs_total, 3),
        # 사용자용 (원칙 6)
        "source_count": count,
        "source_types": sorted(sources),
    }
