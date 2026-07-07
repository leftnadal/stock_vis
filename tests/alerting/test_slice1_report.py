"""MP2-ALERTS Slice 1 — 알림 메일 본문 풀 리포트화.

단일 경로(overview._build_payload 소비, 재계산 0) + 렌더 실패 시 S0 최소 본문 폴백(발송 무실패,
AlertDispatchLog로 식별). 제목 형식 불변. 디스패치 경로 LLM 0.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from django.core.cache import cache

from apps.market_pulse.alert_renderers import (
    _render_report_bodies,
    render_regime_transition_report,
)
from packages.shared.alerting.dispatcher import RENDER_FALLBACK_PREFIX
from packages.shared.alerting.events import AlertEvent, emit
from packages.shared.alerting.models import AlertDispatchLog, AlertSubscription


@pytest.fixture(autouse=True)
def _reset():
    cache.clear()
    yield
    cache.clear()


def _sub(dest="you@example.com"):
    return AlertSubscription.objects.create(
        source_app="market_pulse", event_type="regime_transition",
        channel="email", destination=dest, enabled=True,
    )


def _event(date="2026-07-05", frm="LATE_BULL", to="TRANSITION"):
    return AlertEvent(
        source_app="market_pulse", event_type="regime_transition",
        dedup_key=f"regime_transition:{date}:{frm}:{to}",
        payload={"date": date, "from_regime": frm, "to_regime": to},
    )


PAYLOAD = {"date": "2026-07-05", "from_regime": "LATE_BULL", "to_regime": "TRANSITION"}

# 대표 overview 픽스처(_build_payload 산출 형태 — 전환·델타·anomaly·섹터 전부).
FULL_OVERVIEW = {
    "cards": {
        "regime": {"regime": "TRANSITION", "headline": "혼재 신호", "next_stage": "BEAR_CONTRACTION"},
        "sector": {
            "leaders": [{"symbol": "XLK", "rel_strength": 2.1}, {"symbol": "XLF", "rel_strength": 1.3}],
            "laggards": [{"symbol": "XLE", "rel_strength": -1.0}],
        },
    },
    "anomaly": {"mode": "ANOMALY", "fired": [{"rule_id": "R04", "headline": "VIX 급등 감지"}]},
    "sector_deltas": [
        {"sector": "XLE", "rank_delta": 4, "prev_rank": 7, "rank": 3},
        {"sector": "XLK", "rank_delta": 0, "prev_rank": 1, "rank": 1},
    ],
    "anomaly_delta": {"state": "fired", "new_rules": ["R04"], "resolved_rules": ["R02"]},
}


class TestReportRenderPure:
    def test_snapshot_full_sections(self):
        text, html = _render_report_bodies(PAYLOAD, FULL_OVERVIEW)
        # 전환 요약(라벨·stance·headline·전조)
        assert "상승 후반 경계 → 전환" in text
        assert "혼재 신호" in text
        assert "다음 국면 전조: 약세 수축" in text
        # 델타(섹터 순위 변동 + anomaly 신규/해소, 라벨 재사용)
        assert "에너지 ▲4 (7위→3위)" in text
        assert "이상 신호 신규: VIX 급등" in text
        assert "이상 신호 해소: 집중도 극단" in text
        # rank_delta 0은 생략(XLK 델타 라인 없음)
        assert "기술 ▲" not in text and "기술 ▼" not in text
        # anomaly 활성 + 섹터 상위/하위(라벨 + %)
        assert "VIX 급등 감지" in text
        assert "유입 상위: 기술(+2.10%), 금융(+1.30%)" in text
        assert "유출 하위: 에너지(-1.00%)" in text
        # HTML은 인라인 스타일 + 이미지/차트 0
        assert "style=" in html and "<img" not in html
        assert "리포트" in html

    def test_quiet_graceful_no_data(self):
        # 결측 overview(빈 cards/anomaly) → 예외 0, 최소 요약만.
        text, html = _render_report_bodies(PAYLOAD, {"cards": {}, "anomaly": {}})
        assert "상승 후반 경계 → 전환" in text  # 전환 요약은 항상
        assert "유입 상위" not in text  # 섹터 섹션 생략
        assert "<img" not in html

    def test_no_new_label_dict(self):
        # 라벨은 KO_LABELS 재사용만 — 렌더러 모듈에 신규 dict 리터럴 매핑 0(제약).
        import apps.market_pulse.alert_renderers as mod
        src = __import__("inspect").getsource(mod)
        # regime/sector/rule 라벨 문자열을 코드에 직접 박지 않았는지(대표 라벨로 확인)
        assert "강세 확장" not in src and "기술" not in src and "VIX 급등" not in src


@pytest.mark.django_db
class TestSinglePathAndPurity:
    def test_build_payload_pure_callable_in_task_context(self):
        # M-A 검증: HTTP/DRF 컨텍스트 없이(Celery task 동형) 순수 호출 가능.
        from apps.market_pulse.api.views.overview import _build_payload

        payload = _build_payload()  # request 인자 없음
        assert isinstance(payload, dict)
        assert "cards" in payload and "sector_deltas" in payload and "anomaly_delta" in payload

    def test_full_renderer_returns_triple_and_subject_unchanged(self):
        subject, text, html = render_regime_transition_report(PAYLOAD)
        # 제목 형식 불변(S0 하이브리드): "국면 전환: {from} → {to} ({stance})"
        assert subject.startswith("국면 전환: 상승 후반 경계 → 전환 (")
        assert subject.endswith(")")
        assert isinstance(text, str) and isinstance(html, str)
        assert "리포트" in html  # 풀 리포트 본문


@pytest.mark.django_db
class TestRenderFallback:
    def test_render_exception_falls_back_to_minimal_and_logs(self, mailoutbox):
        _sub()
        # 풀 렌더의 _build_payload가 터지도록 주입 → 디스패처 폴백(S0 최소 본문).
        with patch(
            "apps.market_pulse.api.views.overview._build_payload",
            side_effect=RuntimeError("boom"),
        ):
            emit(_event())
        # 발송 자체는 실패하지 않음(1통 발송)
        assert len(mailoutbox) == 1
        mail = mailoutbox[0]
        assert "국면 전환" in mail.subject  # 제목 불변
        # 본문 = S0 최소(풀 리포트 헤딩 "리포트" 없음)
        body = mail.alternatives[0][0] if mail.alternatives else mail.body
        assert "리포트" not in body
        assert "판단 화면 보기" in body or "판단 화면:" in mail.body
        # 로그: SENT + error에 폴백 사유(발송 실패 FAILED와 구분)
        log = AlertDispatchLog.objects.get()
        assert log.status == AlertDispatchLog.Status.SENT
        assert log.error.startswith(RENDER_FALLBACK_PREFIX)
        assert "boom" in log.error

    def test_happy_path_full_report_no_fallback(self, mailoutbox):
        _sub()
        emit(_event())  # 정상 — 스냅샷 없어도 _build_payload는 예외 0(빈 cards)
        assert len(mailoutbox) == 1
        log = AlertDispatchLog.objects.get()
        assert log.status == AlertDispatchLog.Status.SENT
        assert log.error == ""  # 폴백 아님(전건 정상)
