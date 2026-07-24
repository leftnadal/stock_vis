"""ThemeTermOverride per-term override 레이어 테스트 (TH-C3-LLM-DICT-1, 결정35=1).

작업4 롤백 리허설 + 미등재 term 무변경 증명. 1차 규칙/H2 경로 불변(허용 A) 봉인.
"""
from datetime import date

import pytest

from apps.chain_sight.models import HeatEntity, ThemeNewsVolume, ThemeTermOverride
from apps.chain_sight.services.c3_narrative_service import aggregate_theme_news_volume

SECTORS = [
    "Technology", "Financial Services", "Industrials", "Consumer Cyclical",
    "Consumer Defensive", "Energy", "Healthcare", "Communication Services",
    "Utilities", "Real Estate", "Basic Materials",
]


@pytest.fixture(autouse=True)
def _seed_sectors(db):
    for ref in SECTORS:
        HeatEntity.objects.get_or_create(
            kind="sector", ref_id=ref, defaults={"constituent_policy": "static"}
        )


def _mk_news(d, terms):
    from services.news.models import DailyNewsKeyword

    DailyNewsKeyword.objects.create(
        date=d, keywords=[{"search_terms_en": terms}], total_news_count=1
    )


@pytest.mark.django_db
class TestThemeTermOverride:
    def test_unregistered_term_unchanged(self):
        """미등재 term: override 유/무 경로 산출 동일 (허용 A 불변 증명)."""
        _mk_news(date(2026, 6, 1), ["ai"])  # 1차 규칙 → Technology, override 미등재
        aggregate_theme_news_volume(use_override=False)
        base = ThemeNewsVolume.objects.get(
            theme__ref_id="Technology", date=date(2026, 6, 1)
        ).mention_count
        ThemeNewsVolume.objects.all().delete()
        aggregate_theme_news_volume(use_override=True)  # override 테이블 비어있음
        withov = ThemeNewsVolume.objects.get(
            theme__ref_id="Technology", date=date(2026, 6, 1)
        ).mention_count
        assert base == withov == 1

    def test_override_none_removes(self):
        """disposition='none' → 크레딧 제거 (1차 규칙 Technology 우회)."""
        ThemeTermOverride.objects.create(
            term_normalized="jpmorgan ai agents", term_original="JPMorgan AI agents",
            disposition="none", generation="ovr_v1", provenance={"cell": "none_pollute"},
        )
        _mk_news(date(2026, 6, 2), ["JPMorgan AI agents"])  # 1차 규칙 ai→Technology
        aggregate_theme_news_volume(use_override=True)
        assert not ThemeNewsVolume.objects.filter(
            theme__ref_id="Technology", date=date(2026, 6, 2)
        ).exists()

    def test_override_reassign(self):
        """disposition=섹터 → 재배정 (1차 규칙 Technology 대신 FinSvc)."""
        ThemeTermOverride.objects.create(
            term_normalized="jpmorgan ai agents", term_original="JPMorgan AI agents",
            disposition="Financial Services", generation="ovr_v1",
            provenance={"cell": "real_pollute"},
        )
        _mk_news(date(2026, 6, 3), ["JPMorgan AI agents"])
        aggregate_theme_news_volume(use_override=True)
        assert ThemeNewsVolume.objects.filter(
            theme__ref_id="Financial Services", date=date(2026, 6, 3)
        ).exists()
        assert not ThemeNewsVolume.objects.filter(
            theme__ref_id="Technology", date=date(2026, 6, 3)
        ).exists()

    def test_rollback_generation(self):
        """세대 원복(비활성 세대 조회) → override 무효 = 개정 전 1차 규칙 값 일치."""
        ThemeTermOverride.objects.create(
            term_normalized="jpmorgan ai agents", term_original="JPMorgan AI agents",
            disposition="Financial Services", generation="ovr_v1", provenance={},
        )
        _mk_news(date(2026, 6, 4), ["JPMorgan AI agents"])
        aggregate_theme_news_volume(use_override=True, override_generation="ovr_v1")
        assert ThemeNewsVolume.objects.filter(
            theme__ref_id="Financial Services", date=date(2026, 6, 4)
        ).exists()
        # 롤백 = 비활성 세대 조회 → override 빈 map → 1차 규칙 Technology 복귀
        ThemeNewsVolume.objects.all().delete()
        aggregate_theme_news_volume(use_override=True, override_generation="ROLLED_BACK")
        assert ThemeNewsVolume.objects.filter(
            theme__ref_id="Technology", date=date(2026, 6, 4)
        ).exists()
        assert not ThemeNewsVolume.objects.filter(
            theme__ref_id="Financial Services", date=date(2026, 6, 4)
        ).exists()


