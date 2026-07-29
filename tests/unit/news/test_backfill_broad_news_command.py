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


# ── C-N-REPAIR: 표적 소창(window-days=1) — 창 논리 함정 회피 ──
def test_target_single_day_windows_are_independent():
    """window-days=1 → 각 날이 1일 독립 창. EARLIEST 보정이 삼킬 '창 뒷날'이 없음(154 누락 원인 차단)."""
    cmd = mod.Command()
    ws = cmd._windows(dt.date(2024, 5, 3), dt.date(2024, 5, 5), 1)
    assert ws == [
        (dt.date(2024, 5, 3), dt.date(2024, 5, 4)),
        (dt.date(2024, 5, 4), dt.date(2024, 5, 5)),
        (dt.date(2024, 5, 5), dt.date(2024, 5, 6)),
    ]
    # 각 창 span=1일 → 창 내부 EARLIEST 절단으로 뒷날이 잘릴 여지 자체가 없음
    for s, e in ws:
        assert (e - s).days == 1


@pytest.mark.django_db
@override_settings(ALPHA_VANTAGE_API_KEY="testkey")
def test_target_single_day_idempotent_skip():
    """표적일에 이미 임계(1×COVERED_PER_DAY) 이상 기사 → 재수집 skip(멱등, 기존 행 무변경)."""
    for i in range(mod.COVERED_PER_DAY):  # 1일 창 임계 = 1×3
        _mk_article(dt.datetime(2024, 5, 3, 12, tzinfo=dt.timezone.utc), i)
    prov, agg = _mock_provider_aggregator()
    out = StringIO()
    with patch("services.news.providers.alphavantage.AlphaVantageNewsProvider", return_value=prov), \
         patch("services.news.services.aggregator.NewsAggregatorService", return_value=agg), \
         patch.object(mod.time, "sleep"):
        call_command(CMD, "--from", "2024-05-03", "--to", "2024-05-03",
                     "--window-days", "1", "--commit", stdout=out)
    assert prov.fetch_broad_news.call_count == 0  # 이미 커버 → 요청 0(멱등)
    assert "커버됨 skip: 1창" in out.getvalue()


@pytest.mark.django_db
@override_settings(ALPHA_VANTAGE_API_KEY="testkey")
def test_target_single_day_null_day_refetched():
    """표적일이 비어(0건) 있으면 window-days=1 창이 재수집 대상(154 복구 경로)."""
    prov, agg = _mock_provider_aggregator(n_arts=5, saved=5)
    out = StringIO()
    with patch("services.news.providers.alphavantage.AlphaVantageNewsProvider", return_value=prov), \
         patch("services.news.services.aggregator.NewsAggregatorService", return_value=agg), \
         patch.object(mod.time, "sleep"):
        call_command(CMD, "--from", "2024-05-03", "--to", "2024-05-03",
                     "--window-days", "1", "--commit", stdout=out)
    assert prov.fetch_broad_news.call_count == 1  # 빈 날 → 재수집
    assert agg._save_articles.call_count == 1


# ── C-N-REPAIR: --dates 표적 모드(명시일만, 주말/공휴일 낭비 0) ──
@pytest.mark.django_db
@override_settings(ALPHA_VANTAGE_API_KEY="testkey")
def test_dates_mode_targets_only_listed_days():
    """--dates: 명시한 날짜만 1일 창으로 재수집(범위 주말 낭비 없음)."""
    prov, agg = _mock_provider_aggregator(n_arts=5, saved=5)
    out = StringIO()
    with patch("services.news.providers.alphavantage.AlphaVantageNewsProvider", return_value=prov), \
         patch("services.news.services.aggregator.NewsAggregatorService", return_value=agg), \
         patch.object(mod.time, "sleep"):
        call_command(CMD, "--dates", "2024-05-03,2024-08-05,2023-10-19", "--commit", stdout=out)
    assert prov.fetch_broad_news.call_count == 3  # 명시 3일만(주말·중간일 생성 안 함)
    assert "표적 3일(각 1일 창)" in out.getvalue()


@pytest.mark.django_db
@override_settings(ALPHA_VANTAGE_API_KEY="testkey")
def test_dates_mode_idempotent_and_dry_run():
    """--dates 멱등(커버된 명시일 skip) + dry-run(쓰기·요청 0)."""
    for i in range(mod.COVERED_PER_DAY):  # 2024-05-03 커버(임계 3)
        _mk_article(dt.datetime(2024, 5, 3, 12, tzinfo=dt.timezone.utc), i)
    prov, agg = _mock_provider_aggregator()
    out = StringIO()
    # dry-run: provider 미호출
    with patch("services.news.providers.alphavantage.AlphaVantageNewsProvider") as P:
        call_command(CMD, "--dates", "2024-05-03,2024-05-06", stdout=out)
    P.assert_not_called()
    assert "DRY-RUN" in out.getvalue()
    # commit: 커버된 05-03 skip, 05-06만 fetch
    out2 = StringIO()
    with patch("services.news.providers.alphavantage.AlphaVantageNewsProvider", return_value=prov), \
         patch("services.news.services.aggregator.NewsAggregatorService", return_value=agg), \
         patch.object(mod.time, "sleep"):
        call_command(CMD, "--dates", "2024-05-03,2024-05-06", "--commit", stdout=out2)
    assert prov.fetch_broad_news.call_count == 1  # 05-03 커버 skip


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
