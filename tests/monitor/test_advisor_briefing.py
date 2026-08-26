"""ADVISOR L-A 브리핑 서비스 검증 (MON-P4-LA T1). LLM은 mock."""
from datetime import date, datetime, timedelta

import pytest
from django.utils import timezone

from apps.monitor.models import AdvisorNote, Claim, ClaimEvidence
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
class TestCurrencyLabel:
    """B-BE-2 — 브리핑 프롬프트 통화 표기(v1.2). 숫자 정밀도는 무변, 통화 접두만 추가."""

    def test_context_defaults_usd_without_matching_stock(self, monitor):
        # stock_aapl fixture 미사용 → target_ref(AAPL)에 매칭되는 Stock 없음 → USD 폴백
        _snap(monitor, date(2026, 8, 6), 0.10)
        _snap(monitor, date(2026, 8, 7), 0.12)
        ctx = svc.build_context(monitor)
        assert ctx["currency"] == "USD"

    def test_context_reads_krw_from_stock(self, user):
        from apps.monitor.models import Monitor
        from packages.shared.stocks.models import Stock

        Stock.objects.create(symbol="005930", stock_name="Samsung", currency="KRW")
        krw_monitor = Monitor.objects.create(
            user=user, scope=Monitor.Scope.STOCK, target_ref="005930", name="삼성전자 감시"
        )
        _snap(krw_monitor, date(2026, 8, 6), 0.10)
        _snap(krw_monitor, date(2026, 8, 7), 0.12)
        ctx = svc.build_context(krw_monitor)
        assert ctx["currency"] == "KRW"

    def test_prompt_prefixes_usd_close_price_and_preserves_precision(
        self, monitor, stock_aapl
    ):
        _snap(monitor, date(2026, 8, 6), 0.10)
        _snap(monitor, date(2026, 8, 7), 0.12)
        ctx = svc.build_context(monitor)
        assert ctx["close"] is not None
        prompt = svc._render_user_prompt(ctx, True)
        assert f"현재가(종가): ${ctx['close']}" in prompt  # 숫자 원문 그대로 + $ 접두
        assert "원" not in prompt  # 기본 결함 재발 방지(임의 "원" 표기 금지)

    def test_prompt_prefixes_krw_close_price(self, user):
        from datetime import timedelta as _td

        from apps.monitor.models import Monitor
        from packages.shared.stocks.models import DailyPrice, Stock

        stock = Stock.objects.create(symbol="005930", stock_name="Samsung", currency="KRW")
        DailyPrice.objects.bulk_create([
            DailyPrice(
                stock=stock, date=date(2025, 1, 1) + _td(days=i),
                open_price=1, high_price=1, low_price=1, close_price=70000 + i, volume=1,
            )
            for i in range(300)
        ])
        krw_monitor = Monitor.objects.create(
            user=user, scope=Monitor.Scope.STOCK, target_ref="005930", name="삼성전자 감시"
        )
        _snap(krw_monitor, date(2026, 8, 6), 0.10)
        _snap(krw_monitor, date(2026, 8, 7), 0.12)
        ctx = svc.build_context(krw_monitor)
        prompt = svc._render_user_prompt(ctx, True)
        assert f"현재가(종가): ₩{ctx['close']}" in prompt

    def test_system_prompt_instructs_currency_notation(self):
        assert "통화" in svc.SYSTEM_PROMPT_V1

    def test_prompt_version_is_v1_2(self):
        assert svc.PROMPT_VERSION == "v1.2"


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
        assert note.prompt_version == "v1.2"

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


