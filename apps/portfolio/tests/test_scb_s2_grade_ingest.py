"""SCB-CONTEXT-S2 — ingest_analyst_grades 배선 테스트 (배선 후보 ②).

③ FMPRateLimitError 시 중단 + 기존 행 무손상 — `capture_symbols` halt 규율 복제 검증.
기존 4콜 계약(`_fetch_signals`)은 무접촉이므로 여기서 다루지 않는다.
"""
import pytest

from apps.portfolio import tasks as portfolio_tasks
from packages.shared.api_request.providers.fmp.client import FMPRateLimitError
from packages.shared.stocks.models import AnalystGradeChange


def _row(symbol, date, company, prev, new, action):
    return {
        "symbol": symbol, "date": date, "gradingCompany": company,
        "previousGrade": prev, "newGrade": new, "action": action,
    }


class GradesClient:
    """limit_on 심볼에서 카운터 소진 → FMPRateLimitError."""

    def __init__(self, limit_on=None):
        self.limit_on = (limit_on or "").upper()
        self.calls = []

    def get_grades(self, symbol):
        self.calls.append(symbol.upper())
        if symbol.upper() == self.limit_on:
            raise FMPRateLimitError("Daily API limit exceeded")
        return [_row(symbol.upper(), "2026-01-05", "Argus", "Hold", "Buy", "upgrade")]


@pytest.fixture(autouse=True)
def _no_close_all(monkeypatch):
    """close_all()(fork 안전, 버그 #25)은 실워커 전용 — 테스트 트랜잭션 보존 위해 no-op.

    선례: test_sfi_split_guard.py:45 · test_slice20a_backend.py:67.
    """
    from django.db import connections

    monkeypatch.setattr(connections, "close_all", lambda: None)


@pytest.fixture
def _universe(monkeypatch):
    monkeypatch.setattr(portfolio_tasks, "_coach_universe", lambda: ["AAPL", "GEV", "TLN"])


@pytest.mark.django_db
def test_halts_on_rate_limit_and_leaves_prior_rows_intact(monkeypatch, _universe):
    """③ 소진 심볼에서 즉시 중단 · 이전 심볼 적재분 무손상 · 이후 심볼 미시도."""
    client = GradesClient(limit_on="GEV")
    monkeypatch.setattr(portfolio_tasks, "FMPClient", lambda api_key=None: client)

    summary = portfolio_tasks.ingest_analyst_grades.apply().get()

    assert summary["halted_rate_limit"] is True
    assert "GEV" in summary["errors"]
    assert client.calls == ["AAPL", "GEV"]           # TLN은 시도조차 안 함
    assert summary["created"] == 1                    # AAPL만 적재
    assert AnalystGradeChange.objects.filter(symbol="AAPL").count() == 1
    assert AnalystGradeChange.objects.filter(symbol="TLN").count() == 0


@pytest.mark.django_db
def test_symbol_failure_is_isolated(monkeypatch, _universe):
    """rate-limit 아닌 실패는 그 심볼만 건너뛰고 계속한다."""
    class Flaky(GradesClient):
        def get_grades(self, symbol):
            self.calls.append(symbol.upper())
            if symbol.upper() == "GEV":
                raise ValueError("boom")
            return [_row(symbol.upper(), "2026-01-05", "Argus", "Hold", "Buy", "upgrade")]

    client = Flaky()
    monkeypatch.setattr(portfolio_tasks, "FMPClient", lambda api_key=None: client)
    summary = portfolio_tasks.ingest_analyst_grades.apply().get()

    assert summary["halted_rate_limit"] is False
    assert "GEV" in summary["errors"]
    assert client.calls == ["AAPL", "GEV", "TLN"]     # 중단 없음
    assert summary["created"] == 2
    assert AnalystGradeChange.objects.count() == 2


@pytest.mark.django_db
def test_rerun_is_idempotent(monkeypatch, _universe):
    """① 배선 관통 멱등 — 2회 실행에도 행 수 불변."""
    client = GradesClient()
    monkeypatch.setattr(portfolio_tasks, "FMPClient", lambda api_key=None: client)

    first = portfolio_tasks.ingest_analyst_grades.apply().get()
    assert first["created"] == 3 and first["updated"] == 0
    second = portfolio_tasks.ingest_analyst_grades.apply().get()
    assert second["created"] == 0 and second["updated"] == 3
    assert AnalystGradeChange.objects.count() == 3


@pytest.mark.django_db
def test_empty_universe_makes_no_call(monkeypatch):
    """유니버스 0 → client 미생성·콜 0."""
    monkeypatch.setattr(portfolio_tasks, "_coach_universe", lambda: [])
    called = {"n": 0}
    monkeypatch.setattr(
        portfolio_tasks, "FMPClient",
        lambda api_key=None: called.__setitem__("n", called["n"] + 1),
    )
    summary = portfolio_tasks.ingest_analyst_grades.apply().get()
    assert summary["universe"] == 0
    assert called["n"] == 0
    assert AnalystGradeChange.objects.count() == 0


@pytest.mark.django_db
def test_empty_response_is_not_an_error(monkeypatch, _universe):
    """② 빈 응답·무행 → 에러 아님, 행 0."""
    class Empty(GradesClient):
        def get_grades(self, symbol):
            self.calls.append(symbol.upper())
            return []

    monkeypatch.setattr(portfolio_tasks, "FMPClient", lambda api_key=None: Empty())
    summary = portfolio_tasks.ingest_analyst_grades.apply().get()
    assert summary["errors"] == {}
    assert summary["created"] == 0 and summary["fetched"] == 0
    assert AnalystGradeChange.objects.count() == 0