@pytest.mark.django_db
class TestRecomputeOptions:
    """쓰기 3단 재산출 옵션(date_lte 스코프 + zero_missing_existing) 검증."""

    def test_date_lte_scope_excludes_later(self):
        """date_lte 스코프: 상한 초과일 코퍼스는 집계에서 제외(동결 유지)."""
        _mk_news(date(2026, 6, 1), ["ai"])       # ≤ cut
        _mk_news(date(2026, 8, 1), ["ai"])       # > cut (제외돼야)
        aggregate_theme_news_volume(date_lte=date(2026, 7, 11), use_override=False)
        assert ThemeNewsVolume.objects.filter(date=date(2026, 6, 1)).exists()
        assert not ThemeNewsVolume.objects.filter(date=date(2026, 8, 1)).exists()

    def test_date_gte_scope_backfill_range(self):
        """date_gte+date_lte 범위: [gte, lte] 구간만 집계(≤gte 미만 무접촉 = 백필 스코프)."""
        _mk_news(date(2026, 7, 1), ["ai"])        # < gte (제외돼야)
        _mk_news(date(2026, 7, 15), ["ai"])       # 범위 내
        _mk_news(date(2026, 8, 1), ["ai"])        # > lte (제외돼야)
        aggregate_theme_news_volume(
            date_gte=date(2026, 7, 12), date_lte=date(2026, 7, 24), use_override=False
        )
        assert not ThemeNewsVolume.objects.filter(date=date(2026, 7, 1)).exists()
        assert ThemeNewsVolume.objects.filter(date=date(2026, 7, 15)).exists()
        assert not ThemeNewsVolume.objects.filter(date=date(2026, 8, 1)).exists()

    def test_zero_missing_existing_zeros_removed_credit(self):
        """override 'none' 재산출 시 기존 크레딧 행을 0 으로 갱신(삭제 아님, forward-only)."""
        # 1) baseline: ai → Technology 크레딧 1 (override 없음)
        _mk_news(date(2026, 6, 5), ["ai"])
        aggregate_theme_news_volume(use_override=False)
        row = ThemeNewsVolume.objects.get(theme__ref_id="Technology", date=date(2026, 6, 5))
        assert row.mention_count == 1
        # 2) override 등재: ai → none (제거). zero_missing 없이 재산출하면 옛 값 잔존(기존 동작)
        ThemeTermOverride.objects.create(
            term_normalized="ai", term_original="ai",
            disposition="none", generation="ovr_v1", provenance={"cell": "none_pollute"},
        )
        aggregate_theme_news_volume(use_override=True)  # zero_missing_existing=False(기본)
        assert ThemeNewsVolume.objects.get(
            theme__ref_id="Technology", date=date(2026, 6, 5)
        ).mention_count == 1  # 잔존(그 날 counts 에 Technology 없어 upsert 미발생)
        # 3) zero_missing_existing=True 재산출 → 0 으로 갱신, 행은 보존(삭제 아님)
        res = aggregate_theme_news_volume(use_override=True, zero_missing_existing=True)
        row2 = ThemeNewsVolume.objects.get(theme__ref_id="Technology", date=date(2026, 6, 5))
        assert row2.mention_count == 0
        assert res["zeroed"] >= 1

    def test_zero_missing_preserves_active_credit(self):
        """zero_missing_existing 이 그 날 크레딧 받은 테마는 건드리지 않음."""
        ThemeTermOverride.objects.create(
            term_normalized="jpmorgan ai agents", term_original="JPMorgan AI agents",
            disposition="Financial Services", generation="ovr_v1", provenance={},
        )
        _mk_news(date(2026, 6, 6), ["JPMorgan AI agents"])
        aggregate_theme_news_volume(use_override=True, zero_missing_existing=True)
        assert ThemeNewsVolume.objects.get(
            theme__ref_id="Financial Services", date=date(2026, 6, 6)
        ).mention_count == 1
