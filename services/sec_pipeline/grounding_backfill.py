"""SEC β G1 — grounding 백필 (dry-run 분포 + 실기록).

미검증(`grounding_status IS NULL`) evidence 전건을 원문(raw store)과 매칭해 판정 기록.
- **dry-run(기본)**: 쓰기 0건, 판정 4종 분포만 집계·리포트.
- write: `select_for_update(skip_locked=True)` 배치(SEC 파이프라인 기존 규율) + `update_fields`.

결정론 V-A — LLM 0콜(`ground_evidence` 경유).
"""
import logging

from django.db import transaction
from django.utils import timezone

from services.sec_pipeline.grounding import ground_evidence
from services.sec_pipeline.models import SupplyChainEvidence

logger = logging.getLogger(__name__)

WRITE_BATCH_SIZE = 500


def build_source_text(raw_doc) -> str:
    """추출에 사용된 10-K 원문 = item 1/1a/7 텍스트 결합. 소스 부재 시 빈 문자열."""
    if raw_doc is None:
        return ""
    parts = [raw_doc.item_1_text, raw_doc.item_1a_text, raw_doc.item_7_text]
    return "\n".join(p for p in parts if p)


def _empty_tally() -> dict:
    return {"verified": 0, "normalized_match": 0, "not_found": 0, "missing_source": 0}


def run_grounding_backfill(dry_run: bool = True) -> dict:
    """미검증 evidence 전건 접지 판정. dry_run=True면 쓰기 0건·분포만."""
    tally = _empty_tally()

    if dry_run:
        qs = (
            SupplyChainEvidence.objects.filter(grounding_status__isnull=True)
            .select_related("source_document")
            .iterator()
        )
        for ev in qs:
            status = ground_evidence(
                ev.evidence_text, build_source_text(ev.source_document)
            ).status
            tally[status] += 1
    else:
        while True:
            with transaction.atomic():
                batch = list(
                    SupplyChainEvidence.objects.filter(grounding_status__isnull=True)
                    .select_related("source_document")
                    .select_for_update(skip_locked=True)[:WRITE_BATCH_SIZE]
                )
                if not batch:
                    break
                now = timezone.now()
                for ev in batch:
                    result = ground_evidence(
                        ev.evidence_text, build_source_text(ev.source_document)
                    )
                    ev.grounding_status = result.status
                    ev.grounding_method = result.method
                    ev.grounded_at = now
                    tally[result.status] += 1
                SupplyChainEvidence.objects.bulk_update(
                    batch, ["grounding_status", "grounding_method", "grounded_at"]
                )

    total = sum(tally.values())
    logger.info(
        "grounding backfill %s: total=%d %s",
        "dry-run" if dry_run else "write",
        total,
        tally,
    )
    return {"dry_run": dry_run, "total": total, "distribution": tally}
