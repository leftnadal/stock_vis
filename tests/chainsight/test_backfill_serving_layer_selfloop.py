"""SCE-POLLUTION-CLEANUP(2026-08) — backfill_serving_layer 가드 이중화 회귀.

재분류(relation_type 기준)가 (a) 자기루프를 evidence로 되돌리지 않고 excluded로 분류,
(b) 수동 excluded(오염 정제분)를 evidence로 되돌리지 않는지 검증.
"""

import pytest
from django.core.management import call_command

from apps.chain_sight.models import RelationConfidence


@pytest.mark.django_db
class TestBackfillServingLayerSelfLoopGuard:
    def _mk(self, a, b, rel, layer="pending"):
        # bulk_create = save() 자기루프 가드 우회(레거시 조성용)
        RelationConfidence.objects.bulk_create([
            RelationConfidence(
                symbol_a=a, symbol_b=b, relation_type=rel,
                relation_category="truth", serving_layer=layer,
            )
        ])
        return RelationConfidence.objects.get(symbol_a=a, symbol_b=b, relation_type=rel)

    def test_self_loop_not_promoted_to_evidence(self):
        loop = self._mk("DLR", "DLR", "DEPENDS_ON", layer="pending")
        call_command("backfill_serving_layer", "--apply")
        loop.refresh_from_db()
        assert loop.serving_layer == "excluded"  # evidence 아님

    def test_manual_excluded_preserved(self):
        # 수동 무효화(FTNT→DIS류) — relation_type=SEC4종이어도 excluded 보존
        polluted = self._mk("FTNT", "DIS", "DEPENDS_ON", layer="excluded")
        call_command("backfill_serving_layer", "--apply")
        polluted.refresh_from_db()
        assert polluted.serving_layer == "excluded"  # evidence로 안 되돌림

    def test_normal_sec_row_promoted(self):
        normal = self._mk("AMD", "NVDA", "COMPETES_WITH", layer="pending")
        call_command("backfill_serving_layer", "--apply")
        normal.refresh_from_db()
        assert normal.serving_layer == "evidence"
