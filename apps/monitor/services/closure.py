"""가설 마감 서비스 (MON-CLOSE-UI Phase 1).

- propose_verdict: 종합점수 → 제안 판정 밴드 매핑(③, 순수 함수, 상수화).
- current_overall_score: 마감 시점 종합점수(읽기 전용, 최신 스냅샷 = 카드와 동일 소스).
- close_claim: 원자적 마감 — 가드·제안·판정 저장·지표별 결과·동결 스냅샷(⑤ state_machine 불변).
"""
import logging

from django.db import transaction
from django.utils import timezone

from apps.monitor.models import (
    Claim,
    ClaimIndicatorResult,
    ClosureSnapshot,
)

logger = logging.getLogger(__name__)

# ③ 제안 밴드: overall_score∈[-1,1]를 3등분(대칭·무편향). 재튜닝 시 이 두 상수만.
# 백로그: 마감 ≥20건 후 실분포로 재조정.
VERDICT_HI = 0.333
VERDICT_LO = -0.333

# 최종 판정으로 허용되는 값(INCONCLUSIVE는 엣지 — 버튼 미노출, close 액션 거부).
FINAL_VERDICT_CHOICES = frozenset(
    {Claim.Outcome.VALIDATED, Claim.Outcome.PARTIAL, Claim.Outcome.INVALIDATED}
)


class ClosureError(Exception):
    """마감 처리 오류 베이스."""


class AlreadyClosedError(ClosureError):
    """이미 마감된 가설 재마감 시도 (→ 409)."""


class ClosureValidationError(ClosureError):
    """잘못된 입력 (→ 400)."""


def propose_verdict(overall_score):
    """종합점수 → 제안 판정 (③). 순수 함수."""
    if overall_score >= VERDICT_HI:
        return Claim.ProposedVerdict.VALIDATED
    if overall_score <= VERDICT_LO:
        return Claim.ProposedVerdict.INVALIDATED
    return Claim.ProposedVerdict.PARTIAL


def current_overall_score(monitor):
    """마감 시점 종합점수(읽기 전용). 최신 스냅샷 = FE 카드 latest_score와 동일 소스."""
    snap = monitor.snapshots.order_by("-asof_date").first()
    return snap.overall_score if snap else 0.0


def _latest_indicator_value(indicator):
    r = indicator.readings.order_by("-asof").values_list("value", flat=True).first()
    return r


def _build_payload(monitor, score):
    """동결 payload — 지표별 최종값·달위상·스파크라인 시리즈."""
    from apps.monitor.services.sparkline import score_series
    from apps.monitor.services.state_machine import score_to_phase

    indicators = [
        {"id": str(i.id), "name": i.name, "latest_value": _latest_indicator_value(i)}
        for i in monitor.indicators.filter(is_active=True)
    ]
    return {
        "overall_score": score,
        "phase": score_to_phase(score),
        "indicators": indicators,
        "sparkline": score_series(monitor),
    }


@transaction.atomic
def close_claim(claim, *, final_verdict, factor_tags=None, retro_memo="",
                indicator_results=None, user=None):
    """가설 마감 (원자적). 반환 = 마감된 Claim.

    raises: AlreadyClosedError(재마감), ClosureValidationError(잘못된 입력).
    """
    if claim.outcome != Claim.Outcome.PENDING:
        raise AlreadyClosedError("이미 마감된 가설입니다.")

    if final_verdict not in FINAL_VERDICT_CHOICES:
        raise ClosureValidationError(
            f"final_verdict는 {sorted(FINAL_VERDICT_CHOICES)} 중 하나여야 합니다."
        )

    monitor = claim.monitor
    valid_tags = set(Claim.FactorTag.values)
    factor_tags = factor_tags or []
    for t in factor_tags:
        if t not in valid_tags:
            raise ClosureValidationError(f"허용되지 않은 factor_tag: {t}")

    # 지표별 결과 검증 (이 monitor 소속 지표만)
    valid_results = set(ClaimIndicatorResult.Result.values)
    monitor_ind_ids = {str(i) for i in monitor.indicators.values_list("id", flat=True)}
    rows = []
    seen = set()
    for ir in (indicator_results or []):
        iid = str(ir.get("indicator_id"))
        res = ir.get("result")
        if iid not in monitor_ind_ids:
            raise ClosureValidationError(f"이 모니터 소속이 아닌 지표: {iid}")
        if res not in valid_results:
            raise ClosureValidationError(f"허용되지 않은 result: {res}")
        if iid in seen:
            raise ClosureValidationError(f"지표 중복 결과: {iid}")
        seen.add(iid)
        rows.append(ClaimIndicatorResult(claim=claim, indicator_id=iid, result=res))

    score = current_overall_score(monitor)

    claim.proposed_verdict = propose_verdict(score)
    claim.outcome = final_verdict
    claim.status = Claim.Status.RESOLVED
    claim.resolved_by = user
    claim.resolved_at = timezone.now()
    claim.factor_tags = factor_tags
    claim.retro_memo = retro_memo or ""
    claim.save(update_fields=[
        "proposed_verdict", "outcome", "status", "resolved_by",
        "resolved_at", "factor_tags", "retro_memo",
    ])

    if rows:
        ClaimIndicatorResult.objects.bulk_create(rows)

    ClosureSnapshot.objects.create(
        claim=claim, overall_score=score, payload=_build_payload(monitor, score)
    )

    logger.info(
        "claim 마감: claim=%s verdict=%s proposed=%s score=%.4f indicators=%d",
        claim.id, final_verdict, claim.proposed_verdict, score, len(rows),
    )
    return claim


def close_preview(claim):
    """마감 모달 프리필 (읽기 전용, 상태 변경 없음)."""
    monitor = claim.monitor
    score = current_overall_score(monitor)
    return {
        "proposed_verdict": propose_verdict(score),
        "overall_score": score,
        "indicators": [
            {"id": str(i.id), "name": i.name, "latest_value": _latest_indicator_value(i)}
            for i in monitor.indicators.filter(is_active=True)
        ],
    }
