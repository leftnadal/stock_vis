"""collect_calendar_events 태스크 단위 테스트 (EVT-IMPL-2 STEP 4).

mock FMPClient(창 필터링) — 실 FMP 호출 없음. 실쓰기는 테스트 DB만.
검증: upsert 3전이(신규/재관측/occurred) · stale 가드(성분 실패 시 스윕 0) ·
청킹 경계 · dry_run 무쓰기.
"""
import datetime as dt

import pytest

from packages.shared.stocks.models import CalendarEvent
from packages.shared.stocks import tasks as tasks_mod


class FakeClient:
    """창([from,to]) 내 행만 반환하는 mock. 성분 실패는 raises_for로 주입."""

    def __init__(self, *, earnings=None, dividends=None, splits=None, raises_for=None, **kw):
        self._earnings = earnings or []
        self._dividends = dividends or []
        self._splits = splits or []
        self._raises_for = raises_for or set()

    @staticmethod
    def _in_window(rows, frm, to):
        f = dt.date.fromisoformat(frm)
        t = dt.date.fromisoformat(to)
        out = []
        for r in rows:
            d = dt.date.fromisoformat(str(r["date"])[:10])
            if f <= d <= t:
                out.append(r)
        return out

    def get_earnings_calendar(self, frm, to):
        if "earnings" in self._raises_for:
            raise RuntimeError("earnings fetch boom")
        return self._in_window(self._earnings, frm, to)

    def get_dividends_calendar(self, frm, to):
        if "dividends" in self._raises_for:
            raise RuntimeError("dividends fetch boom")
        return self._in_window(self._dividends, frm, to)

    def get_splits_calendar(self, frm, to):
        if "splits" in self._raises_for:
            raise RuntimeError("splits fetch boom")
        return self._in_window(self._splits, frm, to)


def _patch_client(monkeypatch, **kwargs):
    def _factory(*a, **kw):
        return FakeClient(**kwargs)
    monkeypatch.setattr(
        "packages.shared.api_request.providers.fmp.client.FMPClient", _factory
    )


AS_OF = "2026-09-01"  # d0 → forward 09-01..11-29, trailing 08-22..09-01


def _earn(date_str, symbol="NVDA", eps_actual=None):
    return {
        "date": date_str, "symbol": symbol,
        "epsEstimated": "1.2500", "epsActual": eps_actual,
        "revenueEstimated": "1000000", "revenueActual": None,
        "lastUpdated": "2026-09-01",
    }


@pytest.mark.django_db
class TestUpsertTransitions:
    def test_new_then_reobserve_then_occurred(self, monkeypatch):
        # 1) 신규: eps_actual None → scheduled, count=1
        _patch_client(monkeypatch, earnings=[_earn("2026-09-15")])
        tasks_mod.collect_calendar_events(as_of=AS_OF)
        obj = CalendarEvent.objects.get(event_type="EARNINGS", symbol="NVDA")
        assert obj.status == "scheduled"
        assert obj.date_observed_count == 1
        assert CalendarEvent.objects.count() == 1

        # 2) 재관측: 같은 키 → count=2, 여전히 scheduled
        _patch_client(monkeypatch, earnings=[_earn("2026-09-15")])
        tasks_mod.collect_calendar_events(as_of=AS_OF)
        obj.refresh_from_db()
        assert obj.date_observed_count == 2
        assert obj.status == "scheduled"
        assert CalendarEvent.objects.count() == 1

        # 3) occurred 전이: eps_actual 값 → status=occurred
        _patch_client(monkeypatch, earnings=[_earn("2026-09-15", eps_actual="1.4000")])
        tasks_mod.collect_calendar_events(as_of=AS_OF)
        obj.refresh_from_db()
        assert obj.status == "occurred"
        assert str(obj.eps_actual) == "1.4000"

    def test_dividend_and_split_normalized(self, monkeypatch):
        _patch_client(
            monkeypatch,
            dividends=[{"date": "2026-09-20", "symbol": "AAPL", "dividend": "0.240000",
                        "paymentDate": "2026-10-01", "recordDate": "2026-09-22", "frequency": "Quarterly"}],
            splits=[{"date": "2026-09-25", "symbol": "TSLA", "numerator": "3", "denominator": "1", "splitType": "split"}],
        )
        tasks_mod.collect_calendar_events(as_of=AS_OF)
        div = CalendarEvent.objects.get(event_type="DIVIDEND", symbol="AAPL")
        assert div.event_date == dt.date(2026, 9, 20)
        assert div.frequency == "Quarterly"
        assert div.payment_date == dt.date(2026, 10, 1)
        sp = CalendarEvent.objects.get(event_type="SPLIT", symbol="TSLA")
        assert str(sp.split_numerator) == "3.000000"


@pytest.mark.django_db
class TestDryRun:
    def test_dry_run_writes_nothing(self, monkeypatch):
        _patch_client(monkeypatch, earnings=[_earn("2026-09-15"), _earn("2026-10-20", "AMD")])
        res = tasks_mod.collect_calendar_events(as_of=AS_OF, dry_run=True)
        assert CalendarEvent.objects.count() == 0  # DB 무쓰기
        # would-be 카운터는 채워짐
        total_written = sum(c["written"] for c in res["components"].values())
        assert total_written >= 2
        assert res["dry_run"] is True
        assert res["stale_swept"] == {}  # dry_run은 스윕 안 함


