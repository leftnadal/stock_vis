"""market_pulse 알림 렌더러 — regime 전환 이벤트 문구 생성.

앱이 자기 문구를 소유(shared는 앱 무지). payload만 받아 (subject, text, html) 반환.
제목 = D-ALERTS-SUBJECT(판단 중심 하이브리드): `국면 전환: {from_kr} → {to_kr} ({stance})`.
라벨·stance는 i18n/labels.py 재사용(단일 소스, 문구 재작성 금지).
apps.ready()에서 register_market_pulse_alert_renderers()로 shared registry에 주입.
"""
from __future__ import annotations

from django.conf import settings

from apps.market_pulse.i18n.labels import KO_LABELS, resolve_regime_stance


def _regime_kr(regime: str) -> str:
    return KO_LABELS.get(f"regime.{regime}", regime)


def render_regime_transition(payload: dict) -> tuple[str, str, str]:
    date = payload.get("date", "")
    from_regime = payload.get("from_regime", "")
    to_regime = payload.get("to_regime", "")

    from_kr = _regime_kr(from_regime)
    to_kr = _regime_kr(to_regime)
    # 전환 후(to) 국면의 판단 문구 — 결정론적 매핑(status OK로 실카피 도출).
    stance, _ok = resolve_regime_stance(to_regime, "OK")

    subject = f"국면 전환: {from_kr} → {to_kr} ({stance})"

    url = f"{settings.FRONTEND_BASE_URL}/market-pulse-v2"
    text_body = (
        f"{date} 시장 국면이 {from_kr}에서 {to_kr}(으)로 전환됐습니다.\n"
        f"판단: {stance}\n\n"
        f"판단 화면: {url}"
    )
    html_body = (
        f"<p>{date} 시장 국면이 <b>{from_kr}</b> → <b>{to_kr}</b> 전환됐습니다.</p>"
        f"<p>판단: {stance}</p>"
        f'<p><a href="{url}">판단 화면 보기</a></p>'
    )
    return subject, text_body, html_body


def register_market_pulse_alert_renderers() -> None:
    """apps.ready()에서 호출 — shared alerting registry에 렌더러 주입."""
    from packages.shared.alerting.registry import register_alert_renderer

    register_alert_renderer(
        "market_pulse", "regime_transition", render_regime_transition
    )
