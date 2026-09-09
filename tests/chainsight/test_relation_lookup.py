"""CS-S3-1C — 쌍 조회 서비스(A) + serving_layer 축 관계 문장 매핑(B·D-S3-8) 단위.

판정 축 = serving_layer(손 매핑 우선순위 아님). evidence&truth=기록됨 / context=줄에 안 나옴 /
그 외(CO_MENTIONED·미매핑·무행)=관계 기록 없음. 등급(relation_status)은 판정에 안 쓴다.
읽기 전용·마이그 0.
"""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.chain_sight.services.relation_lookup import (
    NONE_LINE,
    RECORDED_SENTENCE,
    lookup_pairs,
    relation_line_for,
)


def _rc(a, b, rtype, layer, category="truth", status="confirmed"):
    from apps.chain_sight.models import RelationConfidence
    return RelationConfidence.objects.create(
        symbol_a=a, symbol_b=b, relation_type=rtype, serving_layer=layer,
        relation_category=category, relation_status=status,
    )


# ── B/D-S3-8 매핑 (serving_layer 축) ──
class TestRelationLine:
    def _rows(self, *specs):
        # specs: (relation_type, serving_layer, category)
        return [{"relation_type": t, "serving_layer": s, "relation_category": c} for t, s, c in specs]

    def test_evidence_truth_recorded_sentence(self):
        assert relation_line_for(self._rows(("SUPPLIES_TO", "evidence", "truth"))) == "공급 관계로 기록됨"
        assert relation_line_for(self._rows(("PARTNER_WITH", "evidence", "truth"))) == "제휴 관계로 기록됨"
        assert relation_line_for(self._rows(("COMPETES_WITH", "evidence", "truth"))) == "경쟁 관계로 기록됨"

    def test_co_mention_only_is_none(self):
        # D-3: CO_MENTIONED만(evidence·market) → 관계 기록 없음.
        assert relation_line_for(self._rows(("CO_MENTIONED", "evidence", "market"))) == NONE_LINE

    def test_context_layer_not_recorded(self):
        # PEER_OF(context) → 줄에 안 나옴 → 관계 기록 없음.
        assert relation_line_for(self._rows(("PEER_OF", "context", "truth"))) == NONE_LINE

    def test_recorded_beats_context(self):
        # D-4: 기록된 관계 + PEER_OF 동시 → 기록된 관계가 이긴다.
        line = relation_line_for(self._rows(
            ("PEER_OF", "context", "truth"), ("PARTNER_WITH", "evidence", "truth"),
        ))
        assert line == "제휴 관계로 기록됨"

    def test_pending_type_falls_to_none(self):
        # 레거시 PEER(pending/truth) 등 evidence 아닌 truth 행 → 관계 기록 없음(조용한 실패).
        assert relation_line_for(self._rows(("PEER", "pending", "truth"))) == NONE_LINE
        # SEC 타입이라도 serving_layer가 evidence 아니면 기록 안 됨.
        assert relation_line_for(self._rows(("COMPETES_WITH", "pending", "truth"))) == NONE_LINE

    def test_unmapped_type_falls_to_none(self):
        # D-8: 매핑에 없는 타입(HAS_THEME 등)은 관계 기록 없음.
        assert relation_line_for(self._rows(("HAS_THEME", "evidence", "truth"))) == NONE_LINE

    def test_empty_rows_is_none(self):
        assert relation_line_for([]) == NONE_LINE

    def test_priority_among_recorded(self):
        # 여러 기록된 관계 → 우선순위 위쪽(SUPPLIES_TO)이 이긴다.
        line = relation_line_for(self._rows(
            ("COMPETES_WITH", "evidence", "truth"), ("SUPPLIES_TO", "evidence", "truth"),
        ))
        assert line == "공급 관계로 기록됨"

    def test_no_grade_words_in_any_sentence(self):
        # D-1 근거: 매핑 문장에 등급 단어 없음.
        blob = " ".join(RECORDED_SENTENCE.values()) + " " + NONE_LINE
        for g in ["confirmed", "probable", "weak", "hidden", "stale", "확인된"]:
            assert g not in blob


# ── A 쌍 조회 서비스(무방향·N+1 금지) ──
@pytest.mark.django_db
class TestLookupPairs:
    def test_undirected_lookup(self):
        _rc("ORCL", "PANW", "PARTNER_WITH", "evidence")
        # 역방향 쌍으로 조회해도 찾는다.
        res = lookup_pairs([("PANW", "ORCL")])
        rows = res[frozenset(("ORCL", "PANW"))]
        assert len(rows) == 1
        assert rows[0]["relation_type"] == "PARTNER_WITH"

    def test_multiple_types_per_pair(self):
        _rc("A", "B", "PEER_OF", "context")
        _rc("A", "B", "COMPETES_WITH", "evidence")
        res = lookup_pairs([("A", "B")])
        assert len(res[frozenset(("A", "B"))]) == 2

    def test_missing_pair_empty(self):
        res = lookup_pairs([("ZZZ", "YYY")])
        assert res.get(frozenset(("ZZZ", "YYY")), []) == []

    def test_no_n_plus_1(self):
        # D-5: 쌍이 여러 개여도 쿼리 수 상한(≤2). N+1 회귀 차단.
        for i in range(10):
            _rc(f"S{i}", f"T{i}", "PARTNER_WITH", "evidence")
        pairs = [(f"S{i}", f"T{i}") for i in range(10)]
        with CaptureQueriesContext(connection) as ctx:
            res = lookup_pairs(pairs)
        assert len(ctx.captured_queries) <= 2
        assert len(res) == 10