# RECON-SWAP-0813 PART 2 — 근거 점검(evidence) 컨텍스트/프롬프트 확장. D-FIXTURE-FIXED-BASE
# 준수(readings는 _READINGS_BASE=2026-08-07에 정합, 스냅샷 as_of와 동일 앵커).
@pytest.mark.django_db
class TestEvidenceContext:
    def _snap2(self, monitor):
        _snap(monitor, date(2026, 8, 6), 0.10)
        _snap(monitor, date(2026, 8, 7), 0.12)

    def test_no_active_claim_evidence_none(self, monitor, stock_aapl):
        self._snap2(monitor)
        ctx = svc.build_context(monitor)
        assert ctx["evidence"] is None

    def test_claim_without_evidences_is_unstructured(self, monitor, stock_aapl):
        self._snap2(monitor)
        Claim.objects.create(monitor=monitor, assertion="근거 없는 주장")
        ctx = svc.build_context(monitor)
        assert ctx["evidence"] == {
            "total": 0, "alive": 0, "extinct": [], "unstructured": True,
        }

    def test_all_alive_evidence(self, monitor, make_indicator, add_readings, stock_aapl):
        self._snap2(monitor)
        ind = make_indicator(name="momentum_12_1", source_key="momentum_12_1", window=10)
        add_readings(ind, [float(i) for i in range(10)], base=_READINGS_BASE)
        claim = Claim.objects.create(monitor=monitor, assertion="애플 강세")
        ClaimEvidence.objects.create(
            claim=claim, kind=ClaimEvidence.Kind.AUTO,
            indicator=ind, operator=ClaimEvidence.Operator.GTE, threshold=0.0, grace_days=5,
        )
        ClaimEvidence.objects.create(
            claim=claim, kind=ClaimEvidence.Kind.MANUAL,
            description="테마 지속", recheck_period_days=90,
            last_confirmed_at=date(2026, 8, 1),
        )
        ctx = svc.build_context(monitor)
        ev = ctx["evidence"]
        assert ev["total"] == 2
        assert ev["alive"] == 2
        assert ev["extinct"] == []
        assert ev["unstructured"] is False

    def test_dead_and_expired_listed_in_extinct(
        self, monitor, make_indicator, add_readings, stock_aapl
    ):
        self._snap2(monitor)
        ind = make_indicator(name="momentum_12_1", source_key="momentum_12_1", window=10)
        add_readings(ind, [float(i) for i in range(10)], base=_READINGS_BASE)
        claim = Claim.objects.create(monitor=monitor, assertion="애플 강세")
        # threshold=999 → 실제 스코어링으로도 항상 위반(grace_days=0) → DEAD.
        ClaimEvidence.objects.create(
            claim=claim, kind=ClaimEvidence.Kind.AUTO,
            indicator=ind, operator=ClaimEvidence.Operator.GTE, threshold=999.0, grace_days=0,
        )
        ClaimEvidence.objects.create(
            claim=claim, kind=ClaimEvidence.Kind.MANUAL,
            description="테마 후퇴", recheck_period_days=10,
            last_confirmed_at=date(2026, 8, 7) - timedelta(days=100),
        )
        ctx = svc.build_context(monitor)
        ev = ctx["evidence"]
        assert ev["total"] == 2 and ev["alive"] == 0
        assert ev["unstructured"] is False
        kinds = {item["kind"] for item in ev["extinct"]}
        assert kinds == {"auto", "manual"}
        auto_item = next(i for i in ev["extinct"] if i["kind"] == "auto")
        assert auto_item["label"] == "momentum_12_1"
        # 실제 score_indicator_dispatch 배선(mock 없음) — 과거로 갈수록 window 부족으로
        # is_sufficient=False가 되는 지점에서 streak 산출이 멈춘다(실측값, 가정값 아님).
        assert auto_item["dead_streak_days"] == 6
        manual_item = next(i for i in ev["extinct"] if i["kind"] == "manual")
        assert manual_item["label"] == "테마 후퇴"
        assert manual_item["overdue_days"] == 90


@pytest.mark.django_db
class TestRenderEvidenceLines:
    def test_none_claim_no_section(self):
        assert svc._render_evidence_lines(None) == []

    def test_unstructured(self):
        lines = svc._render_evidence_lines(
            {"total": 0, "alive": 0, "extinct": [], "unstructured": True}
        )
        assert lines == ["", "근거 점검: 근거 미등록 — 빌더에서 등록 가능"]

    def test_full_alive_one_liner(self):
        ev = {"total": 2, "alive": 2, "extinct": [], "unstructured": False}
        lines = svc._render_evidence_lines(ev)
        assert lines == ["", "근거 점검: 근거 2/2 전부 생존"]

    def test_zero_of_n_warns_and_lists(self):
        ev = {
            "total": 2, "alive": 0, "unstructured": False,
            "extinct": [
                {"kind": "auto", "label": "모멘텀", "dead_streak_days": 12},
                {"kind": "manual", "label": "테마", "overdue_days": 30},
            ],
        }
        lines = svc._render_evidence_lines(ev)
        assert lines[1] == "근거 점검: 근거 0/2 생존"
        assert "  ⚠ 등록 근거 전부 소멸 — 브리핑을 이 소멸 경고로 시작하라." in lines
        assert "  - [자동] 모멘텀: 연속 12거래일 위반(소멸)" in lines
        assert "  - [수동] 테마: 재확인 D-30" in lines

    def test_partial_alive_no_warning_directive(self):
        ev = {
            "total": 3, "alive": 2, "unstructured": False,
            "extinct": [{"kind": "auto", "label": "모멘텀", "dead_streak_days": 7}],
        }
        lines = svc._render_evidence_lines(ev)
        assert lines[1] == "근거 점검: 근거 2/3 생존"
        assert not any("소멸 경고로 시작" in ln for ln in lines)


@pytest.mark.django_db
class TestRenderUserPromptEvidenceIntegration:
    def test_prompt_includes_evidence_section(
        self, monitor, make_indicator, add_readings, stock_aapl
    ):
        ind = make_indicator(name="momentum_12_1", source_key="momentum_12_1", window=10)
        add_readings(ind, [float(i) for i in range(10)], base=_READINGS_BASE)
        _snap(monitor, date(2026, 8, 6), 0.10)
        _snap(monitor, date(2026, 8, 7), 0.12)
        claim = Claim.objects.create(monitor=monitor, assertion="애플 강세")
        ClaimEvidence.objects.create(
            claim=claim, kind=ClaimEvidence.Kind.AUTO,
            indicator=ind, operator=ClaimEvidence.Operator.GTE, threshold=0.0, grace_days=5,
        )
        ctx = svc.build_context(monitor)
        prompt = svc._render_user_prompt(ctx, False)
        assert "근거 점검: 근거 1/1 전부 생존" in prompt

    def test_prompt_omits_evidence_section_without_claim(self, monitor, stock_aapl):
        _snap(monitor, date(2026, 8, 6), 0.10)
        _snap(monitor, date(2026, 8, 7), 0.12)
        ctx = svc.build_context(monitor)
        prompt = svc._render_user_prompt(ctx, False)
        assert "근거 점검" not in prompt