@pytest.mark.django_db
class TestStaleGuard:
    def _seed_stale_candidate(self):
        """forward 창 내 scheduled, last_seen 과거로 강제(금회 미관측 대상)."""
        obj = CalendarEvent.objects.create(
            event_type="EARNINGS", symbol="OLD", event_date=dt.date(2026, 9, 10),
            status="scheduled",
        )
        CalendarEvent.objects.filter(pk=obj.pk).update(
            last_seen_at=dt.datetime(2020, 1, 1, tzinfo=dt.timezone.utc)
        )
        return obj

    def test_sweep_on_fetch_success(self, monkeypatch):
        """earnings fetch 성공·해당 종목 미포함 → OLD가 stale로 스윕."""
        old = self._seed_stale_candidate()
        _patch_client(monkeypatch, earnings=[_earn("2026-09-15", "NVDA")])
        res = tasks_mod.collect_calendar_events(as_of=AS_OF)
        old.refresh_from_db()
        assert old.status == "stale"
        assert res["stale_swept"]["EARNINGS"] == 1

    def test_no_sweep_when_fetch_fails(self, monkeypatch):
        """earnings fetch 실패(가드) → 스윕 0, OLD는 scheduled 유지(대량 오염 차단)."""
        old = self._seed_stale_candidate()
        _patch_client(monkeypatch, raises_for={"earnings"})
        res = tasks_mod.collect_calendar_events(as_of=AS_OF)
        old.refresh_from_db()
        assert old.status == "scheduled"  # 미오염
        assert res["stale_swept"]["EARNINGS"] == "skipped(fetch_failed)"


class TestChunkBoundary:
    def test_no_gap_no_overlap(self):
        d0 = dt.date(2026, 9, 1)
        w = tasks_mod._chunk_windows(d0, 90, 45)
        assert w == [(dt.date(2026, 9, 1), dt.date(2026, 10, 15)),
                     (dt.date(2026, 10, 16), dt.date(2026, 11, 29))]
        # 갭·중복 0: chunk2 시작 = chunk1 끝 + 1일
        assert (w[1][0] - w[0][1]).days == 1


def _density_fetcher(density):
    """창 폭 × density 행 반환(캡 4000 상한). 날짜는 창 전체에 분산."""
    from packages.shared.api_request.providers.fmp.calendar_cap import FMP_CALENDAR_ROW_CAP

    def f(frm, to):
        a = dt.date.fromisoformat(frm)
        b = dt.date.fromisoformat(to)
        span = (b - a).days + 1
        n = min(span * density, FMP_CALENDAR_ROW_CAP)
        return [{"date": (a + dt.timedelta(days=i % span)).isoformat(), "symbol": f"S{i}"}
                for i in range(n)]
    return f


class TestBisect:
    def test_recurses_and_merges_full_coverage(self):
        """넓은 창=캡 도달 → 이분 재귀 → 서브창 병합이 요청 span 전량 커버(소실 0)."""
        wf, wt = dt.date(2026, 10, 11), dt.date(2026, 11, 24)  # 45일
        budget = {"extra": tasks_mod._BISECT_RUN_CALL_CAP}
        rows, meta = tasks_mod._fetch_with_bisect(_density_fetcher(150), wf, wt, budget)
        assert meta["failed"] == []          # 실패 마킹 없음
        assert meta["bisect_depth"] >= 1     # 최소 1회 이분
        assert meta["extra_calls"] <= tasks_mod._BISECT_RUN_CALL_CAP
        dates = sorted({r["date"] for r in rows})
        # 서브창 합집합 == 요청 span (소실 0 입증)
        assert dates[0] == wf.isoformat()
        assert dates[-1] == wt.isoformat()

    def test_depth_scales_with_density(self):
        wf, wt = dt.date(2026, 10, 11), dt.date(2026, 11, 24)
        budget = {"extra": tasks_mod._BISECT_RUN_CALL_CAP}
        _, meta = tasks_mod._fetch_with_bisect(_density_fetcher(400), wf, wt, budget)
        assert meta["bisect_depth"] >= 2

    def test_call_cap_and_min_span_guard_marks_failed(self):
        """극단 밀도 → 이분해도 캡 잔존 → 실패 마킹(콜 상한/최소창 가드)."""
        wf, wt = dt.date(2026, 10, 11), dt.date(2026, 11, 24)
        budget = {"extra": tasks_mod._BISECT_RUN_CALL_CAP}
        rows, meta = tasks_mod._fetch_with_bisect(_density_fetcher(5000), wf, wt, budget)
        assert meta["failed"]                                   # 실패 서브창 존재
        assert meta["extra_calls"] <= tasks_mod._BISECT_RUN_CALL_CAP  # 콜 상한 준수

    def test_no_truncation_no_extra_calls(self):
        """캡 미도달 → 이분 없음, extra_calls 0."""
        wf, wt = dt.date(2026, 10, 11), dt.date(2026, 11, 24)
        budget = {"extra": tasks_mod._BISECT_RUN_CALL_CAP}
        rows, meta = tasks_mod._fetch_with_bisect(_density_fetcher(10), wf, wt, budget)
        assert meta["failed"] == []
        assert meta["bisect_depth"] == 0
        assert meta["extra_calls"] == 0
