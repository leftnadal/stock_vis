"""
SEC-PR-3: Track A 추출 결과 검증 + DB 저장

- 자기 참조 제거
- confidence < 0.3 제거
- target 2자 미만 제거
- relationship_type 허용 목록 외 → DEPENDS_ON 폴백
- confidence → grade 자동 계산
"""

import logging
from django.utils import timezone

from .prompts import PROMPT_VERSION

logger = logging.getLogger(__name__)

ALLOWED_RELATIONSHIP_TYPES = {
    'SUPPLIES_TO', 'CUSTOMER_OF', 'PARTNER_WITH',
    'DEPENDS_ON', 'COMPETES_WITH',
}

# LLM이 회사명 대신 추출하는 제네릭 용어 — 관계로 저장하지 않음
GENERIC_COMPANY_TERMS = {
    'third parties', 'third-party', 'suppliers', 'customers',
    'hyperscalers', 'oems', 'distributors', 'vendors', 'partners',
    'competitors', 'resellers', 'developers', 'retailers',
    'manufacturers', 'service providers', 'contract manufacturers',
    'system integrators', 'business partners', 'cable companies',
    'other partners', 'other resellers', 'other manufacturers',
    'external experts', 'web agencies', 'money market funds',
    'authorized replicators', 'hosting service providers',
    'independent software vendors', 'licensing solution partners',
    'identity vendors', 'security solution vendors',
    'value-added resellers', 'retail outlets',
    'mobile communications companies', 'incumbent telephone companies',
    'device manufacturers', 'chip manufacturers',
    'pharmaceutical manufacturers',
}

# 제네릭 접미사 — "independent ~ distributors", "Windows OEMs" 등 패턴 매칭
_GENERIC_SUFFIXES = (
    'oems', 'vendors', 'partners', 'distributors', 'resellers',
    'manufacturers', 'providers', 'carriers', 'companies', 'retailers',
    'integrators', 'advisors',
)


def _is_generic_term(name: str) -> bool:
    """회사명이 아닌 제네릭 용어인지 판별."""
    lower = name.lower().strip()
    if lower in GENERIC_COMPANY_TERMS:
        return True
    for suffix in _GENERIC_SUFFIXES:
        if lower.endswith(suffix):
            return True
    if lower.startswith('third-party') or lower.startswith('third parties'):
        return True
    return False


def validate_supply_chain_result(result: dict, source_symbol: str) -> list:
    """
    LLM 추출 결과 검증.

    Args:
        result: {'relationships': [...]}
        source_symbol: 원본 기업 심볼

    Returns:
        검증 통과한 관계 리스트
    """
    validated = []
    source_upper = source_symbol.upper()

    for rel in result.get('relationships', []):
        target_name = (rel.get('target_company_name') or '').strip()
        confidence = float(rel.get('confidence', 0))
        rel_type = (rel.get('relationship_type') or '').upper()
        evidence = (rel.get('evidence_text') or '').strip()

        # 자기 참조 제거
        if target_name.upper() == source_upper:
            continue

        # confidence < 0.3 제거
        if confidence < 0.3:
            continue

        # target 2자 미만 제거
        if len(target_name) < 2:
            continue

        # 제네릭 용어 제거 ("third parties", "suppliers" 등)
        if _is_generic_term(target_name):
            continue

        # relationship_type 허용 목록 외 → DEPENDS_ON 폴백
        if rel_type not in ALLOWED_RELATIONSHIP_TYPES:
            rel_type = 'DEPENDS_ON'

        # evidence 길이 제한 (300자)
        if len(evidence) > 300:
            evidence = evidence[:297] + '...'

        validated.append({
            'target_company_name': target_name,
            'relationship_type': rel_type,
            'evidence_text': evidence,
            'system_confidence': confidence,
            'confidence_grade': calculate_confidence_grade(confidence),
            'direction': rel.get('direction', 'inbound'),
        })

    logger.info(
        f"{source_symbol}: {len(result.get('relationships', []))} raw → "
        f"{len(validated)} validated"
    )
    return validated


def calculate_confidence_grade(confidence: float) -> str:
    """confidence 숫자 → grade 변환 (API 노출용)."""
    if confidence >= 0.8:
        return 'high'
    elif confidence >= 0.6:
        return 'medium'
    return 'low'


def save_supply_chain_evidences(validated: list, document, source_symbol: str):
    """
    검증된 관계를 SupplyChainEvidence로 벌크 저장.

    Args:
        validated: validate_supply_chain_result() 반환값
        document: RawDocumentStore 인스턴스
        source_symbol: 원본 기업 심볼
    """
    from .models import SupplyChainEvidence
    from stocks.models import Stock

    source_stock = Stock.objects.filter(symbol=source_symbol.upper()).first()
    if not source_stock:
        logger.error(f"Stock not found: {source_symbol}")
        return []

    evidences = []
    for rel in validated:
        evidences.append(SupplyChainEvidence(
            source_document=document,
            source_company=source_stock,
            target_company=None,  # Phase 1.5 TickerMatcher에서 매칭
            target_company_name=rel['target_company_name'],
            relationship_type=rel['relationship_type'],
            evidence_text=rel['evidence_text'],
            system_confidence=rel['system_confidence'],
            confidence_grade=rel['confidence_grade'],
            neo4j_dirty=True,
            prompt_version=PROMPT_VERSION,
        ))

    created = SupplyChainEvidence.objects.bulk_create(evidences)
    logger.info(f"{source_symbol}: saved {len(created)} supply chain evidences")
    return created
