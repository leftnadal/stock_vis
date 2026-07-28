"""전이 알림·쿨다운·마감제안·다이제스트 검증 (MON-P3-ALERT §7)."""
from datetime import date, timedelta

import pytest

from apps.monitor.models import AlertEvent, Monitor, MonitorSnapshot
from apps.monitor.services import alerts as A
from apps.monitor.services.state_machine import is_deterioration


def _eval(prev, to, asof, score=0.0, changed=None):
    """detect_and_record_alert 입력 eval_res dict."""
    return {
        "prev_state": prev,
        "state": to,
        "asof_date": asof.isoformat(),
        "state_changed": (prev != to) if changed is None else changed,
        "overall_score": score,
    }


# ── is_deterioration (순수) ────────────────────────────────────────────────


class TestIsDeterioration:
    def test_worsening(self):
        assert is_deterioration("active", "weakening") is True
        assert is_deterioration("strengthening", "active") is True
        assert is_deterioration("weakening", "critical") is True

    def test_improving(self):
        assert is_deterioration("critical", "active") is False
        assert is_deterioration("weakening", "strengthening") is False

    def test_lateral_not_deterioration(self):
        # active↔warming_up 동일 랭크(3) → 악화 아님
        assert is_deterioration("active", "warming_up") is False


# ── 전이 감지 + 멱등 ───────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDetectAndRecord:
    def test_transition_creates_alert(self, monitor):
        asof = date(2026, 7, 9)
        res = A.detect_and_record_alert(monitor, _eval("active", "weakening", asof, score=-0.3))
        assert res["created"] is True
        assert res["is_deterioration"] is True
        a = AlertEvent.objects.get()
        assert a.from_state == "active" and a.to_state == "weakening"
        assert a.is_suppressed is False

    def test_no_transition_no_alert(self, monitor):
        res = A.detect_and_record_alert(
            monitor, _eval("active", "active", date(2026, 7, 9), changed=False)
        )
        assert res["created"] is False and res["alert"] is None
        assert AlertEvent.objects.count() == 0

    def test_improvement_flagged_non_deterioration(self, monitor):
        res = A.detect_and_record_alert(
            monitor, _eval("critical", "active", date(2026, 7, 9), score=0.4)
        )
        assert res["created"] is True
        assert res["is_deterioration"] is False

    def test_idempotent_rerun(self, monitor):
        ev = _eval("active", "weakening", date(2026, 7, 9))
        A.detect_and_record_alert(monitor, ev)
        res2 = A.detect_and_record_alert(monitor, ev)  # 재실행
        assert res2["created"] is False
        assert AlertEvent.objects.count() == 1

    def test_multiple_monitors(self, user):
        m1 = Monitor.objects.create(user=user, scope="stock", target_ref="AAPL", name="A")
        m2 = Monitor.objects.create(user=user, scope="stock", target_ref="MSFT", name="B")
        A.detect_and_record_alert(m1, _eval("active", "weakening", date(2026, 7, 9)))
        A.detect_and_record_alert(m2, _eval("active", "critical", date(2026, 7, 9)))
        assert AlertEvent.objects.count() == 2


# ── 쿨다운 억제/해제 경계 ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestCooldown:
    def test_first_not_suppressed(self, monitor):
        res = A.detect_and_record_alert(monitor, _eval("active", "weakening", date(2026, 7, 1)))
        assert res["suppressed"] is False

    def test_same_direction_within_cooldown_suppressed(self, monitor):
        # 월(07-06) 악화 → 목(07-09) 재악화 = 3거래일(화수목) 이내 → 억제
        A.detect_and_record_alert(monitor, _eval("active", "weakening", date(2026, 7, 6)))
        res = A.detect_and_record_alert(monitor, _eval("weakening", "critical", date(2026, 7, 9)))
        assert res["suppressed"] is True

    def test_same_direction_beyond_cooldown_not_suppressed(self, monitor):
        # 월(07-06) 악화 → 다음주 월(07-13) = 5거래일 → 해제
        A.detect_and_record_alert(monitor, _eval("active", "weakening", date(2026, 7, 6)))
        res = A.detect_and_record_alert(monitor, _eval("weakening", "critical", date(2026, 7, 13)))
        assert res["suppressed"] is False

    def test_opposite_direction_not_suppressed(self, monitor):
        # 악화 직후 개선은 다른 방향 → 억제 안 함
        A.detect_and_record_alert(monitor, _eval("active", "weakening", date(2026, 7, 6)))
        res = A.detect_and_record_alert(monitor, _eval("weakening", "strengthening", date(2026, 7, 7)))
        assert res["suppressed"] is False

    def test_trading_days_helper(self):
        # 월(06) → 목(09): 화수목 = 3
        assert A._trading_days_between(date(2026, 7, 6), date(2026, 7, 9)) == 3
        # 월(06) → 금(10): 화수목금 = 4
        assert A._trading_days_between(date(2026, 7, 6), date(2026, 7, 10)) == 4
        # 금(10) → 월(13): 주말 제외 월 = 1
        assert A._trading_days_between(date(2026, 7, 10), date(2026, 7, 13)) == 1


