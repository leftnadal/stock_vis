"""
CS-P1A Slice2: RelationConfidence.serving_layer 백필.

DECISIONS D-CS-REDESIGN-BEFORE-BASELINE 매핑표 기준:
  - SEC 4종(COMPETES_WITH·SUPPLIES_TO·PARTNER_WITH·DEPENDS_ON)·CO_MENTIONED → evidence
  - PEER_OF·PRICE_CORRELATED → context
  - PEER(2건) 등 그 외 → pending 유지(미분류)

기본 dry-run. 실제 쓰기는 --apply (병진 GO 게이트 뒤에만).
쓰기는 QuerySet.update()로 serving_layer 컬럼만 갱신 — save() 미호출이라
relation_status·last_observed_at·neo4j_dirty 무접촉(OUT 스코프: 기존 status 변경 금지 준수).
"""

from django.core.management.base import BaseCommand
from django.db.models import F

from apps.chain_sight.models import RelationConfidence

EVIDENCE_TYPES = [
    "COMPETES_WITH",
    "SUPPLIES_TO",
    "PARTNER_WITH",
    "DEPENDS_ON",
    "CO_MENTIONED",
]
CONTEXT_TYPES = ["PEER_OF", "PRICE_CORRELATED"]
# PEER(2건) 및 기타 = pending(default) 유지 — 디렉터 검수 대상.


class Command(BaseCommand):
    help = "RelationConfidence.serving_layer 백필 (매핑표 기준). 기본 dry-run, --apply로 실행."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="실제 쓰기(미지정=dry-run, 쓰기 0건).",
        )

    def handle(self, *args, **opts):
        # SCE-POLLUTION-CLEANUP(2026-08) 가드 이중화:
        #   (a) 자기루프(symbol_a==symbol_b)는 evidence 승격 금지 → excluded로 분류.
        #       모델 save() 가드는 신규 create만 막고 레거시 self-loop 갱신은 통과하므로,
        #       relation_type 기준 재분류가 self-loop를 evidence로 되돌리는 회귀를 여기서 차단.
        #   (b) 이미 excluded인 행(수동 무효화 = FTNT→DIS 등 오염 정제분)은 보존 —
        #       relation_type만 보고 evidence로 되돌리지 않는다.
        selfloop_filter = {"symbol_a": F("symbol_b")}
        ev_qs = (
            RelationConfidence.objects.filter(relation_type__in=EVIDENCE_TYPES)
            .exclude(**selfloop_filter)
            .exclude(serving_layer="excluded")
        )
        selfloop_qs = RelationConfidence.objects.filter(
            relation_type__in=EVIDENCE_TYPES, **selfloop_filter
        ).exclude(serving_layer="excluded")
        ctx_qs = (
            RelationConfidence.objects.filter(relation_type__in=CONTEXT_TYPES)
            .exclude(**selfloop_filter)
            .exclude(serving_layer="excluded")
        )
        pending_qs = RelationConfidence.objects.exclude(
            relation_type__in=EVIDENCE_TYPES + CONTEXT_TYPES
        )
        ev_n, sl_n, ctx_n, pend_n = (
            ev_qs.count(),
            selfloop_qs.count(),
            ctx_qs.count(),
            pending_qs.count(),
        )

        self.stdout.write("=== serving_layer 백필 대상 (매핑표) ===")
        self.stdout.write(f"  evidence ← SEC4종·CO_MENTIONED (self-loop·기존excluded 제외) : {ev_n}")
        self.stdout.write(f"  excluded ← 자기루프(source==target) : {sl_n}")
        self.stdout.write(f"  context  ← PEER_OF·PRICE_CORRELATED : {ctx_n}")
        self.stdout.write(f"  pending 유지 ← PEER 등 : {pend_n}")

        if not opts["apply"]:
            self.stdout.write(self.style.WARNING("dry-run (--apply 미지정): 쓰기 0건"))
            return

        u1 = ev_qs.update(serving_layer="evidence")
        u_sl = selfloop_qs.update(serving_layer="excluded")
        u2 = ctx_qs.update(serving_layer="context")
        self.stdout.write(
            self.style.SUCCESS(
                f"백필 완료: evidence {u1} / excluded(self-loop) {u_sl} / context {u2} / pending {pend_n}"
            )
        )
