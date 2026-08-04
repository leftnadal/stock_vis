"""관계 도메인 태깅 훅 태스크 (⑳-3 S2-B Slice 4) — 이벤트 구동(beat 미사용).

SEC 관계 신규/미태깅 생성 시 sec_pipeline이 이 태스크를 큐잉한다. 코어=domain_tagging
(커맨드와 동일 단일 소스, 복제 없음). draft·machine_check만 기록 — 승인본 미기록.

현재 SEC 유입 0이므로 훅은 대기 상태가 정상(발화 없음).
"""

import logging

from celery import shared_task

from apps.chain_sight.models import RelationConfidence
from apps.chain_sight.services.domain_tagging import (
    SEC_RELATION_TYPES,
    is_human_reviewed,
    tag_one,
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def tag_relation_domain_task(self, rc_id: int):
    """단건 SEC 관계 도메인 태깅 → draft/machine_check/status 기록(승인본 미기록)."""
    try:
        rc = RelationConfidence.objects.filter(
            id=rc_id, relation_type__in=SEC_RELATION_TYPES
        ).first()
        if rc is None:
            return {"skipped": "not-sec-or-missing", "rc_id": rc_id}
        # ⑳-3 S3-MINDMAP S1: 검수 verdict 보유분 보호 — 자동 태깅 덮어쓰기 금지.
        if is_human_reviewed(rc):
            return {"skipped": "human-reviewed", "rc_id": rc_id}
        if not rc.relation_basis_summary:
            return {"skipped": "no-basis", "rc_id": rc_id}

        from apps.market_pulse.llm.client import generate_with_circuit
        from packages.shared.stocks.models import Stock

        def llm_call(system, contents):
            resp = generate_with_circuit(system_instruction=system, contents=contents)
            return getattr(resp, "text", "") or ""

        target_name = (
            Stock.objects.filter(symbol=rc.symbol_b)
            .values_list("stock_name", flat=True).first() or ""
        )
        out = tag_one(
            symbol_a=rc.symbol_a, symbol_b=rc.symbol_b, center=rc.symbol_a,
            relation_type=rc.relation_type, basis=rc.relation_basis_summary,
            target_name=target_name, llm_call=llm_call,
        )
        RelationConfidence.objects.filter(id=rc_id).update(
            relation_domain_draft=out["draft"],
            domain_review_status=out["review_status"],
            domain_machine_check=out["machine_check"],
            # relation_domain(승인본)은 절대 미기록(검수=Phase 2, 하드 룰)
        )
        return {"rc_id": rc_id, "review_status": out["review_status"], "gate": out["gate_class"]}
    except Exception as exc:
        logger.warning(f"tag_relation_domain_task 실패 rc_id={rc_id}: {exc}")
        raise self.retry(exc=exc)


# ── L2 경로: 신규 PEER 유입 자동 태깅 (L2-ADOPT) ──
def _peer_terciles():
    """현 PEER 유니버스 pair_mcap 3분위 경계(t1,t2). 단건 훅 is_estimate 판정용."""
    from apps.chain_sight.management.commands.tag_peer_domains import compute_terciles
    from apps.chain_sight.services.peer_domain_tagging import PEER_RELATION_TYPES
    from packages.shared.stocks.models import Stock

    rows = list(
        RelationConfidence.objects.filter(relation_type__in=PEER_RELATION_TYPES)
        .exclude(domain_review_status="rejected")
        .values_list("symbol_a", "symbol_b")
    )
    syms = {a for a, _ in rows} | {b for _, b in rows}
    mcaps = dict(
        Stock.objects.filter(symbol__in=syms)
        .exclude(market_capitalization__isnull=True).exclude(market_capitalization=0)
        .values_list("symbol", "market_capitalization")
    )
    pair_mcaps = [
        min(float(mcaps[a]), float(mcaps[b]))
        for a, b in rows if a in mcaps and b in mcaps
    ]
    return compute_terciles(pair_mcaps)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def tag_peer_domain_task(self, rc_id: int):
    """단건 PEER 관계 L2 도메인 태깅 → draft/status/machine_check(승인본 미기록).

    거부권(grounded ≤ 0.2) 발동 시 status='rejected' → 서빙 시 업종 버킷 폴백.
    """
    try:
        from apps.chain_sight.management.commands.tag_peer_domains import tercile_of
        from apps.chain_sight.services.peer_adjudicator import load_dict
        from apps.chain_sight.services.peer_domain_tagging import (
            PEER_RELATION_TYPES,
            TAG_SOURCE,
            tag_peer_one,
        )
        from packages.shared.stocks.models import Stock

        rc = RelationConfidence.objects.filter(
            id=rc_id, relation_type__in=PEER_RELATION_TYPES
        ).first()
        if rc is None:
            return {"skipped": "not-peer-or-missing", "rc_id": rc_id}
        # 검수 verdict 보유분 보호(L1과 동일 가드).
        if is_human_reviewed(rc):
            return {"skipped": "human-reviewed", "rc_id": rc_id}
        # idempotent: 이미 L2-ADOPT 태깅됐으면 skip.
        mc = rc.domain_machine_check or {}
        if isinstance(mc, dict) and mc.get("source") == TAG_SOURCE:
            return {"skipped": "already-tagged", "rc_id": rc_id}

        a, b = rc.symbol_a, rc.symbol_b
        st = {
            s.symbol: s
            for s in Stock.objects.filter(symbol__in=[a, b]).only(
                "symbol", "stock_name", "industry", "description", "market_capitalization"
            )
        }
        sa, sb = st.get(a), st.get(b)
        ind_a = (sa.industry if sa else "") or ""
        ind_b = (sb.industry if sb else "") or ""
        same = None
        if ind_a and ind_b:
            same = ind_a.strip().lower() == ind_b.strip().lower()
        pair_mcap = None
        if sa and sb and sa.market_capitalization and sb.market_capitalization:
            pair_mcap = min(float(sa.market_capitalization), float(sb.market_capitalization))
        t1, t2 = _peer_terciles()
        terc = tercile_of(pair_mcap, t1, t2)

        def llm_call(system, contents):
            from apps.market_pulse.llm.client import generate_with_circuit
            # thinking_budget=512(D-L2-THINKING-BUDGET, 배치와 동일).
            resp = generate_with_circuit(
                system_instruction=system, contents=contents, thinking_budget=512
            )
            return getattr(resp, "text", "") or ""

        out = tag_peer_one(
            symbol_a=a, symbol_b=b,
            name_a=(sa.stock_name if sa else "") or "", name_b=(sb.stock_name if sb else "") or "",
            industry_a=ind_a, industry_b=ind_b,
            desc_a=(sa.description if sa else "") or "", desc_b=(sb.description if sb else "") or "",
            mcap_tercile=terc, industry_same=same, dct=load_dict(), llm_call=llm_call,
        )
        # 쌍 단위 — 방향 엣지 양쪽에 동일 태그(승인본 relation_domain 무접촉).
        from django.db.models import Q
        RelationConfidence.objects.filter(
            Q(symbol_a=a, symbol_b=b) | Q(symbol_a=b, symbol_b=a),
            relation_type__in=PEER_RELATION_TYPES,
        ).update(
            relation_domain_draft=out["draft"],
            domain_review_status=out["review_status"],
            domain_machine_check=out["machine_check"],
        )
        return {"rc_id": rc_id, "review_status": out["review_status"], "veto": out["veto"]}
    except Exception as exc:
        logger.warning(f"tag_peer_domain_task 실패 rc_id={rc_id}: {exc}")
        raise self.retry(exc=exc)
