"""ClaimEvidence 일일 생사 판정 서비스 (RECON-SWAP-0813 PART 1, v0).

Claim에 부착된 근거(ClaimEvidence) 각각을 as_of 기준으로 alive/dead/expired/unknown
판정한다. 순수 함수 — DB 쓰기 없음, LLM 호출 없음.

자동형 유예 연속성: 별도 "위반 이력" 테이블을 신설하지 않고, 매 호출 시
IndicatorReading 이력에서 연속 위반 거래일 수를 재계산한다(신규 상태 저장 최소화).
"""
from datetime import timedelta

from django.utils import timezone

from apps.monitor.models.evidence import ClaimEvidence
from apps.monitor.services.technical import score_indicator_dispatch

ALIVE = "alive"
DEAD = "dead"
EXPIRED = "expired"
UNKNOWN = "unknown"

_VALIDATED_STATUSES = ["ok", "extreme_jump_allowed"]


def _is_violation(raw_z, operator, threshold):
    """operator+threshold 조건을 raw_z가 만족하지 못하면 위반(True)."""
    if raw_z is None or threshold is None:
        return True
    if operator == ClaimEvidence.Operator.GTE:
        return not (raw_z >= threshold)
    if operator == ClaimEvidence.Operator.LTE:
        return not (raw_z <= threshold)
    if operator == ClaimEvidence.Operator.GT:
        return not (raw_z > threshold)
    if operator == ClaimEvidence.Operator.LT:
        return not (raw_z < threshold)
    return False


def _reading_dates(indicator, as_of_date):
    """indicator의 유효 판독 거래일(중복 제거, 최신순). DISTINCT+ORDER BY 컬럼 불일치를
    피하려 파이썬에서 dedupe(값 정렬은 이미 -asof이므로 순서 보존됨)."""
    qs = (
        indicator.readings.filter(
            validation_status__in=_VALIDATED_STATUSES,
            asof__date__lte=as_of_date,
        )
        .order_by("-asof")
        .values_list("asof", flat=True)
    )
    seen = set()
    dates = []
    for ts in qs:
        d = ts.date() if hasattr(ts, "date") else ts
        if d not in seen:
            seen.add(d)
            dates.append(d)
    return dates


def _judge_auto(evidence, as_of_date):
    """자동형: 최신 스코어가 불충분(is_sufficient=False)/indicator=null이면 판정 보류(unknown).

    그 외에는 as_of부터 과거로 거래일별 재채점 → 연속 위반 거래일 수(dead_streak_days)를
    센다. grace_days 이내면 alive(유예 중), 초과하면 dead.
    """
    base = {"evidence_id": evidence.id, "kind": ClaimEvidence.Kind.AUTO}
    indicator = evidence.indicator
    if indicator is None:
        return {**base, "status": UNKNOWN, "dead_streak_days": 0}

    latest = score_indicator_dispatch(indicator, as_of_date=as_of_date)
    if not latest.get("is_sufficient", False):
        return {**base, "status": UNKNOWN, "dead_streak_days": 0}

    streak = 0
    for d in _reading_dates(indicator, as_of_date):
        scored = score_indicator_dispatch(indicator, as_of_date=d)
        if not scored.get("is_sufficient", False):
            break
        if _is_violation(scored.get("raw_z"), evidence.operator, evidence.threshold):
            streak += 1
        else:
            break

    status = ALIVE if streak <= evidence.grace_days else DEAD
    return {**base, "status": status, "dead_streak_days": streak}


def _judge_manual(evidence, as_of_date):
    """수동형: last_confirmed_at(없으면 created_at) + recheck_period_days < as_of면 expired."""
    base = {"evidence_id": evidence.id, "kind": ClaimEvidence.Kind.MANUAL}
    baseline = evidence.last_confirmed_at or evidence.created_at.date()
    due = baseline + timedelta(days=evidence.recheck_period_days)
    if due < as_of_date:
        elapsed = (as_of_date - baseline).days
        return {**base, "status": EXPIRED, "dead_streak_days": elapsed}
    return {**base, "status": ALIVE, "dead_streak_days": 0}


def judge_claim_evidences(claim, as_of_date=None):
    """claim.evidences 전부를 as_of 기준으로 판정해 dict 목록 반환. DB 쓰기 없음."""
    if as_of_date is None:
        as_of_date = timezone.localdate()

    results = []
    for evidence in claim.evidences.select_related("indicator").order_by("created_at"):
        if evidence.kind == ClaimEvidence.Kind.AUTO:
            results.append(_judge_auto(evidence, as_of_date))
        else:
            results.append(_judge_manual(evidence, as_of_date))
    return results
