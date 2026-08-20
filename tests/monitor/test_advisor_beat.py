"""ADVISOR beat 배선 통합 검증 (MON-P4-LA T2).

태스크 서명·PeriodicTask 등록을 실제 beat 호출 경로 그대로 검증(직접 함수 호출 대체
금지 — as_of 서명 사건 재발 방지). 등록 task 문자열이 실제 태스크로 apply 실행되는지까지.
"""
from datetime import date, datetime, timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone
from django_celery_beat.models import PeriodicTask

from apps.monitor import tasks as monitor_tasks
from apps.monitor.models import AdvisorNote, Claim, ClaimEvidence
from apps.monitor.models.monitoring import MonitorSnapshot

ADVISOR_BEAT = "advisor-daily-briefing"
ADVISOR_TASK_PATH = "apps.monitor.tasks.advisor_briefing_task"


@pytest.mark.django_db
class TestAdvisorTask:
    def test_disabled_is_noop(self, settings):
        settings.ADVISOR_ENABLED = False
        r = monitor_tasks.advisor_briefing_task.apply().get()
        assert r["status"] == "disabled"

    def test_enabled_runs_over_monitors(self, settings, monkeypatch, monitor):
        # ADVISOR_ENABLED=True + EOD 신선 → stock 모니터 loop. 스냅샷 없는 monitor는 스킵.
        settings.ADVISOR_ENABLED = True
        monkeypatch.setattr("apps.monitor.tasks.is_eod_fresh", lambda *a, **k: True)
        r = monitor_tasks.advisor_briefing_task.apply().get()
        assert r["status"] == "ok"
        assert r["created"] == 0 and r["skipped"] == 1  # AAPL, 스냅샷 없음 → 스킵

    def test_failure_isolated_per_symbol(self, settings, monkeypatch, monitor):
        # D2: 한 종목 generate_briefing 예외 → 그 종목만 failed, 태스크는 완주.
        settings.ADVISOR_ENABLED = True
        monkeypatch.setattr("apps.monitor.tasks.is_eod_fresh", lambda *a, **k: True)

        def _boom(m):
            raise RuntimeError("llm down")

        monkeypatch.setattr(
            "apps.monitor.services.advisor_briefing.generate_briefing", _boom
        )
        r = monitor_tasks.advisor_briefing_task.apply().get()
        assert r["status"] == "ok" and r["failed"] == 1


@pytest.mark.django_db
class TestAdvisorBeatEvidenceSmoke:
    """RECON-SWAP-0813 PART 2 — 근거 점검 프롬프트 라인이 실제 beat 경로
    (advisor_briefing_task → generate_briefing → build_context/_render_user_prompt)를
    통해 LLM 호출까지 배선되는지 검증. generate_briefing 직접 호출이 아니라
    advisor_briefing_task.apply()로 태운다(이 파일 계약 — as_of 서명 사건 재발 방지).
    """

    def test_evidence_lines_reach_llm_prompt_via_beat(
        self, settings, monkeypatch, monitor, make_indicator, add_readings
    ):
        from packages.shared.stocks.models import DailyPrice, Stock

        settings.ADVISOR_ENABLED = True
        monkeypatch.setattr("apps.monitor.tasks.is_eod_fresh", lambda *a, **k: True)

        stock = Stock.objects.create(symbol="AAPL")
        DailyPrice.objects.bulk_create(
            [
                DailyPrice(
                    stock=stock, date=date(2025, 1, 1) + timedelta(days=i),
                    open_price=1, high_price=1, low_price=1, close_price=100 + i, volume=1,
                )
                for i in range(300)
            ]
        )

        base = timezone.make_aware(datetime(2026, 8, 7, 12, 0))
        as_of = base.date()
        ind = make_indicator(name="momentum_12_1", source_key="momentum_12_1", window=10)
        add_readings(ind, [float(i) for i in range(10)], base=base)

        MonitorSnapshot.objects.create(
            monitor=monitor, asof_date=date(2026, 8, 6), overall_score=0.10, state="active"
        )
        MonitorSnapshot.objects.create(
            monitor=monitor, asof_date=as_of, overall_score=0.30, state="active"
        )

        claim = Claim.objects.create(monitor=monitor, assertion="애플 강세 지속")
        # 자동형 — threshold=999 → 실제 스코어링으로도 항상 위반, grace_days=0 → DEAD.
        ClaimEvidence.objects.create(
            claim=claim, kind=ClaimEvidence.Kind.AUTO,
            indicator=ind, operator=ClaimEvidence.Operator.GTE, threshold=999.0, grace_days=0,
        )
        # 수동형 — 재확인 기한 90일 경과 → EXPIRED.
        ClaimEvidence.objects.create(
            claim=claim, kind=ClaimEvidence.Kind.MANUAL,
            description="AI 테마 열기 지속", recheck_period_days=10,
            last_confirmed_at=as_of - timedelta(days=100),
        )

        captured = {}

        class _Resp:
            text = '{"headline": "h", "body": "본문 무변 확인"}'
            model = "m"
            input_tokens = 1
            output_tokens = 1

        def _fake_complete(user_prompt, **kwargs):
            captured["prompt"] = user_prompt
            return _Resp()

        monkeypatch.setattr("packages.shared.llm.complete", _fake_complete)

        r = monitor_tasks.advisor_briefing_task.apply().get()
        assert r["status"] == "ok"
        assert r["created"] == 1 and r["failed"] == 0

        prompt = captured["prompt"]
        # 기존 본문(v1.1 계약 무변) — 기존 라인이 그대로 존재
        assert "종합 점수:" in prompt
        assert "상태(달 위상):" in prompt
        assert "근거 지표 커버리지:" in prompt
        # 신규 근거 점검 라인 — 0/2 생존 + 소멸 경고 지시 + 자동/수동 상세
        assert "근거 점검: 근거 0/2 생존" in prompt
        assert "브리핑을 이 소멸 경고로 시작하라" in prompt
        # 실제 score_indicator_dispatch 배선(mock 없음) 실측값 — TestEvidenceContext와 동일 근거.
        assert "momentum_12_1: 연속 6거래일 위반(소멸)" in prompt
        assert "AI 테마 열기 지속: 재확인 D-90" in prompt

        note = AdvisorNote.objects.get(monitor=monitor, asof=as_of)
        assert note.body == "본문 무변 확인"


@pytest.mark.django_db
class TestAdvisorBeatRegistration:
    def test_task_path_matches_registered_name(self):
        # 등록될 task 문자열 = 실제 태스크의 celery 이름(서명 정합)
        assert monitor_tasks.advisor_briefing_task.name == ADVISOR_TASK_PATH

    def test_sync_registers_disabled_beat(self):
        call_command("sync_monitor_beat")
        t = PeriodicTask.objects.get(name=ADVISOR_BEAT)
        assert t.enabled is False  # 기본 OFF(이중잠금)
        assert t.task == ADVISOR_TASK_PATH
        assert t.crontab.hour == "18" and t.crontab.minute == "50"
        assert t.crontab.day_of_week == "1-5"
        assert t.crontab.timezone.key == "America/New_York"

    def test_sync_preserves_manual_enable(self):
        # get_or_create → 수동 점등 후 멱등 재실행이 되돌리지 않는다(§8 점등 보존)
        call_command("sync_monitor_beat")
        t = PeriodicTask.objects.get(name=ADVISOR_BEAT)
        t.enabled = True
        t.save()
        call_command("sync_monitor_beat")  # 재실행
        t.refresh_from_db()
        assert t.enabled is True