# ── danger 연속 카운터 + 마감 제안 ─────────────────────────────────────────


@pytest.mark.django_db
class TestDangerStreak:
    def _snap(self, monitor, d, state):
        return MonitorSnapshot.objects.create(
            monitor=monitor, asof_date=d, overall_score=-0.7, state=state
        )

    def test_streak_below_threshold(self, monitor):
        base = date(2026, 7, 9)
        for i in range(5):
            self._snap(monitor, base - timedelta(days=i), "critical")
        newly = A.update_danger_streak(monitor, base)
        monitor.refresh_from_db()
        assert monitor.danger_streak == 5
        assert monitor.close_suggested is False
        assert newly is False

    def test_streak_reaches_threshold_new_suggestion(self, monitor):
        base = date(2026, 7, 9)
        for i in range(10):
            self._snap(monitor, base - timedelta(days=i), "critical")
        newly = A.update_danger_streak(monitor, base)
        monitor.refresh_from_db()
        assert monitor.danger_streak == 10
        assert monitor.close_suggested is True
        assert newly is True  # 직전 False → 이번 True

    def test_streak_resets_on_non_critical(self, monitor):
        base = date(2026, 7, 9)
        # 최근일 active → 연속 0
        self._snap(monitor, base, "active")
        for i in range(1, 12):
            self._snap(monitor, base - timedelta(days=i), "critical")
        A.update_danger_streak(monitor, base)
        monitor.refresh_from_db()
        assert monitor.danger_streak == 0
        assert monitor.close_suggested is False

    def test_already_suggested_not_new(self, monitor):
        base = date(2026, 7, 9)
        monitor.close_suggested = True
        monitor.save(update_fields=["close_suggested"])
        for i in range(11):
            self._snap(monitor, base - timedelta(days=i), "critical")
        newly = A.update_danger_streak(monitor, base)
        assert newly is False  # 이미 제안 상태 → 신규 아님


# ── 다이제스트 빌더 ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDigest:
    def _alert(self, monitor, to, det, asof, suppressed=False):
        return AlertEvent.objects.create(
            monitor=monitor, from_state="active", to_state=to, asof=asof,
            score=-0.3 if det else 0.3, is_deterioration=det, is_suppressed=suppressed,
        )

    def test_transition_day_has_content(self, monitor):
        asof = date(2026, 7, 9)
        self._alert(monitor, "weakening", True, asof)
        self._alert(monitor, "strengthening", False, asof)
        d = A.build_digest(asof)
        assert d["has_content"] is True
        assert len(d["deteriorations"]) == 1
        assert len(d["improvements"]) == 1

    def test_no_transition_day_empty(self, monitor):
        d = A.build_digest(date(2026, 7, 9))
        assert d["has_content"] is False
        assert d["deteriorations"] == [] and d["improvements"] == []

    def test_suggestion_only_day_has_content(self, monitor):
        # 전이 0건이지만 마감 제안 신규 → 발송 대상
        d = A.build_digest(date(2026, 7, 9), new_close_monitor_ids=[monitor.id])
        assert d["has_content"] is True
        assert len(d["close_suggestions"]) == 1

    def test_suppressed_excluded_from_rows(self, monitor):
        asof = date(2026, 7, 9)
        self._alert(monitor, "weakening", True, asof, suppressed=True)
        d = A.build_digest(asof)
        assert d["deteriorations"] == []
        assert d["has_content"] is False

    def test_render_html_and_subject(self, monitor):
        asof = date(2026, 7, 9)
        self._alert(monitor, "critical", True, asof)
        d = A.build_digest(asof)
        subject = A.render_digest_subject(d)
        html = A.render_digest_html(d)
        text = A.render_digest_text(d)
        assert "악화 1건" in subject
        assert "악화 전이" in html and monitor.name in html
        assert "악화 전이" in text

    def test_send_digest_no_content_skips(self, monitor):
        res = A.send_digest(date(2026, 7, 9))
        assert res["sent"] is False and res["reason"] == "no_content"

    def test_send_digest_no_recipient_skips(self, monitor, settings):
        settings.MONITOR_ALERT_RECIPIENT = ""
        self._alert(monitor, "weakening", True, date(2026, 7, 9))
        res = A.send_digest(date(2026, 7, 9))
        assert res["sent"] is False and res["reason"] == "no_recipient"

    def test_send_digest_delivers_when_recipient_set(self, monitor, settings):
        settings.MONITOR_ALERT_RECIPIENT = "ops@example.com"
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        self._alert(monitor, "weakening", True, date(2026, 7, 9))
        res = A.send_digest(date(2026, 7, 9))
        assert res["sent"] is True
        from django.core import mail
        assert len(mail.outbox) == 1
        assert "악화" in mail.outbox[0].subject
