"""market_pulse 알림 렌더러 — regime 전환 이벤트 문구 생성.

앱이 자기 문구를 소유(shared는 앱 무지). payload만 받아 (subject, text, html) 반환.
제목 = D-ALERTS-SUBJECT(판단 중심 하이브리드): `국면 전환: {from_kr} → {to_kr} ({stance})`.
라벨·stance는 i18n/labels.py 재사용(단일 소스, 문구 재작성 금지).
apps.ready()에서 register_market_pulse_alert_renderers()로 shared registry에 주입.

MP2-ALERTS S1(D-ALERTS-RENDER): 본문을 풀 리포트로 승격.
  - 단일 경로: 리포트 본문은 판단 화면과 **동일한 `overview._build_payload()`** 소비(재계산 0).
  - 폴백: 풀 렌더가 어떤 이유로든 실패하면 디스패처가 S0 최소 본문(render_regime_transition)으로
    폴백해 발송 자체는 실패하지 않는다(fallback으로 registry 주입).
  - 디스패치 경로 LLM 호출 0(결정적·저지연).
"""
from __future__ import annotations

from typing import Any

from django.conf import settings

from apps.market_pulse.i18n.labels import KO_LABELS, resolve_regime_stance


def _regime_kr(regime: str) -> str:
    return KO_LABELS.get(f"regime.{regime}", regime)


def _sector_kr(symbol: str) -> str:
    return KO_LABELS.get(f"sector.{symbol}", symbol)


def _rule_kr(rule_id: str) -> str:
    return KO_LABELS.get(f"rule.{rule_id}", rule_id)


def _regime_subject(payload: dict) -> str:
    """제목(S0 확정 하이브리드) — transient 값만으로 산출(폴백에도 강건). 형식 불변."""
    from_kr = _regime_kr(payload.get("from_regime", ""))
    to_kr = _regime_kr(payload.get("to_regime", ""))
    stance, _ok = resolve_regime_stance(payload.get("to_regime", ""), "OK")
    return f"국면 전환: {from_kr} → {to_kr} ({stance})"


def _market_pulse_url() -> str:
    return f"{settings.FRONTEND_BASE_URL}/market-pulse-v2"


# ─────────────────────────────────────────────────────────────
# S0 최소 본문 — 풀 렌더 실패 시 디스패처 폴백(transient 값만, 재조회 0, 예외 0).
# ─────────────────────────────────────────────────────────────
def render_regime_transition(payload: dict) -> tuple[str, str, str]:
    date = payload.get("date", "")
    from_kr = _regime_kr(payload.get("from_regime", ""))
    to_kr = _regime_kr(payload.get("to_regime", ""))
    stance, _ok = resolve_regime_stance(payload.get("to_regime", ""), "OK")

    subject = _regime_subject(payload)
    url = _market_pulse_url()
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


# ─────────────────────────────────────────────────────────────
# 풀 리포트 본문 — 순수 함수(payload in → 문자열 out, 스냅샷 테스트 가능).
#   값·라벨은 payload/KO_LABELS 소스 그대로. 렌더러 내 사전/매핑 신설 0.
# ─────────────────────────────────────────────────────────────
def _fmt_pct(v: Any) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    return f"{'+' if f >= 0 else ''}{f:.2f}%"


