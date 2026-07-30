"""관계 도메인 태깅 훅 태스크 (⑳-3 S2-B Slice 4) — 이벤트 구동(beat 미사용).

SEC 관계 신규/미태깅 생성 시 sec_pipeline이 이 태스크를 큐잉한다. 코어=domain_tagging
(커맨드와 동일 단일 소스, 복제 없음). draft·machine_check만 기록 — 승인본 미기록.

현재 SEC 유입 0이므로 훅은 대기 상태가 정상(발화 없음).
"""

import logging

from celery import shared_task

from apps.chain_sight.models import RelationConfidence
from apps.chain_sight.services.domain_tagging import SEC_RELATION_TYPES, tag_one

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
