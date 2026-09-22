"""PRICE-FRESH-1-B §A-3 — 메일에 종가 날짜 (MM-DD) 표기.

근거: 2026-09-18 실물 메일이 헤더 as_of=09-17인데 종가는 09-14 값(286.52)이었고
메일만으로 그 불일치를 알 수 없었다. 날짜 표기가 결함을 자가 노출시킨다.
텍스트·HTML은 공용 헬퍼(_close_with_date)를 쓰므로 문구가 갈라지지 않는다.
"""
from datetime import date

import pytest

from apps.monitor.services.alerts import (
    build_digest,
    render_digest_html,
    render_digest_text,
)

AS_OF = date(2026, 9, 17)


def _ev(close_date="2026-09-14"):
    return [{
        "type": "near_stop", "claim_id": "x", "monitor_name": "탈렌", "target_ref": "TLN",
        "close": 286.52, "stop": 271.2, "to_stop_pct": -5.35, "band_pct": 7.07,
        "close_date": close_date, "recheck": False, "immediate": True,
    }]


@pytest.mark.django_db
class TestCloseDateRender:
    def test_text_shows_close_date(self):
        body = render_digest_text(build_digest(AS_OF, scenario_events=_ev()))
        assert "종가 286.52 (09-14)" in body

    def test_html_shows_close_date(self):
        html = render_digest_html(build_digest(AS_OF, scenario_events=_ev()))
        assert "종가 286.52 (09-14)" in html

    def test_both_renderers_agree(self):
        """드리프트 금지 — 두 렌더가 같은 종가 문자열을 쓴다."""
        d = build_digest(AS_OF, scenario_events=_ev())
        frag = "286.52 (09-14)"
        assert frag in render_digest_text(d) and frag in render_digest_html(d)

    def test_stale_gap_is_visible_against_header(self):
        """★ 이 표기의 목적: 헤더 as_of와 종가 날짜의 불일치가 메일에서 보인다."""
        d = build_digest(AS_OF, scenario_events=_ev())
        body = render_digest_text(d)
        assert "2026-09-17" in body      # 헤더 as_of
        assert "(09-14)" in body         # 실제 종가 날짜 — 3일 차이가 드러난다

    def test_missing_close_date_degrades_gracefully(self):
        """close_date 없으면 날짜 없이 종가만 — 렌더가 죽지 않는다."""
        body = render_digest_text(build_digest(AS_OF, scenario_events=_ev(close_date=None)))
        assert "종가 286.52 /" in body
        assert "(" not in body.split("종가 286.52")[1].split("/")[0]

    def test_digest_carries_close_date(self):
        d = build_digest(AS_OF, scenario_events=_ev())
        assert d["near_stops"][0]["close_date"] == "2026-09-14"
