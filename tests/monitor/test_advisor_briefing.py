"""ADVISOR L-A 브리핑 서비스 검증 (MON-P4-LA T1). LLM은 mock."""
from datetime import date, datetime, timedelta

import pytest
from django.utils import timezone

from apps.monitor.models import AdvisorNote
from apps.monitor.models.monitoring import MonitorSnapshot
from apps.monitor.services import advisor_briefing as svc

# readings 앵커 = 스냅샷 as_of(2026-08-07)에 정합 — now 앵커 시 asof<= 필터가
# readings를 전량 배제해 coverage_n=0이 되는 fixture time-bomb 방지.
_READINGS_BASE = timezone.make_aware(datetime(2026, 8, 7, 12, 0))


class _Resp:
    """packages.shared.llm.complete 반환 LLMResponse 대역."""

    def __init__(self, text, model="claude-sonnet-4-5", it=120, ot=60):
        self.text = text
        self.model = model
        self.input_tokens = it
        self.output_tokens = ot


def _mock_complete(monkeypatch, text):
    monkeypatch.setattr(
        "packages.shared.llm.complete", lambda *a, **k: _Resp(text)
    )


@pytest.fixture
def stock_aapl(db):
    from packages.shared.stocks.models import DailyPrice, Stock

    stock = Stock.objects.create(symbol="AAPL")
    # 시작일을 as_of(2026-08-07) 훨씬 이전으로 — 300행 전부 as_of 이하에 들어오게(source_n 충분)
    DailyPrice.objects.bulk_create([
        DailyPrice(
            stock=stock, date=date(2025, 1, 1) + timedelta(days=i),
            open_price=1, high_price=1, low_price=1, close_price=100 + i, volume=1,
        )
        for i in range(300)
    ])
    return stock


def _snap(monitor, d, score, state="active"):
    return MonitorSnapshot.objects.create(
        monitor=monitor, asof_date=d, overall_score=score, state=state
    )


@pytest.mark.django_db
class TestBuildContext:
    def test_none_without_snapshot(self, monitor):
        assert svc.build_context(monitor) is None

    def test_coverage_denominator_not_hardcoded_9(self, monitor, make_indicator, add_readings, stock_aapl):
        # 지표 2개만 등록 → 분모=2 (9 하드코딩 아님)
        for k in ("momentum_12_1", "volume_ratio"):
            ind = make_indicator(name=k, source_key=k, window=10)
            add_readings(ind, [float(i) for i in range(10)], base=_READINGS_BASE)
        _snap(monitor, date(2026, 8, 6), 0.10)
        _snap(monitor, date(2026, 8, 7), 0.12)
        ctx = svc.build_context(monitor)
        assert ctx["coverage_total"] == 2
        assert ctx["coverage_n"] == 2  # DailyPrice 300 → 둘 다 충분
        assert ctx["delta"] == pytest.approx(0.02)
        assert ctx["overall_score"] == 0.12

    def test_v11_state_display_and_score_precision(self, monitor, make_indicator, add_readings, stock_aapl):
        # v1.1: 상태=화면 display 달위상 어휘 · 점수 4자리 그대로 프롬프트 인용
        from apps.monitor.services.state_machine import score_to_phase

        ind = make_indicator(name="momentum_12_1", source_key="momentum_12_1", window=10)
        add_readings(ind, [float(i) for i in range(10)], base=_READINGS_BASE)
        _snap(monitor, date(2026, 8, 7), 0.1234)
        ctx = svc.build_context(monitor)
        assert ctx["state_display"] == score_to_phase(0.1234)["label"]
        prompt = svc._render_user_prompt(ctx, True)
        assert ctx["state_display"] in prompt  # 달 위상 어휘 통일
        assert "달 위상" in prompt
        assert "+0.1234" in prompt  # 점수 4자리 그대로(반올림 금지 원문)


