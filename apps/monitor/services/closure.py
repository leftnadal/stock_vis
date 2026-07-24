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


def is_expired_scenario(claim, as_of):
    """매수 시나리오가 '기한만료'인가 — 진입가 있고, 기한 경과했고, 진입 미도달.

    (D-TIMING-DECISIONS-5 ④-B) entry_price 없는 구 가설은 대상 아님(EXPIRED은 진입 개념 전제).
    (D-HOLD-DECISIONS 부속) hold 모드는 진입 개념 없음 → EXPIRED 제안 대상 아님.
    """
    return bool(
        claim.scenario_type != Claim.ScenarioType.HOLD
        and claim.entry_price is not None
        and claim.deadline is not None
        and claim.deadline < as_of
        and claim.entry_reached_at is None
    )


def is_hold_deadline_passed(claim, as_of):
    """보유 관리 시나리오의 기한 경과 여부 (D-HOLD-DECISIONS 부속).

    hold는 진입 개념이 없어 EXPIRED이 아니라 '만료 알림 1회'만 — 이 판정으로 게이트한다.
    """
    return bool(
        claim.scenario_type == Claim.ScenarioType.HOLD
        and claim.deadline is not None
        and claim.deadline < as_of
    )


def propose_verdict(overall_score, *, expired=False):
    """종합점수 → 제안 판정 (③). 순수 함수.

    만료 분기(④-B): 기존 밴드 로직 **앞단** — expired=True면 EXPIRED 제안(그 외 기존 불변).
    """
    if expired:
        return Claim.ProposedVerdict.EXPIRED
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


def _build_payload(monitor, score, claim=None):
    """동결 payload — 지표별 최종값·달위상·스파크라인 시리즈.

    가격 시나리오 마감(TIMING-P1 ⑤): claim 가격 있으면 close·손익률·최종 zone additive 동결.
    """
    from apps.monitor.services.sparkline import score_series
    from apps.monitor.services.state_machine import score_to_phase

    indicators = [
        {"id": str(i.id), "name": i.name, "latest_value": _latest_indicator_value(i)}
        for i in monitor.indicators.filter(is_active=True)
    ]
    payload = {
        "overall_score": score,
        "phase": score_to_phase(score),
        "indicators": indicators,
        "sparkline": score_series(monitor),
    }

    # 가격 시나리오 동결 (앵커=hold면 매입가, 그 외 진입가 — 있을 때만, additive)
    if claim is not None:
        from apps.monitor.services.price_zone import zone_anchor
        from apps.monitor.services.price_zone import resolve_zone
        from apps.monitor.services.scenario import latest_close

        anchor = zone_anchor(claim)
        if anchor is not None:
            close = latest_close(monitor.target_ref)
            anchor_f = float(anchor)
            pnl_pct = (
                (close - anchor_f) / anchor_f * 100.0
                if (close is not None and anchor_f)
                else None
            )
            is_hold = claim.scenario_type == Claim.ScenarioType.HOLD
            scenario_freeze = {
                "close_price": close,
                # entry_price 키는 하위호환 유지(앵커 값) — 소비처 계약 불변.
                "entry_price": anchor_f,
                "pnl_pct": round(pnl_pct, 4) if pnl_pct is not None else None,
                "zone": resolve_zone(
                    close, anchor, claim.target_price, claim.stop_price
                ),
                "scenario_type": claim.scenario_type,
            }
            if is_hold:
                # 보유 기간 사후분석 (D-HOLD-DECISIONS 5) — purchase_date 있으면 동결.
                scenario_freeze["purchase_price"] = anchor_f
                scenario_freeze["purchase_date"] = (
                    claim.purchase_date.isoformat() if claim.purchase_date else None
                )
                if claim.purchase_date:
                    scenario_freeze["holding_days"] = (
                        timezone.localdate() - claim.purchase_date
                    ).days
            payload["scenario"] = scenario_freeze
    return payload


@transaction.atomic
def close_claim(claim, *, final_verdict, factor_tags=None, retro_memo="",
                indicator_results=None, user=None):
    """가설 마감 (원자적). 반환 = 마감된 Claim.

    raises: AlreadyClosedError(재마감), ClosureValidationError(잘못된 입력).
    """
    if claim.outcome != Claim.Outcome.PENDING:
        raise AlreadyClosedError("이미 마감된 시나리오입니다.")

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

    expired = is_expired_scenario(claim, timezone.localdate())
    claim.proposed_verdict = propose_verdict(score, expired=expired)
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
        claim=claim, overall_score=score, payload=_build_payload(monitor, score, claim=claim)
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
