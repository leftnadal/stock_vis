"""MP2-ALERTS Slice 0 — regime 전환 → 이메일 1통 + dedup 파이프라인.

E1~E6(디스패처 정책) + 제목 형식(stance 매핑) + shared/alerting의 apps import 부재.
발송 성공 경로는 locmem 백엔드(mailoutbox)로 실검증(dev 자동 폴백과 동형).
"""
from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache

from packages.shared.alerting.events import AlertEvent, emit
from packages.shared.alerting.models import AlertDispatchLog, AlertSubscription
from packages.shared.alerting.registry import AlertRendererNotRegistered


@pytest.fixture(autouse=True)
def _reset():
    cache.clear()  # circuit_breaker 상태 초기화(테스트 간 오염 차단)
    yield
    cache.clear()


def _sub(dest="you@example.com", event_type="regime_transition"):
    return AlertSubscription.objects.create(
        source_app="market_pulse", event_type=event_type,
        channel="email", destination=dest, enabled=True,
    )


def _event(date="2026-07-05", frm="TRANSITION", to="LATE_BULL"):
    return AlertEvent(
        source_app="market_pulse", event_type="regime_transition",
        dedup_key=f"regime_transition:{date}:{frm}:{to}",
        payload={"date": date, "from_regime": frm, "to_regime": to},
    )


@pytest.mark.django_db
class TestDispatchPipeline:
    def test_e1_first_transition_sends_and_logs_sent(self, mailoutbox):
        _sub()
        emit(_event())
        assert len(mailoutbox) == 1
        assert "국면 전환" in mailoutbox[0].subject
        logs = AlertDispatchLog.objects.all()
        assert logs.count() == 1
        assert logs.first().status == AlertDispatchLog.Status.SENT

    def test_e2_redispatch_same_key_no_send_no_row(self, mailoutbox):
        _sub()
        emit(_event())          # 최초 발송
        emit(_event())          # 15분 재발동 — 같은 dedup_key, 이미 sent
        assert len(mailoutbox) == 1                      # 재발송 없음
        assert AlertDispatchLog.objects.count() == 1     # 행 추가 없음

    def test_e3_flip_roundtrip_distinct_keys_both_send(self, mailoutbox):
        _sub()
        emit(_event(frm="TRANSITION", to="LATE_BULL"))
        emit(_event(frm="LATE_BULL", to="TRANSITION"))   # 왕복 — 다른 키
        assert len(mailoutbox) == 2
        assert AlertDispatchLog.objects.count() == 2

    def test_e4_failure_then_retry_succeeds_single_row(self, mailoutbox):
        _sub()
        failing = MagicMock()
        failing.deliver.side_effect = RuntimeError("SMTP down")
        with patch("packages.shared.alerting.dispatcher.get_provider", return_value=failing):
            with pytest.raises(RuntimeError):
                emit(_event())
        log = AlertDispatchLog.objects.get()
        assert log.status == AlertDispatchLog.Status.FAILED
        assert "SMTP down" in log.error
        # 다음 사이클 자연 재시도 — 같은 dedup_key, failed라 재발송 시도 → 성공
        emit(_event())
        log.refresh_from_db()
        assert log.status == AlertDispatchLog.Status.SENT
        assert AlertDispatchLog.objects.count() == 1     # 행 중복 없음
        assert len(mailoutbox) == 1

    def test_e5_no_subscription_marks_sent_no_send(self, mailoutbox):
        # 구독 0 → 발송 0이지만 억제는 정상(에러 아님) → sent
        emit(_event())
        assert len(mailoutbox) == 0
        assert AlertDispatchLog.objects.get().status == AlertDispatchLog.Status.SENT

    def test_e6_missing_renderer_failed_and_raises(self, mailoutbox):
        _sub(event_type="unknown_event")
        evt = AlertEvent(
            source_app="market_pulse", event_type="unknown_event",
            dedup_key="unknown_event:x", payload={},
        )
        with pytest.raises(AlertRendererNotRegistered):
            emit(evt)                                    # 예외 전파(트리거는 별도 task라 격리)
        log = AlertDispatchLog.objects.get()
        assert log.status == AlertDispatchLog.Status.FAILED
        assert "unknown_event" in log.error
        assert len(mailoutbox) == 0


@pytest.mark.django_db
def test_subject_uses_stance_mapping():
    from apps.market_pulse.alert_renderers import render_regime_transition

    subject, text, html = render_regime_transition(
        {"date": "2026-07-05", "from_regime": "LATE_BULL", "to_regime": "TRANSITION"}
    )
    # 판단 중심 하이브리드: 국면 전환: {from_kr} → {to_kr} ({stance})
    assert subject.startswith("국면 전환: 상승 후반 경계 → 전환 (")
    assert "관망" in subject          # TRANSITION stance(labels.py REGIME_STANCE) 정합
    assert "market-pulse-v2" in text and "market-pulse-v2" in html


def test_alerting_has_no_apps_import():
    """shared/alerting은 apps.*를 import하지 않는다(경계 — AST 스캔)."""
    root = Path(__file__).resolve().parents[2] / "packages" / "shared" / "alerting"
    offenders = []
    for py in root.rglob("*.py"):
        tree = ast.parse(py.read_text(), filename=str(py))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("apps"):
                offenders.append(f"{py.name}:{node.lineno} from {node.module}")
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.name.startswith("apps"):
                        offenders.append(f"{py.name}:{node.lineno} import {a.name}")
    assert offenders == [], f"shared/alerting apps import 위반: {offenders}"