@pytest.mark.django_db
class TestUnchanged:
    def _ctx(self, monitor, delta, state, prev_state):
        return {
            "symbol": "AAPL", "asof": date(2026, 8, 7), "overall_score": 0.1,
            "delta": delta, "state": state, "prev_state": prev_state,
            "coverage_n": 6, "coverage_total": 9, "indicators": [],
            "close": 150.0, "levels": [], "claim": None,
        }

    def test_unchanged_all_quiet(self, monitor):
        # 상태 동일 + |Δ|<0.02 + claim 없음(미교차) → 무변화
        assert svc.is_unchanged(self._ctx(monitor, 0.01, "active", "active"), monitor) is True

    def test_changed_by_delta(self, monitor):
        assert svc.is_unchanged(self._ctx(monitor, 0.05, "active", "active"), monitor) is False

    def test_changed_by_state_transition(self, monitor):
        assert svc.is_unchanged(self._ctx(monitor, 0.01, "active", "warming_up"), monitor) is False


@pytest.mark.django_db
class TestGenerateBriefing:
    def _prep(self, monitor, make_indicator, add_readings):
        ind = make_indicator(name="momentum_12_1", source_key="momentum_12_1", window=10)
        add_readings(ind, [float(i) for i in range(10)], base=_READINGS_BASE)
        _snap(monitor, date(2026, 8, 6), 0.10)
        _snap(monitor, date(2026, 8, 7), 0.30)  # Δ=0.2 변화

    def test_creates_note(self, monkeypatch, monitor, make_indicator, add_readings, stock_aapl):
        self._prep(monitor, make_indicator, add_readings)
        _mock_complete(monkeypatch, '{"headline": "GEV 강세 지속", "body": "근거 지표 1/1, 목표까지 여유."}')
        note = svc.generate_briefing(monitor)
        assert note is not None
        assert note.headline == "GEV 강세 지속"
        assert note.asof == date(2026, 8, 7)
        assert note.surface == AdvisorNote.Surface.L_A
        assert note.coverage_total == 1 and note.coverage_n == 1
        assert note.model_id == "claude-sonnet-4-5"
        assert note.input_tokens == 120 and note.output_tokens == 60
        assert note.prompt_version == "v1.1"

    def test_idempotent_skip(self, monkeypatch, monitor, make_indicator, add_readings, stock_aapl):
        self._prep(monitor, make_indicator, add_readings)
        AdvisorNote.objects.create(
            monitor=monitor, asof=date(2026, 8, 7), surface=AdvisorNote.Surface.L_A,
            headline="기존", body="b", coverage_n=1, coverage_total=1,
            model_id="m", prompt_version="v1",
        )
        _mock_complete(monkeypatch, '{"headline": "새것", "body": "b"}')
        assert svc.generate_briefing(monitor) is None
        assert AdvisorNote.objects.filter(monitor=monitor, asof=date(2026, 8, 7)).count() == 1

    def test_lexical_guard_rejects(self, monkeypatch, monitor, make_indicator, add_readings, stock_aapl):
        self._prep(monitor, make_indicator, add_readings)
        _mock_complete(monkeypatch, '{"headline": "지금 매수하세요", "body": "b"}')
        assert svc.generate_briefing(monitor) is None
        assert not AdvisorNote.objects.filter(monitor=monitor).exists()

    def test_parse_failure_silent(self, monkeypatch, monitor, make_indicator, add_readings, stock_aapl):
        self._prep(monitor, make_indicator, add_readings)
        _mock_complete(monkeypatch, "이건 JSON이 아님")
        assert svc.generate_briefing(monitor) is None
        assert not AdvisorNote.objects.filter(monitor=monitor).exists()

    def test_llm_exception_silent(self, monkeypatch, monitor, make_indicator, add_readings, stock_aapl):
        self._prep(monitor, make_indicator, add_readings)

        def _boom(*a, **k):
            raise RuntimeError("api down")

        monkeypatch.setattr("packages.shared.llm.complete", _boom)
        assert svc.generate_briefing(monitor) is None
        assert not AdvisorNote.objects.filter(monitor=monitor).exists()

    def test_no_snapshot_skip(self, monkeypatch, monitor, stock_aapl):
        _mock_complete(monkeypatch, '{"headline": "h", "body": "b"}')
        assert svc.generate_briefing(monitor) is None
