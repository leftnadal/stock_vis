"""전이 알림 감지·쿨다운·마감 제안·다이제스트 (MON-P3-ALERT).

refresh_monitors_task의 evaluate 직후 같은 태스크 내부에서 호출된다(신규 beat 없음).
- detect_and_record_alert: 전이 → AlertEvent 멱등 기록 + 쿨다운 억제 판정.
- update_danger_streak: danger(critical) 연속 거래일 → close_suggested 갱신.
- build_digest / render_digest_* / send_digest: 당일 전이·제안 요약 이메일(전이일 한정).
"""
import logging
from datetime import date, timedelta

from django.conf import settings

from apps.monitor.models import AlertEvent, Monitor
from apps.monitor.services.state_machine import is_deterioration

logger = logging.getLogger(__name__)

# 쿨다운: 동일 모니터·동일 방향 전이가 직전 알림 후 이 거래일 수 이내 재발 시 억제(기록은 유지).
COOLDOWN_TRADING_DAYS = 3
# 마감 제안: danger(critical) 상태가 이 거래일 수 이상 연속되면 제안 플래그.
DANGER_STREAK_CLOSE_THRESHOLD = 10
DANGER_STATE = "critical"


def _trading_days_between(d_from, d_to):
    """d_from(제외) ~ d_to(포함) 사이 평일 수 = 거래일 근사.

    휴장 캘린더는 도입하지 않는다(스코프 밖, D-MONITOR-BEAT 결정 2와 동일 원칙).
    """
    if d_to <= d_from:
        return 0
    n = 0
    d = d_from + timedelta(days=1)
    while d <= d_to:
        if d.weekday() < 5:
            n += 1
        d += timedelta(days=1)
    return n


def _within_cooldown(monitor, deterioration, asof):
    """동일 방향 직전 AlertEvent가 asof 기준 COOLDOWN_TRADING_DAYS 이내면 True."""
    prior = (
        AlertEvent.objects.filter(
            monitor=monitor, is_deterioration=deterioration, asof__lt=asof
        )
        .order_by("-asof")
        .first()
    )
    if prior is None:
        return False
    return _trading_days_between(prior.asof, asof) <= COOLDOWN_TRADING_DAYS


def detect_and_record_alert(monitor, eval_res):
    """evaluate 결과로 전이 감지 → AlertEvent 멱등 기록 + 쿨다운 억제 판정.

    반환: {"alert": AlertEvent|None, "created": bool, "suppressed": bool, "is_deterioration": bool}
    """
    from_state = eval_res.get("prev_state")
    to_state = eval_res["state"]
    asof = date.fromisoformat(eval_res["asof_date"])

    # 전이 없음(상태 불변) → 알림 없음
    if not eval_res.get("state_changed") or from_state == to_state:
        return {"alert": None, "created": False, "suppressed": False, "is_deterioration": False}

    deterioration = is_deterioration(from_state, to_state)
    suppressed = _within_cooldown(monitor, deterioration, asof)

    alert, created = AlertEvent.objects.get_or_create(
        monitor=monitor,
        from_state=from_state,
        to_state=to_state,
        asof=asof,
        defaults={
            "score": eval_res["overall_score"],
            "is_deterioration": deterioration,
            "is_suppressed": suppressed,
        },
    )
    return {
        "alert": alert,
        "created": created,
        "suppressed": alert.is_suppressed,
        "is_deterioration": alert.is_deterioration,
    }


def update_danger_streak(monitor, as_of):
    """danger(critical) 연속 거래일 카운트 → danger_streak·close_suggested 갱신.

    반환: 신규 제안 발생 여부(직전 False → 이번 True). 스냅샷 asof 내림차순 연속 카운트.
    """
    streak = 0
    for s in monitor.snapshots.filter(asof_date__lte=as_of).order_by("-asof_date"):
        if s.state == DANGER_STATE:
            streak += 1
        else:
            break

    was_suggested = monitor.close_suggested
    now_suggested = streak >= DANGER_STREAK_CLOSE_THRESHOLD
    if monitor.danger_streak != streak or monitor.close_suggested != now_suggested:
        monitor.danger_streak = streak
        monitor.close_suggested = now_suggested
        monitor.save(update_fields=["danger_streak", "close_suggested", "updated_at"])
    return now_suggested and not was_suggested


# ── 다이제스트 이메일 (전이일 한정, best-effort) ──────────────────────────────

_STATE_LABEL = dict(Monitor.State.choices)


def build_digest(as_of, new_close_monitor_ids=None):
    """당일(as_of) 다이제스트 데이터. 억제 알림은 개별 행에서 제외.

    반환: {"as_of", "deteriorations":[...], "improvements":[...], "close_suggestions":[...],
           "has_content": bool}
    """
    new_close_monitor_ids = set(new_close_monitor_ids or [])
    rows = list(
        AlertEvent.objects.filter(asof=as_of, is_suppressed=False)
        .select_related("monitor")
        .order_by("-is_deterioration", "monitor__name")
    )

    def _row(a):
        return {
            "monitor_name": a.monitor.name,
            "target_ref": a.monitor.target_ref,
            "from_state": a.from_state,
            "to_state": a.to_state,
            "from_label": _STATE_LABEL.get(a.from_state, a.from_state),
            "to_label": _STATE_LABEL.get(a.to_state, a.to_state),
            "score": a.score,
        }

    deteriorations = [_row(a) for a in rows if a.is_deterioration]
    improvements = [_row(a) for a in rows if not a.is_deterioration]

    close_suggestions = [
        {"monitor_name": m.name, "target_ref": m.target_ref, "danger_streak": m.danger_streak}
        for m in Monitor.objects.filter(id__in=new_close_monitor_ids)
    ]

    has_content = bool(deteriorations or improvements or close_suggestions)
    return {
        "as_of": as_of.isoformat(),
        "deteriorations": deteriorations,
        "improvements": improvements,
        "close_suggestions": close_suggestions,
        "has_content": has_content,
    }


