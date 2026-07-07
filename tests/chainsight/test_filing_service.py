"""
C2b 발행 신호 파이프라인 테스트 (TH-3, 설계서 §5.2 재정의판).

검증:
- accession 추출 + dedup_key 멱등.
- 424B5 정확 일치 필터(prefix 오염 차단) + symbol 결측 카운트 제외.
- IPO 거래소 필터(NYSE/NASDAQ) + 멱등.
- 90일 건수 집계 + c2b_from_db z 산출(부호 정방향).
"""

from datetime import date, timedelta

import pytest

from apps.chain_sight.models import ThemeFilingCount
from apps.chain_sight.services import filing_service as fs


class _FakeClient:
    """FMP 클라이언트 스텁 — 주입 응답 반환."""

    def __init__(self, by_form=None, ipos=None):
        self._by_form = by_form or {}   # {(form, from, to): [rows]}
        self._ipos = ipos or []

    def get_sec_filings_by_form_type(self, form_type, from_date, to_date, page=0, limit=100):
        return self._by_form.get((form_type, from_date, to_date), [])

    def get_ipos_calendar(self, from_date, to_date):
        return self._ipos


class TestDedupHelpers:
    def test_extract_accession_from_link(self):
        link = "https://www.sec.gov/Archives/edgar/data/320193/0000320193-26-000075-index.htm"
        assert fs.extract_accession(link) == "0000320193-26-000075"

    def test_extract_accession_fallback_to_link(self):
        assert fs.extract_accession("no-accession-here") == "no-accession-here"
        assert fs.extract_accession("") == ""

    def test_dedup_key_stable_and_case_insensitive(self):
        k1 = fs.build_filing_dedup_key("aapl", "320193", "0000320193-26-000075")
        k2 = fs.build_filing_dedup_key("AAPL", "320193", "0000320193-26-000075")
        assert k1 == k2 and len(k1) == 64


@pytest.mark.django_db
class TestCollect424b5:
    def test_exact_match_filter_blocks_prefix_pollution(self):
        """424B5 정확 일치만 카운트 — 424B5MEF·424B3 등 변형 제외."""
        day = date(2026, 7, 6)
        iso = day.isoformat()
        rows = [
            {"symbol": "AAA", "cik": "1", "formType": "424B5", "filingDate": iso, "link": "a/000-00-000001-index.htm"},
            {"symbol": "BBB", "cik": "2", "formType": "424B5MEF", "filingDate": iso, "link": "b"},  # 변형 제외
            {"symbol": "CCC", "cik": "3", "formType": "424B3", "filingDate": iso, "link": "c"},     # 다른 폼 제외
        ]
        client = _FakeClient(by_form={("424B5", iso, iso): rows})

        res = fs.collect_424b5_for_day(client, day)

        assert res["fetched"] == 3
        assert res["exact"] == 1
        assert res["created"] == 1
        assert res["skipped_form"] == 2
        assert ThemeFilingCount.objects.filter(form_type="424B5").count() == 1
        assert ThemeFilingCount.objects.get().symbol == "AAA"

    def test_no_symbol_excluded_and_counted(self):
        """symbol 결측분(~10%)은 카운트 제외 + 결손 집계 (침묵 유입 방지)."""
        day = date(2026, 7, 6)
        iso = day.isoformat()
        rows = [
            {"symbol": "", "cik": "9", "formType": "424B5", "filingDate": iso, "link": "x"},
            {"symbol": "AAA", "cik": "1", "formType": "424B5", "filingDate": iso, "link": "a/000-00-000001-index.htm"},
        ]
        client = _FakeClient(by_form={("424B5", iso, iso): rows})

        res = fs.collect_424b5_for_day(client, day)

        assert res["skipped_no_symbol"] == 1
        assert res["created"] == 1

    def test_idempotent_upsert(self):
        """같은 filing 재수집 = 중복 생성 없음 (dedup_key)."""
        day = date(2026, 7, 6)
        iso = day.isoformat()
        rows = [{"symbol": "AAA", "cik": "1", "formType": "424B5", "filingDate": iso, "link": "a/000-00-000001-index.htm"}]
        client = _FakeClient(by_form={("424B5", iso, iso): rows})

        fs.collect_424b5_for_day(client, day)
        res2 = fs.collect_424b5_for_day(client, day)

        assert res2["created"] == 0  # 이미 존재
        assert ThemeFilingCount.objects.filter(form_type="424B5").count() == 1


@pytest.mark.django_db
class TestCollectIpo:
    def test_exchange_filter_keeps_nyse_nasdaq(self):
        """NYSE/NASDAQ 만 적재 — OTC·해외 제외."""
        ipos = [
            {"symbol": "IPO1", "date": "2026-07-06", "exchange": "NASDAQ Global Select"},
            {"symbol": "IPO2", "date": "2026-07-06", "exchange": "NYSE"},
            {"symbol": "IPO3", "date": "2026-07-06", "exchange": "OTC"},          # 제외
            {"symbol": "IPO4", "date": "2026-07-06", "exchange": "KOSDAQ"},       # 제외
        ]
        client = _FakeClient(ipos=ipos)

        res = fs.collect_ipos_range(client, date(2026, 7, 1), date(2026, 7, 6))

        assert res["created"] == 2
        assert res["skipped_exchange"] == 2
        kept = set(ThemeFilingCount.objects.filter(form_type="IPO").values_list("symbol", flat=True))
        assert kept == {"IPO1", "IPO2"}


@pytest.mark.django_db
class TestC2bAggregation:
    def _seed(self, symbol, d, form_type, exchange=""):
        ThemeFilingCount.objects.create(
            symbol=symbol,
            filing_date=d,
            form_type=form_type,
            exchange=exchange,
            dedup_key=f"{symbol}|{form_type}|{d.isoformat()}",
        )

    def test_count_filings_90d_window(self):
        as_of = date(2026, 7, 6)
        self._seed("AAA", as_of - timedelta(days=10), "424B5")   # 창 안
        self._seed("AAA", as_of - timedelta(days=200), "424B5")  # 창 밖
        self._seed("BBB", as_of - timedelta(days=5), "424B5")    # 창 안
        n = fs.count_filings_90d(["AAA", "BBB"], as_of, "424B5")
        assert n == 2

    def test_c2b_from_db_positive_z_on_recent_surge(self):
        """현재 90일 발행이 과거보다 급증하면 z>0 (공급 증가 = 과열, 정방향)."""
        as_of = date(2026, 7, 6)
        # 과거 3년: 드문 발행 (히스토리 낮음)
        base = as_of - timedelta(days=1000)
        for i in range(6):
            self._seed(f"H{i}", base + timedelta(days=i * 120), "424B5")
        # 최근 90일: 발행 급증
        for i in range(12):
            self._seed(f"R{i}", as_of - timedelta(days=i * 5 + 1), "424B5")

        syms = [f"H{i}" for i in range(6)] + [f"R{i}" for i in range(12)]
        comp = fs.c2b_from_db(syms, as_of, step_days=14, min_n=20, include_ipo=False)

        assert comp["missing_reason"] is None, comp
        assert comp["z"] is not None and comp["z"] > 0
        assert comp["raw"]["count_424b5"] >= 10
