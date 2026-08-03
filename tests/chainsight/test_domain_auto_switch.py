"""⑳-3 S3-MINDMAP S1 — L1 자동화 스위치 + 검수 verdict 270 보호 가드."""

import pytest
from django.test import override_settings

from apps.chain_sight.models import RelationConfidence
from apps.chain_sight.services import domain_tagging as dt


def _rc(a, b, rtype="SUPPLIES_TO", status=None, mc=None, basis=""):
    return RelationConfidence.objects.create(
        symbol_a=a, symbol_b=b, relation_type=rtype, relation_category="truth",
        domain_review_status=status, domain_machine_check=mc,
        relation_basis_summary=basis,
    )


@pytest.mark.django_db
class TestHumanReviewedGuard:
    def test_verdict_holder_is_human_reviewed(self):
        # review_status 있음 + machine_check 없음 = 검수 산출(보호)
        rc = _rc("AAA", "BBB", status="approved", mc=None)
        assert dt.is_human_reviewed(rc) is True

    def test_fresh_relation_not_reviewed(self):
        rc = _rc("CCC", "DDD", status=None, mc=None)
        assert dt.is_human_reviewed(rc) is False

    def test_pipeline_tagged_not_reviewed(self):
        # 파이프라인이 태깅하면 machine_check가 채워짐 → 보호 대상 아님(재처리 가능)
        rc = _rc("EEE", "FFF", status="pending", mc={"json_parse": True})
        assert dt.is_human_reviewed(rc) is False

    def test_exclude_human_reviewed_queryset(self):
        v = _rc("AAA", "BBB", status="approved", mc=None)     # 보호
        p = _rc("CCC", "DDD", status="pending", mc={"x": 1})   # 파이프라인
        fresh = _rc("EEE", "FFF", status=None, mc=None)        # 신규
        qs = dt.exclude_human_reviewed(RelationConfidence.objects.all())
        ids = set(qs.values_list("id", flat=True))
        assert v.id not in ids           # verdict 보유 제외
        assert p.id in ids and fresh.id in ids


# ── e2e 훅: mock LLM ──
_GOOD_JSON = (
    '{"domain_tags": ["메모리·HBM"], "type_match": {"match": true, "suggested_type": null}, '
    '"refined_basis": "", "confidence": 0.92}'
)


class _Resp:
    def __init__(self, text):
        self.text = text


@pytest.mark.django_db
class TestAutoTaggingE2E:
    @override_settings(DOMAIN_AUTO_APPROVE=True, DOMAIN_CONFIDENCE_THRESHOLD=0.75)
    def test_fresh_sec_relation_auto_tagged(self, monkeypatch):
        from packages.shared.stocks.models import Stock
        Stock.objects.create(symbol="MU", stock_name="Micron Technology")
        rc = _rc("NVDA", "MU", "SUPPLIES_TO",
                 basis="SEC 10-K: We purchase memory from Micron (MU).")
        monkeypatch.setattr(
            "apps.market_pulse.llm.client.generate_with_circuit",
            lambda **kw: _Resp(_GOOD_JSON),
        )
        from apps.chain_sight.tasks.domain_tasks import tag_relation_domain_task
        res = tag_relation_domain_task(rc.id)
        rc.refresh_from_db()
        assert res["review_status"] == "auto"          # 스위치 ON → auto
        assert rc.relation_domain_draft == "메모리·HBM"
        assert rc.domain_machine_check is not None
        assert rc.relation_domain is None              # 승인본은 하드룰상 미기록

    @override_settings(DOMAIN_AUTO_APPROVE=True)
    def test_verdict_holder_skipped_by_hook(self, monkeypatch):
        # 검수 승인된 관계는 훅이 건드리지 않는다(덮어쓰기 금지)
        rc = _rc("INCY", "REGN", "COMPETES_WITH", status="approved", mc=None,
                 basis="SEC 10-K: compete with Regeneron (REGN).")
        called = {"n": 0}

        def _spy(**kw):
            called["n"] += 1
            return _Resp(_GOOD_JSON)

        monkeypatch.setattr("apps.market_pulse.llm.client.generate_with_circuit", _spy)
        from apps.chain_sight.tasks.domain_tasks import tag_relation_domain_task
        res = tag_relation_domain_task(rc.id)
        assert res == {"skipped": "human-reviewed", "rc_id": rc.id}
        assert called["n"] == 0                        # LLM 호출조차 안 함
        rc.refresh_from_db()
        assert rc.relation_domain_draft is None        # 무접촉
