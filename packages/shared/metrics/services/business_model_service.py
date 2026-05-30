"""
SEC-PR-13: Business Model 서비스 레이어.

다른 앱이 sec_pipeline.models를 직접 import하지 않고,
이 서비스를 통해 접근한다 (원칙 5).

⚠️ for_api가 confidence 숫자 노출 경계의 유일한 게이트 (원칙 6).
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_business_model(symbol: str, for_api: bool = False) -> Optional[dict]:
    """
    최신 Business Model Snapshot 조회.

    Args:
        symbol: 종목 심볼
        for_api: True → overall_confidence 제거, confidence_grade만

    Returns:
        dict 또는 None
    """
    from sec_pipeline.models import BusinessModelSnapshot

    snapshot = (
        BusinessModelSnapshot.objects.filter(symbol_id=symbol.upper())
        .order_by("-as_of_date")
        .first()
    )

    if not snapshot:
        return None

    result = {
        "symbol": symbol.upper(),
        "as_of_date": str(snapshot.as_of_date),
        "direct_customer_contact": snapshot.direct_customer_contact,
        "contract_model": snapshot.contract_model,
        "recurring_revenue_signal": snapshot.recurring_revenue_signal,
        "channel_dependency": snapshot.channel_dependency,
        "customer_concentration": snapshot.customer_concentration,
        "confidence_grade": snapshot.confidence_grade,
        "prompt_version": snapshot.prompt_version,
    }

    if not for_api:
        # 내부용: 숫자 포함
        result["overall_confidence"] = float(snapshot.overall_confidence)

    return result


def get_business_model_evidence(symbol: str, field_name: str = None) -> list:
    """
    Business Model 근거 문장 조회.

    Args:
        symbol: 종목 심볼
        field_name: 특정 필드만 (None이면 전체)

    Returns:
        list[dict]
    """
    from sec_pipeline.models import BusinessModelSnapshot, BusinessModelEvidence

    snapshot = (
        BusinessModelSnapshot.objects.filter(symbol_id=symbol.upper())
        .order_by("-as_of_date")
        .first()
    )

    if not snapshot:
        return []

    qs = BusinessModelEvidence.objects.filter(snapshot=snapshot)
    if field_name:
        qs = qs.filter(field_name=field_name)

    return [
        {
            "field_name": ev.field_name,
            "evidence_text": ev.evidence_text,
            "confidence": float(ev.confidence),
        }
        for ev in qs
    ]


def is_recurring_business(symbol: str) -> Optional[bool]:
    """
    사업이 반복 매출 기반인지 판단.

    Returns:
        True (subscription/high), False (one_time/low), None (판단 불가)
    """
    bm = get_business_model(symbol)
    if not bm:
        return None

    contract = bm.get("contract_model", "unknown")
    recurring = bm.get("recurring_revenue_signal", "unknown")

    if contract == "subscription" or recurring == "high":
        return True
    elif contract == "one_time" and recurring == "low":
        return False

    return None
