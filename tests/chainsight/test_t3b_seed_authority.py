"""T-3b ⓓ-2 — seed status 권위 일원화 테스트 (Phase B).

seed(services/sec_pipeline/tasks.seed_relations_to_chainsight)는:
  - 기존 pair: relation_status 무접촉 (하향=decay, 상향=upward 엔진) → flap 소멸.
  - 신규 pair: 초기 status 설정은 생성자 권한 유지 (create_defaults, ≥85 규칙은
    upward.HIGHSCORE_THRESHOLD 단일 출처).
"""

from datetime import date

import pytest

from apps.chain_sight.models import RelationConfidence
from services.sec_pipeline.tasks import seed_relations_to_chainsight


def _doc(stock):
    from services.sec_pipeline.models import RawDocumentStore

    return RawDocumentStore.objects.create(
        symbol=stock, accession_no=f"acc-{stock.pk}",
        filing_date=date(2023, 11, 1), fiscal_year=2023,
        final_link="https://sec.gov/x",
    )


def _stock(symbol):
    from packages.shared.stocks.models import Stock

    return Stock.objects.create(symbol=symbol, stock_name=f"{symbol} Inc.")


def _sce(doc, source, target, grade):
    from services.sec_pipeline.models import SupplyChainEvidence

    return SupplyChainEvidence.objects.create(
        source_document=doc, source_company=source, target_company=target,
        target_company_name=target.stock_name,
        relationship_type="SUPPLIES_TO", evidence_text="ev",
        confidence_grade=grade,
    )


@pytest.mark.django_db
def test_e_seed_does_not_downgrade_existing_confirmed():
    """(e) flap 회귀: seed의 medium 재관측이 기존 confirmed를 probable로 하향하지 못함."""
    a, b = _stock("AAA"), _stock("BBB")
    doc = _doc(a)
    # 기존 confirmed pair (upward가 올려둔 상태 모사)
    RelationConfidence.objects.create(
        symbol_a=a.pk, symbol_b=b.pk, relation_type="SUPPLIES_TO",
        relation_category="truth", relation_status="confirmed",
        truth_score=85, evidence_tier_best=1,
    )
    _sce(doc, a, b, grade="medium")  # score 60 → 구코드라면 probable로 덮어씀
    seed_relations_to_chainsight()
    rc = RelationConfidence.objects.get(
        symbol_a=a.pk, symbol_b=b.pk, relation_type="SUPPLIES_TO")
    assert rc.relation_status == "confirmed"  # 하향 안 됨 (flap 근절)


@pytest.mark.django_db
def test_h_seed_updates_score_but_not_status_on_existing():
    """(h) seed 업데이트가 status 필드는 무접촉하되 score 등 다른 필드는 갱신."""
    a, b = _stock("AAA"), _stock("BBB")
    doc = _doc(a)
    RelationConfidence.objects.create(
        symbol_a=a.pk, symbol_b=b.pk, relation_type="SUPPLIES_TO",
        relation_category="truth", relation_status="confirmed",
        truth_score=99, evidence_tier_best=1,
    )
    _sce(doc, a, b, grade="medium")  # score 60
    seed_relations_to_chainsight()
    rc = RelationConfidence.objects.get(
        symbol_a=a.pk, symbol_b=b.pk, relation_type="SUPPLIES_TO")
    assert rc.relation_status == "confirmed"  # status 무접촉
    assert rc.truth_score == 0.60             # score는 갱신됨 (defaults 경로, D-RC-SCALE [0,1])


@pytest.mark.django_db
def test_seed_new_pair_born_evidence_layer():
    """S3-1C 보강 N-3c: 신규 SEC pair는 serving_layer='evidence'로 태어난다.

    (CO_MENTIONED 생성부와 대칭 — 모델 default='pending'이라 미설정 시 관계 줄에서 사라진다.)
    """
    a, b = _stock("AAA"), _stock("BBB")
    doc = _doc(a)
    _sce(doc, a, b, grade="high")
    seed_relations_to_chainsight()
    rc = RelationConfidence.objects.get(
        symbol_a=a.pk, symbol_b=b.pk, relation_type="SUPPLIES_TO")
    assert rc.serving_layer == "evidence"


@pytest.mark.django_db
def test_seed_does_not_touch_existing_serving_layer():
    """S3-1C 보강 N-2: 기존 행의 serving_layer 무접촉(excluded 거부권 보존).

    create_defaults만 evidence를 쓰므로 update 경로는 excluded를 evidence로 되돌리지 않는다.
    """
    a, b = _stock("AAA"), _stock("BBB")
    doc = _doc(a)
    RelationConfidence.objects.create(
        symbol_a=a.pk, symbol_b=b.pk, relation_type="SUPPLIES_TO",
        relation_category="truth", relation_status="confirmed",
        serving_layer="excluded", truth_score=85, evidence_tier_best=1,
    )
    _sce(doc, a, b, grade="high")  # 재관측 → update 경로
    seed_relations_to_chainsight()
    rc = RelationConfidence.objects.get(
        symbol_a=a.pk, symbol_b=b.pk, relation_type="SUPPLIES_TO")
    assert rc.serving_layer == "excluded"  # evidence로 안 되돌림


@pytest.mark.django_db
def test_f_seed_new_pair_keeps_initial_status_by_grade():
    """(f) 신규 pair 생성 초기값 현행 유지: high→confirmed, medium→probable (create_defaults)."""
    a, b = _stock("AAA"), _stock("BBB")
    c, d = _stock("CCC"), _stock("DDD")
    doc = _doc(a)
    _sce(doc, a, b, grade="high")     # score 85 ≥ HIGHSCORE → confirmed
    _sce(doc, c, d, grade="medium")   # score 60 → probable
    seed_relations_to_chainsight()
    high = RelationConfidence.objects.get(
        symbol_a=a.pk, symbol_b=b.pk, relation_type="SUPPLIES_TO")
    med = RelationConfidence.objects.get(
        symbol_a=c.pk, symbol_b=d.pk, relation_type="SUPPLIES_TO")
    assert high.relation_status == "confirmed"
    assert med.relation_status == "probable"