def _report_sections(payload: dict, overview: dict) -> list[tuple[str, list[str]]]:
    """(제목, 라인 목록) 섹션 리스트 — 결측은 graceful(섹션/라인 생략, 0 변환 0)."""
    cards = overview.get("cards") or {}
    regime = cards.get("regime") or {}
    sector = cards.get("sector") or {}
    anomaly = overview.get("anomaly") or {}
    sector_deltas = overview.get("sector_deltas") or []
    anomaly_delta = overview.get("anomaly_delta") or {}

    from_kr = _regime_kr(payload.get("from_regime", ""))
    to_kr = _regime_kr(payload.get("to_regime", ""))
    stance, _ok = resolve_regime_stance(payload.get("to_regime", ""), "OK")

    sections: list[tuple[str, list[str]]] = []

    # ① 국면 전환 요약
    summary = [f"{from_kr} → {to_kr}", f"판단: {stance}"]
    if regime.get("headline"):
        summary.append(str(regime["headline"]))
    if regime.get("next_stage"):
        summary.append(f"다음 국면 전조: {_regime_kr(regime['next_stage'])}")
    sections.append(("국면 전환", summary))

    # ② 어제와 달라진 것(델타) — 국면 전환 + 섹터 순위 변동 + anomaly 신규/해소
    delta_lines: list[str] = []
    for d in sector_deltas[:3]:
        rd = d.get("rank_delta")
        if not rd:
            continue
        arrow = f"▲{rd}" if rd > 0 else f"▼{abs(rd)}"
        delta_lines.append(
            f"{_sector_kr(d.get('sector', ''))} {arrow} ({d.get('prev_rank')}위→{d.get('rank')}위)"
        )
    state = anomaly_delta.get("state")
    for r in anomaly_delta.get("new_rules", []) or []:
        delta_lines.append(f"이상 신호 신규: {_rule_kr(r)}")
    for r in anomaly_delta.get("resolved_rules", []) or []:
        delta_lines.append(f"이상 신호 해소: {_rule_kr(r)}")
    if not delta_lines and state == "no_history":
        delta_lines.append("비교할 직전 데이터 없음")
    if delta_lines:
        sections.append(("어제와 달라진 것", delta_lines))

    # ③ 전조/원인 — anomaly 활성
    fired = anomaly.get("fired") or []
    if fired:
        anomaly_lines = [f"이상 신호 모드: {anomaly.get('mode', '')}"]
        for f in fired:
            hl = f.get("headline") or _rule_kr(f.get("rule_id", ""))
            anomaly_lines.append(f"· {hl}")
        sections.append(("전조 / 이상 신호", anomaly_lines))

    # ④ 섹터 상황 — rel_strength 상위/하위
    leaders = sector.get("leaders") or []
    laggards = sector.get("laggards") or []
    if leaders or laggards:
        sec_lines: list[str] = []
        if leaders:
            sec_lines.append(
                "유입 상위: "
                + ", ".join(f"{_sector_kr(r.get('symbol', ''))}({_fmt_pct(r.get('rel_strength'))})" for r in leaders)
            )
        if laggards:
            sec_lines.append(
                "유출 하위: "
                + ", ".join(f"{_sector_kr(r.get('symbol', ''))}({_fmt_pct(r.get('rel_strength'))})" for r in laggards)
            )
        sections.append(("섹터 상황", sec_lines))

    return sections


def _render_report_bodies(payload: dict, overview: dict) -> tuple[str, str]:
    """섹션 → (plain-text, HTML 인라인스타일). 모바일 가독(통근 피크). 이미지·차트 0."""
    date = payload.get("date", "")
    url = _market_pulse_url()
    sections = _report_sections(payload, overview)

    # plain-text
    text_parts = [f"[{date}] 시장 국면 전환 리포트", ""]
    for title, lines in sections:
        text_parts.append(f"■ {title}")
        text_parts.extend(f"  {ln}" for ln in lines)
        text_parts.append("")
    text_parts.append(f"판단 화면 전체 보기: {url}")
    text_body = "\n".join(text_parts)

    # HTML(인라인 스타일 — 이메일 클라이언트 호환·모바일 가독)
    html_parts = [
        '<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:520px;'
        'margin:0 auto;color:#1e293b;font-size:15px;line-height:1.55;">',
        f'<h2 style="font-size:17px;margin:0 0 12px;">[{date}] 시장 국면 전환 리포트</h2>',
    ]
    for title, lines in sections:
        html_parts.append(
            f'<div style="margin:0 0 14px;padding:10px 12px;border:1px solid #e2e8f0;'
            f'border-radius:8px;background:#f8fafc;">'
            f'<div style="font-weight:600;font-size:13px;color:#475569;margin-bottom:6px;">{title}</div>'
        )
        for ln in lines:
            html_parts.append(f'<div style="margin:2px 0;">{ln}</div>')
        html_parts.append("</div>")
    html_parts.append(
        f'<p style="margin:16px 0 0;"><a href="{url}" '
        f'style="color:#0ea5e9;text-decoration:none;font-weight:600;">판단 화면 전체 보기 →</a></p>'
    )
    html_parts.append("</div>")
    html_body = "".join(html_parts)

    return text_body, html_body


def render_regime_transition_report(payload: dict) -> tuple[str, str, str]:
    """풀 리포트 렌더러(primary). 판단 화면과 동일한 _build_payload 소비(단일 경로).

    예외 발생 시 디스패처가 render_regime_transition(폴백)으로 대체 — 발송은 실패하지 않는다.
    """
    # 지연 import(뷰 모듈 import 사이클 회피, 기존 함수 내부 import 관례 동형).
    from apps.market_pulse.api.views.overview import _build_payload

    subject = _regime_subject(payload)
    overview = _build_payload()
    text_body, html_body = _render_report_bodies(payload, overview)
    return subject, text_body, html_body


def register_market_pulse_alert_renderers() -> None:
    """apps.ready()에서 호출 — shared alerting registry에 렌더러 주입.

    primary = 풀 리포트 / fallback = S0 최소 본문(풀 렌더 실패 시 디스패처가 사용).
    """
    from packages.shared.alerting.registry import register_alert_renderer

    register_alert_renderer(
        "market_pulse",
        "regime_transition",
        render_regime_transition_report,
        fallback=render_regime_transition,
    )
