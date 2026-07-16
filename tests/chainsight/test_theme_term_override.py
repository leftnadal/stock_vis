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
