"""SUNMON-REEXTRACT (D-SUNMON-REEXTRACT) — failed 재추출 + completed 절대 가드 입증.

av-broad 수집 완료 후 체이닝되는 `reextract_recent_failed_keywords`가
- failed 행은 (기사 있으면) 재추출해 completed 전이,
- completed 행은 어떤 경로로도 무접촉(byte 동일),
- 기사 0건이면 failed 유지
함을 검증한다. LLM은 genai.Client stub으로 결정화(현행 마이그 테스트 패턴 재사용).
"""

import json
import uuid
from datetime import date, datetime

import pytest
from django.utils import timezone

from services.news.models import DailyNewsKeyword, NewsArticle
from services.news.services.keyword_extractor import reextract_recent_failed_keywords


@pytest.fixture
def stub_gemini(monkeypatch, settings):
    """genai.Client를 가로채 _call_llm이 결정적 키워드 1건을 반환하게 한다."""
    settings.GEMINI_API_KEY = "fake-key"

    class _Usage:
        prompt_token_count = 5
        candidates_token_count = 10

    class _Resp:
        text = json.dumps(
            [
                {
                    "text": "AI 랠리 지속",
                    "sentiment": "positive",
                    "importance": 0.9,
                    "related_symbols": ["NVDA"],
                    "search_terms_en": ["AI rally"],
                }
            ]
        )
        usage_metadata = _Usage()

    class _Models:
        def generate_content(self, *, model, contents, config):
            return _Resp()

    class _Client:
        def __init__(self, api_key=None):
            self.models = _Models()

    import google.genai as real_genai

    monkeypatch.setattr(real_genai, "Client", _Client)


def _make_article(d: date, i: int = 0) -> NewsArticle:
    """KST 창 [d 00:00, d 23:59] 내(정오)에 발행된 최소 NewsArticle 1건."""
    dt = timezone.make_aware(datetime(d.year, d.month, d.day, 12, i % 60))
    return NewsArticle.objects.create(
        url=f"https://example.com/{d}/{i}/{uuid.uuid4()}",
        url_hash=uuid.uuid4().hex,
        title=f"news {d} {i}",
        source="marketaux",
        published_at=dt,
        marketaux_uuid=uuid.uuid4().hex[:20],
    )


@pytest.mark.django_db
def test_failed_reextract_success(stub_gemini):
    """failed + 기사 존재 → 재추출로 completed 전이."""
    d = date(2026, 8, 9)
    DailyNewsKeyword.objects.create(
        date=d, status="failed", keywords=[], error_message="No news found for this date"
    )
    _make_article(d)

    summary = reextract_recent_failed_keywords(target_dates=[d])

    row = DailyNewsKeyword.objects.get(date=d)
    assert row.status == "completed"
    assert len(row.keywords) >= 1
    assert summary == [
        {"date": str(d), "before": "failed", "after": "completed", "keywords": len(row.keywords)}
    ]


@pytest.mark.django_db
def test_completed_untouched(stub_gemini):
    """completed 행은 기사가 있어도 무접촉 — keywords·updated_at byte 동일."""
    d = date(2026, 8, 9)
    orig_kw = [{"text": "기존 키워드", "sentiment": "neutral"}]
    row = DailyNewsKeyword.objects.create(
        date=d, status="completed", keywords=orig_kw, total_news_count=42
    )
    orig_updated = row.updated_at
    _make_article(d)  # 기사 있어도 completed는 대상 아님

    summary = reextract_recent_failed_keywords(target_dates=[d])

    row.refresh_from_db()
    assert row.status == "completed"
    assert row.keywords == orig_kw  # byte 동일
    assert row.total_news_count == 42
    assert row.updated_at == orig_updated  # 미갱신(무접촉)
    assert summary == []  # 대상 없음


@pytest.mark.django_db
def test_no_articles_stays_failed(stub_gemini):
    """failed + 기사 0건 → failed 유지(공백 유지 = 정상)."""
    d = date(2026, 8, 10)
    DailyNewsKeyword.objects.create(
        date=d, status="failed", keywords=[], error_message="No news found for this date"
    )
    # 기사 미생성

    summary = reextract_recent_failed_keywords(target_dates=[d])

    row = DailyNewsKeyword.objects.get(date=d)
    assert row.status == "failed"
    assert row.keywords == []
    assert summary == [
        {"date": str(d), "before": "failed", "after": "failed", "keywords": 0}
    ]


@pytest.mark.django_db
def test_guard_completed_byte_identical_when_mixed(stub_gemini, caplog):
    """completed 1행 + failed 1행 혼재 → completed byte 동일, failed만 재추출 + 로그 기록."""
    import logging

    d_done = date(2026, 8, 8)
    d_fail = date(2026, 8, 9)
    done_kw = [{"text": "토요일 키워드", "sentiment": "positive"}]
    done = DailyNewsKeyword.objects.create(
        date=d_done, status="completed", keywords=done_kw, total_news_count=100
    )
    done_updated = done.updated_at
    DailyNewsKeyword.objects.create(
        date=d_fail, status="failed", keywords=[], error_message="No news found for this date"
    )
    _make_article(d_fail)

    with caplog.at_level(logging.INFO, logger="apps.sunmon_reextract"):
        summary = reextract_recent_failed_keywords(target_dates=[d_done, d_fail])

    # completed 무접촉
    done.refresh_from_db()
    assert done.status == "completed"
    assert done.keywords == done_kw  # byte 동일
    assert done.updated_at == done_updated  # 무접촉

    # failed만 재추출
    fail = DailyNewsKeyword.objects.get(date=d_fail)
    assert fail.status == "completed"
    assert [s["date"] for s in summary] == [str(d_fail)]

    # SUNMON_REEXTRACT 파일 로그(관측 재료) 기록 확인 — d_fail 1건만
    lines = [r.message for r in caplog.records if "SUNMON_REEXTRACT" in r.getMessage()]
    assert len(lines) == 1
    assert f"date={d_fail}" in caplog.records[-1].getMessage()
