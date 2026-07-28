"""backfill_broad_news 커맨드 회귀 — Slice C-N.

핵심 계약:
- dry-run 기본(--commit 없으면 provider 미인스턴스·쓰기 0).
- --commit = pending 창별 fetch_broad_news 재사용 체인 호출(라이브와 동일 save 경로).
- --max-requests 예산 준수(초과 창은 다음 실행으로).
- skip-covered: 이미 커버된 창(기사 ≥ COVERED_THRESHOLD)은 AV 요청 없이 skip.
- 윈도우 생성 경계 정확.
"""
import datetime as dt
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from django.test import override_settings

from services.news.management.commands import backfill_broad_news as mod
from services.news.models import NewsArticle

CMD = "backfill_broad_news"


def _mk_article(published: dt.datetime, i: int):
    return NewsArticle.objects.create(
        url=f"https://ex.com/a/{published.date()}/{i}",
        title=f"headline {i}",
        source="test",
        published_at=published,
    )


def _mock_provider_aggregator(n_arts=3, saved=3, updated=0, skipped=0):
    prov = MagicMock()
    prov.fetch_broad_news.return_value = list(range(n_arts))  # len()만 사용
    agg = MagicMock()
    agg.deduplicator.deduplicate.side_effect = lambda arts: arts
    agg._save_articles.return_value = (saved, updated, skipped)
    return prov, agg


# ── 순수 윈도우 로직 ─────────────────────────────────────────
def test_windows_boundaries_cover_range_inclusive():
    cmd = mod.Command()
    ws = cmd._windows(dt.date(2024, 1, 1), dt.date(2024, 1, 10), 7)
    # 1/1~1/8, 1/8~1/11(끝=to+1 클램프)
    assert ws[0] == (dt.date(2024, 1, 1), dt.date(2024, 1, 8))
    assert ws[-1][1] == dt.date(2024, 1, 11)  # to(1/10)+1
    # 전 구간 연속(겹침·공백 0)
    for (_, e), (s2, _) in zip(ws, ws[1:]):
        assert e == s2


# ── dry-run: provider 미호출·쓰기 0 ─────────────────────────
@pytest.mark.django_db
@override_settings(ALPHA_VANTAGE_API_KEY="testkey")
def test_dry_run_does_not_instantiate_provider_or_write():
    out = StringIO()
    with patch("services.news.providers.alphavantage.AlphaVantageNewsProvider") as P, \
         patch("services.news.services.aggregator.NewsAggregatorService") as A:
        call_command(CMD, "--from", "2024-01-01", "--to", "2024-01-14",
                     "--window-days", "7", stdout=out)
    P.assert_not_called()
    A.assert_not_called()
    assert NewsArticle.objects.count() == 0
    assert "DRY-RUN" in out.getvalue()


# ── --commit: 재사용 체인 호출 + 예산 준수 ──────────────────
@pytest.mark.django_db
@override_settings(ALPHA_VANTAGE_API_KEY="testkey")
def test_commit_fetches_each_pending_window_up_to_budget():
    prov, agg = _mock_provider_aggregator(n_arts=3, saved=3)
    out = StringIO()
    with patch("services.news.providers.alphavantage.AlphaVantageNewsProvider", return_value=prov), \
         patch("services.news.services.aggregator.NewsAggregatorService", return_value=agg), \
         patch.object(mod.time, "sleep"):
        # 2024-01-01~01-21 · 7일 창 = 3창, 예산 2 → 2창만
        call_command(CMD, "--from", "2024-01-01", "--to", "2024-01-21",
                     "--window-days", "7", "--max-requests", "2", "--commit", stdout=out)
    assert prov.fetch_broad_news.call_count == 2  # 예산 준수
    assert agg._save_articles.call_count == 2
    assert "잔여 1창" in out.getvalue()  # 초과분 이후 실행


# ── skip-covered: 이미 커버된 창은 요청 없이 skip ───────────
@pytest.mark.django_db
@override_settings(ALPHA_VANTAGE_API_KEY="testkey")
def test_skip_covered_window_not_refetched():
    # 첫 창(01-01~01-08, 7일)에 임계(7×COVERED_PER_DAY)개 기사 심음 → skip 대상.
    # 여러 날에 분산(경계일 spillover가 아닌 실제 커버 모사).
    covered = 7 * mod.COVERED_PER_DAY
    for i in range(covered):
        _mk_article(dt.datetime(2024, 1, 1 + (i % 6), 12, tzinfo=dt.timezone.utc), i)
    prov, agg = _mock_provider_aggregator()
    out = StringIO()
    with patch("services.news.providers.alphavantage.AlphaVantageNewsProvider", return_value=prov), \
         patch("services.news.services.aggregator.NewsAggregatorService", return_value=agg), \
         patch.object(mod.time, "sleep"):
        # 2창(01-01~08 커버됨, 01-08~15 미커버) → 미커버 1창만 fetch
        call_command(CMD, "--from", "2024-01-01", "--to", "2024-01-14",
                     "--window-days", "7", "--commit", stdout=out)
    assert prov.fetch_broad_news.call_count == 1  # 커버된 창 skip
    assert "커버됨 skip: 1창" in out.getvalue()


# ── spillover 회귀: 경계일 소수 기사만으론 skip 안 함(갭 방지) ──
@pytest.mark.django_db
@override_settings(ALPHA_VANTAGE_API_KEY="testkey")
def test_boundary_spillover_below_threshold_not_skipped():
    # 창(01-01~01-08)에 경계일 1일치 소수(< 임계)만 존재 = 인접 백필 spillover 모사.
    for i in range(mod.COVERED_PER_DAY):  # 임계(7×3)보다 훨씬 적음
        _mk_article(dt.datetime(2024, 1, 7, 12, tzinfo=dt.timezone.utc), i)
    prov, agg = _mock_provider_aggregator()
    out = StringIO()
    with patch("services.news.providers.alphavantage.AlphaVantageNewsProvider", return_value=prov), \
         patch("services.news.services.aggregator.NewsAggregatorService", return_value=agg), \
         patch.object(mod.time, "sleep"):
        call_command(CMD, "--from", "2024-01-01", "--to", "2024-01-07",
                     "--window-days", "7", "--commit", stdout=out)
    # spillover만으론 커버로 안 봄 → 재조회
    assert prov.fetch_broad_news.call_count == 1
    assert "커버됨 skip: 0창" in out.getvalue()


# ── saturation 감지(fetched >= limit) ──────────────────────
@pytest.mark.django_db
@override_settings(ALPHA_VANTAGE_API_KEY="testkey")
def test_saturation_flagged_when_fetched_hits_limit():
    prov, agg = _mock_provider_aggregator(n_arts=50, saved=50)
    out = StringIO()
    with patch("services.news.providers.alphavantage.AlphaVantageNewsProvider", return_value=prov), \
         patch("services.news.services.aggregator.NewsAggregatorService", return_value=agg), \
         patch.object(mod.time, "sleep"):
        call_command(CMD, "--from", "2024-01-01", "--to", "2024-01-07",
                     "--window-days", "7", "--limit", "50", "--commit", stdout=out)
    assert "SATURATED" in out.getvalue()