def render_digest_subject(digest):
    """제목 = 악화 요약 우선(대시보드 상태 우선순위 문법)."""
    nd = len(digest["deteriorations"])
    ni = len(digest["improvements"])
    nc = len(digest["close_suggestions"])
    parts = []
    if nd:
        parts.append(f"악화 {nd}건")
    if nc:
        parts.append(f"마감 제안 {nc}건")
    if ni:
        parts.append(f"개선 {ni}건")
    summary = " · ".join(parts) if parts else "변동 없음"
    return f"[Monitor] {summary} ({digest['as_of']})"


def render_digest_text(digest):
    """플레인 텍스트 본문(악화 → 개선 → 마감 제안 순)."""
    lines = [f"Monitor 다이제스트 — {digest['as_of']}", ""]
    if digest["deteriorations"]:
        lines.append("■ 악화 전이")
        for r in digest["deteriorations"]:
            lines.append(
                f"  - {r['monitor_name']} [{r['target_ref']}]: "
                f"{r['from_label']} → {r['to_label']} (score {r['score']:.4f})"
            )
        lines.append("")
    if digest["improvements"]:
        lines.append("■ 개선 전이")
        for r in digest["improvements"]:
            lines.append(
                f"  - {r['monitor_name']} [{r['target_ref']}]: "
                f"{r['from_label']} → {r['to_label']} (score {r['score']:.4f})"
            )
        lines.append("")
    if digest["close_suggestions"]:
        lines.append("■ 마감 제안 (danger 연속)")
        for r in digest["close_suggestions"]:
            lines.append(
                f"  - {r['monitor_name']} [{r['target_ref']}]: "
                f"위험 {r['danger_streak']}거래일 연속 → 마감 검토 제안"
            )
    return "\n".join(lines)


def render_digest_html(digest):
    """인라인 스타일 단순 HTML(이미지 없음). 악화 → 개선 → 마감 제안 순."""
    _DET = "#c0392b"
    _IMP = "#1e824c"
    _CLOSE = "#b7791f"

    def _section(title, rows, color, kind):
        if not rows:
            return ""
        items = []
        for r in rows:
            if kind == "close":
                body = (
                    f"<strong>{r['monitor_name']}</strong> "
                    f"<span style=\"color:#888\">[{r['target_ref']}]</span> — "
                    f"위험 {r['danger_streak']}거래일 연속 → 마감 검토 제안"
                )
            else:
                body = (
                    f"<strong>{r['monitor_name']}</strong> "
                    f"<span style=\"color:#888\">[{r['target_ref']}]</span> — "
                    f"{r['from_label']} → <strong>{r['to_label']}</strong> "
                    f"<span style=\"color:#888\">(score {r['score']:.4f})</span>"
                )
            items.append(
                f'<li style="margin:6px 0;padding:8px 12px;border-left:3px solid {color};'
                f'background:#fafafa;list-style:none">{body}</li>'
            )
        return (
            f'<h3 style="color:{color};font-size:15px;margin:18px 0 6px">{title}</h3>'
            f'<ul style="margin:0;padding:0">{"".join(items)}</ul>'
        )

    body = (
        _section("악화 전이", digest["deteriorations"], _DET, "transition")
        + _section("개선 전이", digest["improvements"], _IMP, "transition")
        + _section("마감 제안", digest["close_suggestions"], _CLOSE, "close")
    )
    return (
        '<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;'
        'max-width:560px;margin:0 auto;color:#222">'
        f'<h2 style="font-size:18px;margin:0 0 4px">Monitor 다이제스트</h2>'
        f'<p style="color:#888;margin:0 0 8px">{digest["as_of"]}</p>'
        f"{body}"
        '</div>'
    )


def send_digest(as_of, new_close_monitor_ids=None):
    """전이일 한정 다이제스트 발송(best-effort). 내용 없으면 미발송.

    반환: {"sent": bool, "reason": str}. 수신자 미설정·내용 없음·발송 실패 모두 로그 후 skip.
    """
    digest = build_digest(as_of, new_close_monitor_ids=new_close_monitor_ids)
    if not digest["has_content"]:
        return {"sent": False, "reason": "no_content"}

    recipient = getattr(settings, "MONITOR_ALERT_RECIPIENT", "") or ""
    if not recipient:
        logger.warning("monitor digest skip: MONITOR_ALERT_RECIPIENT 미설정 (인앱 이중화라 best-effort)")
        return {"sent": False, "reason": "no_recipient"}

    try:
        from packages.shared.alerting.delivery.email import EmailProvider

        EmailProvider().deliver(
            subject=render_digest_subject(digest),
            text_body=render_digest_text(digest),
            html_body=render_digest_html(digest),
            destination=recipient,
        )
        logger.info(
            "monitor digest 발송: as_of=%s 악화=%d 개선=%d 마감제안=%d → %s",
            as_of,
            len(digest["deteriorations"]),
            len(digest["improvements"]),
            len(digest["close_suggestions"]),
            recipient,
        )
        return {"sent": True, "reason": "ok"}
    except Exception:  # noqa: BLE001 — best-effort, 인앱이 이중화
        logger.warning("monitor digest 발송 실패(best-effort, skip)", exc_info=True)
        return {"sent": False, "reason": "send_failed"}
