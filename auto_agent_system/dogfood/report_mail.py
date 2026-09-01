"""AGENT-S1 1단계 — 전일 대비 diff 3분류 + 메일 발송.

분류: **신규**(어제 정상/부재 → 오늘 비정상) · **재발 N일째**(연속 비정상) ·
**해소**(어제 비정상 → 오늘 정상). 변화가 없으면 3줄 요약으로 끝낸다 —
매일 오는 메일이 길면 안 읽히고, 안 읽히는 점검은 없는 것과 같다.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .check_quant import OK, OUT_DIR

MAIL_TO = os.getenv("DOGFOOD_MAIL_TO", "jinie545@gmail.com")
FOOTER = "1단계(정량)입니다. 루브릭 채점·관찰 후보는 2·3단계에서 추가됩니다."

_FNAME = re.compile(r"^quant_(\d{8})\.json$")


@dataclass
class Change:
    key: str
    note: str
    status: str
    streak: int = 1  # 재발 연속 일수


def load_reports(out_dir: Path) -> list[tuple[date, dict[str, Any]]]:
    """디렉토리의 리포트를 날짜 오름차순으로."""
    rows: list[tuple[date, dict[str, Any]]] = []
    for path in sorted(out_dir.glob("quant_*.json")):
        m = _FNAME.match(path.name)
        if not m:
            continue
        stamp = m.group(1)
        try:
            day = date(int(stamp[:4]), int(stamp[4:6]), int(stamp[6:]))
            rows.append((day, json.loads(path.read_text(encoding="utf-8"))))
        except (ValueError, json.JSONDecodeError):
            continue
    return rows


def _bad(check: dict[str, Any]) -> bool:
    return check.get("status") != OK


def _streak(key: str, history: list[tuple[date, dict[str, Any]]]) -> int:
    """오늘 포함, 이 항목이 연속으로 비정상인 일수. history는 오래된→최신."""
    count = 0
    for _, report in reversed(history):
        check = (report.get("checks") or {}).get(key)
        if check is None or not _bad(check):
            break
        count += 1
    return count


def classify(history: list[tuple[date, dict[str, Any]]]) -> dict[str, Any]:
    """history 마지막이 오늘. 전일 리포트가 없으면 baseline."""
    if not history:
        return {"baseline": [], "new": [], "recurring": [], "resolved": [], "_baseline_day": True}

    today = history[-1][1]
    checks = today.get("checks") or {}

    if len(history) == 1:
        return {
            "baseline": [
                Change(k, v.get("note", ""), v.get("status", "")) for k, v in checks.items() if _bad(v)
            ],
            "new": [], "recurring": [], "resolved": [], "_baseline_day": True,
        }

    prev = history[-2][1].get("checks") or {}
    new: list[Change] = []
    recurring: list[Change] = []
    resolved: list[Change] = []

    for key, check in checks.items():
        was = prev.get(key)
        if _bad(check):
            if was is None or not _bad(was):
                new.append(Change(key, check.get("note", ""), check.get("status", "")))
            else:
                recurring.append(
                    Change(key, check.get("note", ""), check.get("status", ""), _streak(key, history))
                )
        elif was is not None and _bad(was):
            resolved.append(Change(key, check.get("note", ""), check.get("status", "")))

    return {"baseline": [], "new": new, "recurring": recurring, "resolved": resolved,
            "_baseline_day": False}


def is_baseline(groups: dict[str, Any]) -> bool:
    """비교 대상(전일 리포트)이 없던 날인지. classify가 baseline 키에만 담는다."""
    return groups.get("_baseline_day", False) is True


def _summary_lines(report: dict[str, Any], groups: dict[str, Any]) -> list[str]:
    s = report.get("summary") or {}
    market = report.get("market") or {}
    holiday = market.get("run_date_holiday")

    lines = [
        f"대상 세션 {report.get('session_date')} · 정량 {s.get('passed')}/{s.get('total')} 통과"
        f" (주의 {s.get('warn')} / 실패 {s.get('failed')})",
    ]
    if holiday:
        lines.append(f"실행일은 미국장 휴장({holiday}) — 신선도 판정은 직전 거래일 기준입니다.")
    if is_baseline(groups):
        lines.append("기준일 — 전일 리포트가 없어 비교하지 않았습니다. 내일부터 신규/재발/해소를 구분합니다.")
    elif groups["new"] or groups["recurring"] or groups["resolved"]:
        lines.append(
            f"신규 {len(groups['new'])} · 재발 {len(groups['recurring'])} · 해소 {len(groups['resolved'])}"
        )
    else:
        lines.append("전일 대비 변화 없음.")
    if report.get("auth_mode") != "token":
        lines.append("API는 무인증 모드로 점검했습니다(엔드포인트 존재만 확인 — 스키마·빈 응답 미검사).")
    return lines


def render_body(report: dict[str, Any], groups: dict[str, Any]) -> str:
    parts: list[str] = list(_summary_lines(report, groups))
    body = ["\n".join(parts), ""]

    if groups["baseline"]:
        body.append("■ 기준일 — 전일 리포트가 없어 비교하지 않았습니다. 오늘의 비정상 항목:")
        body += [f"  · {c.key} — {c.note}" for c in groups["baseline"]] or ["  · 없음"]
        body.append("")

    if groups["new"]:
        body.append("■ 신규")
        body += [f"  · [{c.status}] {c.key} — {c.note}" for c in groups["new"]]
        body.append("")
    if groups["recurring"]:
        body.append("■ 재발")
        body += [f"  · [{c.status}] {c.key} — {c.streak}일째 — {c.note}" for c in groups["recurring"]]
        body.append("")
    if groups["resolved"]:
        body.append("■ 해소")
        body += [f"  · {c.key} — {c.note}" for c in groups["resolved"]]
        body.append("")

    changed = is_baseline(groups) or any(groups[k] for k in ("new", "recurring", "resolved"))
    if changed:
        body.append("■ 전체 상세")
        for key, check in (report.get("checks") or {}).items():
            body.append(f"  {check.get('status', '?'):>4}  {key:<34} {check.get('note', '')}")
        body.append("")

    body.append(FOOTER)
    return "\n".join(body)


def render_subject(report: dict[str, Any]) -> str:
    s = report.get("summary") or {}
    run = report.get("run_date") or ""
    try:
        d = date.fromisoformat(run)
        stamp = f"{d.month}/{d.day}"
    except ValueError:
        stamp = run
    return f"Stock-Vis 야간 점검 — {stamp} (정량 {s.get('passed')}/{s.get('total')} 통과)"


def build_mail(out_dir: Path | None = None) -> tuple[str, str, dict[str, Any]]:
    history = load_reports(out_dir or OUT_DIR)
    if not history:
        raise SystemExit("리포트가 없습니다 — check_quant.py를 먼저 실행하세요.")
    report = history[-1][1]
    groups = classify(history)
    return render_subject(report), render_body(report, groups), groups


def send(subject: str, body: str, to: str = MAIL_TO) -> int:
    """Django SMTP 설정 재사용. 값은 절대 출력하지 않는다.

    구현은 `auto_agent_system.common.mail.send` — healthcheck 에이전트와 공유한다
    (OPS-HEALTHCHECK-NIGHTLY-WIRE). 이 래퍼는 기존 호출부·테스트 호환용.
    """
    from ..common.mail import send as _send

    return _send(subject, body, to)


def main() -> int:
    parser = argparse.ArgumentParser(description="야간 도그푸딩 diff + 메일")
    parser.add_argument("--out-dir", help="리포트 디렉토리")
    parser.add_argument("--to", default=MAIL_TO, help="수신자")
    parser.add_argument("--dry-run", action="store_true", help="발송 없이 본문만 출력")
    args = parser.parse_args()

    subject, body, _ = build_mail(Path(args.out_dir) if args.out_dir else None)
    if args.dry_run:
        print(subject)
        print("-" * 72)
        print(body)
        return 0
    sent = send(subject, body, args.to)
    print(f"발송 {sent}건 → {args.to} · {subject}")
    return 0 if sent else 1


if __name__ == "__main__":
    raise SystemExit(main())
