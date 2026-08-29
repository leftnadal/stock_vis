"""D-RC-SCALE (RC-A-1 PART 2) — 눈금 정규화 불변식.

행위보존이 아니라 "의도된 값 변경"의 불변식을 고정한다(item 11):
(a) 순서 보존 — 변환 전후 truth_score 순위 완전 동일
(b) 계단 대응 — {0,35,60,85}→{0,0.35,0.60,0.85} 행수 그대로
(c) version="3.0" 전행 · [0,1] 밖 값 0건
(d) ego 렌더 등급 분포(계단별 행수) 전후 동일
"""

import pytest

from apps.chain_sight.api.ego_views import (
    GRADE_CONFIRMED,
    GRADE_LIKELY,
    GRADE_OBSERVED,
    GRADE_UNVERIFIED,
    _grade_by_score,
)
from apps.chain_sight.models import RelationConfidence
from apps.chain_sight.services.score_scale import (
    apply_scale_normalization,
    to_unit_scale,
)


def test_to_unit_scale_pure_mapping_and_outliers():
    """순수 함수: 계단 매핑 + 오염값(≤1) 보존 + null + 멱등."""
    assert to_unit_scale(0) == 0
    assert to_unit_scale(35) == 0.35
    assert to_unit_scale(60) == 0.60
    assert to_unit_scale(85) == 0.85
    # 이미 [0,1]인 "PEER" 오염값 무접촉
    assert to_unit_scale(0.5) == 0.5
    assert to_unit_scale(0.6) == 0.6
    assert to_unit_scale(None) is None
    # 멱등: 변환값 재적용 불변
    assert to_unit_scale(to_unit_scale(85)) == 0.85


def _seed_premigration_rows():
    """구 스케일(version 2.1) 행 시드. 실 분포 근사: 0/35/60/85 + outlier 0.5/0.6."""
    specs = [
        # (symbol_b, relation_type, category, truth, market)
        ("T85A", "PEER_OF", "truth", 85, None),
        ("T85B", "SUPPLIES_TO", "truth", 85, None),
        ("T60A", "COMPETES_WITH", "truth", 60, None),
        ("T60B", "PARTNER_WITH", "truth", 60, None),
        ("T60C", "DEPENDS_ON", "truth", 60, None),
        ("T35A", "PEER_OF", "truth", 35, None),
        ("T00A", "PEER_OF", "truth", 0, None),
        ("M85A", "CO_MENTIONED", "market", 0, 85),
        ("M60A", "PRICE_CORRELATED", "market", 0, 60),
        ("M35A", "CO_MENTIONED", "market", 0, 35),
        ("P05A", "PEER", "truth", 0.6, None),  # outlier(이미 [0,1])
        ("P05B", "PEER", "truth", 0.5, None),  # outlier
    ]
    for sb, rt, cat, ts, ms in specs:
        rc = RelationConfidence.objects.create(
            symbol_a="AAA", symbol_b=sb, relation_type=rt,
            relation_category=cat, truth_score=ts, market_score=ms,
        )
        # 구 상태 재현: score_version "2.1"로 강제(모델 default는 이제 3.0)
        RelationConfidence.objects.filter(pk=rc.pk).update(score_version="2.1")


@pytest.mark.django_db
def test_order_preservation_legit_population():
    """(a) legitimate 모집단(구 [0,100] 스케일 행)의 truth_score 순위 완전 동일.

    ★ 전역이 아님: 오염 outlier(0<ts≤1 인 "PEER" 2행 0.5/0.6)는 구 스케일에서 35 아래에
    있었으나 legitimate 값만 /100되면서 0.35~0.60 사이로 상대순위가 이동한다. 이는 그 2행이
    진짜 잘못된 스케일임을 재확인하는 의도된 결과 → outlier 제외한 모집단에서 순서 보존 검증.
    """
    _seed_premigration_rows()
    # legitimate = 구 스케일 값(0 또는 >1). 오염(0<ts≤1)은 제외.
    legit = RelationConfidence.objects.exclude(truth_score__gt=0.0, truth_score__lte=1.0)
    before = list(legit.order_by("truth_score", "id").values_list("id", flat=True))
    apply_scale_normalization(RelationConfidence)
    after = list(
        RelationConfidence.objects.filter(id__in=before)
        .order_by("truth_score", "id").values_list("id", flat=True)
    )
    assert before == after, "legitimate 모집단은 단조변환 — 순위 불변"


@pytest.mark.django_db
def test_step_mapping_counts():
    """(b) 계단 대응 행수 보존: 85→0.85, 60→0.60, 35→0.35, 0→0."""
    _seed_premigration_rows()
    apply_scale_normalization(RelationConfidence)

    def cnt(field, val):
        return RelationConfidence.objects.filter(**{field: val}).count()

    # truth: 85→0.85(2), 35→0.35(1) [충돌 없음]
    assert cnt("truth_score", 0.85) == 2
    assert cnt("truth_score", 0.35) == 1
    # truth 0.60 = 매핑 3(60) + outlier 0.6(1) = 4 (0.6==0.60 float 동치는 실서비스도 동일)
    assert cnt("truth_score", 0.60) == 4
    # market: 85→0.85(1), 60→0.60(1), 35→0.35(1) [충돌 없음]
    assert cnt("market_score", 0.85) == 1
    assert cnt("market_score", 0.60) == 1
    assert cnt("market_score", 0.35) == 1


@pytest.mark.django_db
def test_outliers_not_rescaled():
    """(b') outlier 0.5/0.6(이미 [0,1])은 /100 되지 않고 보존."""
    _seed_premigration_rows()
    apply_scale_normalization(RelationConfidence)
    p05a = RelationConfidence.objects.get(symbol_b="P05A")
    p05b = RelationConfidence.objects.get(symbol_b="P05B")
    assert p05a.truth_score == 0.6, "0.6은 이미 [0,1] — 무접촉"
    assert p05b.truth_score == 0.5, "0.5은 이미 [0,1] — 무접촉"


@pytest.mark.django_db
def test_version_and_range_invariant():
    """(c) 전행 version="3.0" · 모든 truth/market ∈ [0,1]."""
    _seed_premigration_rows()
    apply_scale_normalization(RelationConfidence)
    assert not RelationConfidence.objects.exclude(score_version="3.0").exists()
    for ts, ms in RelationConfidence.objects.values_list("truth_score", "market_score"):
        assert 0.0 <= ts <= 1.0
        assert ms is None or 0.0 <= ms <= 1.0


@pytest.mark.django_db
def test_ego_grade_distribution_preserved():
    """(d) ego _grade_by_score 등급 분포가 계단별 행수와 일치(정규화 후 새 임계로)."""
    _seed_premigration_rows()
    apply_scale_normalization(RelationConfidence)

    # 표시점수 = truth(truth cat) 또는 market(market cat)
    grades = []
    for rc in RelationConfidence.objects.all():
        disp = rc.truth_score if rc.relation_category == "truth" else rc.market_score
        grades.append(_grade_by_score(disp))

    from collections import Counter
    dist = Counter(grades)
    # confirmed: truth 0.85(2) + market 0.85(1) = 3
    assert dist[GRADE_CONFIRMED] == 3
    # likely: truth 0.60(3) + market 0.60(1) + outlier 0.6(1) = 5
    assert dist[GRADE_LIKELY] == 5
    # observed: truth 0.35(1) + market 0.35(1) + outlier 0.5(1) = 3
    assert dist[GRADE_OBSERVED] == 3
    # unverified: truth 0(1) → market_score None인 truth cat 0점 = unverified(1)
    assert dist[GRADE_UNVERIFIED] == 1
