"""
C3 H2 사전 원장 테스트 (TH-13, 결정19=A/결정21=C) — 설계 부록 A 박제.

커버:
- ThemeKeywordH2 모델 + provenance(source/applied_at/confidence)
- load_h2_sector_map: source 필터
- aggregate use_h2: 미배정분 H2 채움 / 1차 배정 무접촉(P2) / 추가만(R3) / use_h2=False 무시
"""

from datetime import date

import pytest
from django.utils import timezone

from apps.chain_sight.models import HeatEntity, ThemeKeywordH2, ThemeNewsVolume
from apps.chain_sight.services.c3_narrative_service import (
    _normalize,
    aggregate_theme_news_volume,
    load_h2_sector_map,
)


def _mk_news(d, term_lists):
    from services.news.models import DailyNewsKeyword

    keywords = [{"search_terms_en": terms} for terms in term_lists]
    DailyNewsKeyword.objects.create(date=d, keywords=keywords, total_news_count=1)


def _h2(term, sector, confidence="high", source="h2_v1"):
    return ThemeKeywordH2.objects.create(
        term_normalized=_normalize(term), term_original=term, sector=sector,
        confidence=confidence, source=source, applied_at=timezone.now(),
    )


@pytest.mark.django_db
class TestThemeKeywordH2Model:
    def test_provenance_fields(self):
        row = _h2("Quantum Widget Corp", "Technology", confidence="medium")
        row.refresh_from_db()
        assert row.source == "h2_v1"
        assert row.confidence == "medium"
        assert row.applied_at is not None
        assert row.term_normalized == "quantum widget corp"

    def test_term_normalized_unique_merge(self):
        # 대소문자만 다른 두 원문 → 동일 정규화 키(자연 병합, TH-12b 판정)
        _h2("Quantum WIDGET", "Technology")
        with pytest.raises(Exception):
            _h2("quantum widget", "Energy")  # unique(term_normalized) 위반


@pytest.mark.django_db
class TestLoadH2SectorMap:
    def test_source_filter(self):
        _h2("alpha term", "Technology", source="h2_v1")
        _h2("beta term", "Energy", source="h2_v2")
        m = load_h2_sector_map(source="h2_v1")
        assert m == {"alpha term": "Technology"}

    def test_default_loads_active_union(self):
        # TH-14 provenance 체인: 기본(source=None) = h2_v1 유지분 + h2_v2 재검분 = 활성 전체
        _h2("alpha term", "Technology", source="h2_v1")
        _h2("beta term", "Energy", source="h2_v2")  # 재검 교정분
        m = load_h2_sector_map()
        assert m == {"alpha term": "Technology", "beta term": "Energy"}

    def test_demote_delete_removes_from_active(self):
        # 강등 = 행 삭제 → 활성 사전에서 제거(미배정 복귀)
        row = _h2("gamma term", "Energy", source="h2_v1")
        assert _normalize("gamma term") in load_h2_sector_map()
        row.delete()
        assert _normalize("gamma term") not in load_h2_sector_map()


@pytest.mark.django_db
class TestAggregateWithH2:
    def _tech(self):
        return HeatEntity.objects.get(kind="sector", ref_id="Technology")

    def test_h2_fills_unassigned(self):
        # 1차 규칙 미배정 용어 → H2 사전으로 Technology 배정
        _mk_news(date(2026, 6, 1), [["quantum widget breakthrough"]])
        _h2("quantum widget breakthrough", "Technology")
        aggregate_theme_news_volume(use_h2=True)
        assert ThemeNewsVolume.objects.get(theme=self._tech(), date=date(2026, 6, 1)).mention_count == 1

    def test_use_h2_false_ignores(self):
        _mk_news(date(2026, 6, 2), [["quantum widget breakthrough"]])
        _h2("quantum widget breakthrough", "Technology")
        aggregate_theme_news_volume(use_h2=False)
        assert not ThemeNewsVolume.objects.filter(theme=self._tech(), date=date(2026, 6, 2)).exists()

    def test_h2_does_not_touch_first_rule_assigned(self):
        # 'ai'(1차 규칙 Technology) 는 H2 에 있어도 1차 우선 — 이중 카운트 없음(P2)
        _mk_news(date(2026, 6, 3), [["ai"]])
        _h2("ai", "Energy")  # 상충 H2(무시되어야 함)
        aggregate_theme_news_volume(use_h2=True)
        tech = ThemeNewsVolume.objects.get(theme=self._tech(), date=date(2026, 6, 3)).mention_count
        assert tech == 1  # 1차 규칙만 1회 (H2 미적용)
        energy = HeatEntity.objects.get(kind="sector", ref_id="Energy")
        assert not ThemeNewsVolume.objects.filter(theme=energy, date=date(2026, 6, 3)).exists()

    def test_h2_only_adds_never_decreases(self):
        # R3 원칙: 1차 배정 카운트는 H2 유무와 무관하게 보존
        _mk_news(date(2026, 6, 4), [["ai", "quantum widget breakthrough"]])
        aggregate_theme_news_volume(use_h2=False)
        base = ThemeNewsVolume.objects.get(theme=self._tech(), date=date(2026, 6, 4)).mention_count
        _h2("quantum widget breakthrough", "Technology")
        aggregate_theme_news_volume(use_h2=True)
        after = ThemeNewsVolume.objects.get(theme=self._tech(), date=date(2026, 6, 4)).mention_count
        assert after == base + 1  # ai(1차) 보존 + quantum(H2) 추가
