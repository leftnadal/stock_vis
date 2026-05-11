"""
SEC-PR-12: Track B 추출 결과 검증 + DB 저장.
"""

import logging

from .prompts import PROMPT_VERSION_TRACK_B

logger = logging.getLogger(__name__)

# 필드별 허용 값
FIELD_ALLOWED_VALUES = {
    'direct_customer_contact': {'direct', 'indirect', 'hybrid', 'unknown'},
    'contract_model': {'subscription', 'one_time', 'hybrid', 'unknown'},
    'recurring_revenue_signal': {'high', 'medium', 'low', 'unknown'},
    'channel_dependency': {'high_dependency', 'moderate', 'low_dependency', 'unknown'},
    'customer_concentration': {'concentrated', 'diversified', 'unknown'},
}

BM_FIELDS = list(FIELD_ALLOWED_VALUES.keys())


def validate_business_model_result(result: dict) -> dict:
    """
    LLM 추출 결과 검증.

    Returns:
        검증된 dict {field_name: {value, evidence_text, confidence}}
    """
    validated = {}

    for field in BM_FIELDS:
        field_data = result.get(field, {})
        if not isinstance(field_data, dict):
            validated[field] = {'value': 'unknown', 'evidence_text': '', 'confidence': 0.0}
            continue

        value = field_data.get('value', 'unknown')
        evidence = (field_data.get('evidence_text') or '')[:200]
        confidence = float(field_data.get('confidence', 0))

        # 허용 값 검증
        if value not in FIELD_ALLOWED_VALUES[field]:
            value = 'unknown'

        validated[field] = {
            'value': value,
            'evidence_text': evidence,
            'confidence': min(max(confidence, 0.0), 1.0),
        }

    return validated


def calculate_confidence_grade(overall_confidence: float) -> str:
    """overall_confidence → grade."""
    if overall_confidence >= 0.8:
        return 'high'
    elif overall_confidence >= 0.6:
        return 'medium'
    return 'low'


def save_business_model_snapshot(validated: dict, document, symbol: str):
    """
    검증된 결과를 BusinessModelSnapshot + BusinessModelEvidence로 저장.
    """
    from .models import BusinessModelSnapshot, BusinessModelEvidence
    from stocks.models import Stock

    stock = Stock.objects.filter(symbol=symbol.upper()).first()
    if not stock:
        logger.error(f"Stock not found: {symbol}")
        return None

    # overall_confidence: 5개 confidence 평균
    confidences = [validated[f]['confidence'] for f in BM_FIELDS]
    overall = sum(confidences) / len(confidences) if confidences else 0

    snapshot, created = BusinessModelSnapshot.objects.update_or_create(
        symbol=stock,
        source_document=document,
        defaults={
            'as_of_date': document.filing_date,
            'direct_customer_contact': validated['direct_customer_contact']['value'],
            'contract_model': validated['contract_model']['value'],
            'recurring_revenue_signal': validated['recurring_revenue_signal']['value'],
            'channel_dependency': validated['channel_dependency']['value'],
            'customer_concentration': validated['customer_concentration']['value'],
            'overall_confidence': overall,
            'confidence_grade': calculate_confidence_grade(overall),
            'prompt_version': PROMPT_VERSION_TRACK_B,
        }
    )

    # Evidence 저장
    if created:
        evidences = []
        for field in BM_FIELDS:
            field_data = validated[field]
            if field_data['evidence_text']:
                evidences.append(BusinessModelEvidence(
                    snapshot=snapshot,
                    field_name=field,
                    evidence_text=field_data['evidence_text'],
                    confidence=field_data['confidence'],
                ))
        if evidences:
            BusinessModelEvidence.objects.bulk_create(evidences)

    logger.info(
        f"{symbol}: BM snapshot {'created' if created else 'updated'} "
        f"(grade={snapshot.confidence_grade})"
    )
    return snapshot
