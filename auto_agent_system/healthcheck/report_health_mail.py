"""health_check JSON → 전일 대비 diff → 메일 (OPS-HEALTHCHECK-NIGHTLY-WIRE).

dogfood의 `report_mail`과 같은 3분류(신규/재발 N일째/해소) 개념을 쓰되, 스키마가
근본적으로 달라 로직은 공유하지 않는다:
  - dogfood      : {"checks": {key: {"status": "ok"|"warn"|"fail", ...}}}
  - health_check : [{"name", "status": 0|1|2, "status_label", "detail", "evidence"}]
메일 발송(`common.mail.send`)만 공유한다.

**조용한 날은 보내지 않는다** — 변화 0 + ERROR 0이면 발송하지 않는다(매일 오는
무의미한 메일이 섞이면 읽히지 않는다). 다만 월요일은 "살아 있음"을 확인하기 위해
이상이 없어도 1통 보낸다(잡이 죽은 것과 조용한 것을 구별하기 위함).
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

OUT_DIR = Path(os.getenv("HEALTHCHECK_OUT_DIR", str(Path.home() / "stock-vis-nightly" / "health")))
MAIL_TO = os.getenv("HEALTHCHECK_MAIL_TO", os.getenv("AGENT_MAIL_TO", "jinie545@gmail.com"))

OK, WARN, ERROR = 0, 1, 2
STATUS_MARK = {OK: "✅", WARN: "⚠️", ERROR: "❌"}

_FNAME = re.compile(r"^health_(\d{8})\.json$")
FOOTER = "하네스 점검(scripts/health_check.py) 자동 보고입니다. 변화가 없는 날은 발송하지 않습니다(월요일 제외)."


@dataclass
class Change:
    name: str
    status: int
    detail: str
    streak: int = 1  # 재발 연속 일수


def load_reports(out_dir: Path) -> list[tuple[date, list[dict[str, Any]]]]:
    """디렉터리의 리포트를 날짜 오름차순으로. 손상 파일은 건너뛴다."""
    rows: list[tuple[date, list[dict[str, Any]]]] = []
    for path in sorted(out_dir.glob("health_*.json")):
        m = _FNAME.match(path.name)
        if not m:
            continue
        stamp = m.group(1)
        try:
            day = date(int(stamp[:4]), int(stamp[4:6]), int(stamp[6:]))
            data = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, json.JSONDecodeError, OSError):
            continue
        if isinstance(data, list):
            rows.append((day, data))
    return rows


def as_map(report: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """항목 이름 → 항목. health_check는 리스트로 내보내므로 비교용으로 뒤집는다."""
    return {c.get("name", ""): c for c in report if isinstance(c, dict)}


def _bad(check: dict[str, Any]) -> bool:
    return int(check.get("status", OK)) > OK


def _streak(name: str, history: list[tuple[date, list[dict[str, Any]]]]) -> int:
    """오늘 포함, 이 항목이 연속으로 비정상인 일수. history는 오래된→최신."""
    count = 0
    for _, report in reversed(history):
        check = as_map(report).get(name)
        if check is None or not _bad(check):
            break
        count += 1
    return count


def classify(history: list[tuple[date, list[dict[str, Any]]]]) -> dict[str, Any]:
    """history 마지막이 오늘. 전일 리포트가 없으면 baseline."""
    if not history:
        return {"baseline": [], "new": [], "recurring": [], "resolved": [], "_baseline_day": True}

    today = as_map(history[-1][1])

    if len(history) == 1:
        return {
            "baseline": [
                Change(k, int(v.get("status", OK)), v.get("detail", ""))
                for k, v in today.items()
                if _bad(v)
            ],
            "new": [],
            "recurring": [],
            "resolved": [],
            "_baseline_day": True,
        }

    prev = as_map(history[-2][1])
    new: list[Change] = []
    recurring: list[Change] = []
    resolved: list[Change] = []

    for name, check in today.items():
        was = prev.get(name)
        status = int(check.get("status", OK))
        detail = check.get("detail", "")
        if _bad(check):
            if was is None or not _bad(was):
                new.append(Change(name, status, detail))
            else:
                recurring.append(Change(name, status, detail, _streak(name, history)))
        elif was is not None and _bad(was):
            resolved.append(Change(name, status, detail))

    return {
        "baseline": [],
        "new": new,
        "recurring": recurring,
        "resolved": resolved,
        "_baseline_day": False,
    }


def is_baseline(groups: dict[str, Any]) -> bool:
    return groups.get("_baseline_day", False) is True


def counts(report: list[dict[str, Any]]) -> dict[int, int]:
    out = {OK: 0, WARN: 0, ERROR: 0}
    for c in report:
        s = int(c.get("status", OK))
        if s in out:
            out[s] += 1
    return out


def should_send(groups: dict[str, Any], report: list[dict[str, Any]], today: date) -> tuple[bool, str]:
    """발송 여부 + 사유. 조용한 날(변화 0 · ERROR 0)은 보내지 않는다."""
    if is_baseline(groups):
        return True, "첫 수집(baseline)"
    if counts(report)[ERROR] > 0:
        return True, "ERROR 존재"
    if groups["new"]:
        return True, "신규 이상"
    if groups["resolved"]:
        return True, "해소 보고"
    if today.weekday() == 0:  # 월요일 — 잡이 살아 있음을 확인
        return True, "주간 확인(월)"
    return False, "변화 없음·ERROR 0 — 발송 생략"


def render_subject(report: list[dict[str, Any]], today: date) -> str:
    c = counts(report)
    return f"Stock-Vis 하네스 건강 — {today.month}/{today.day} (❌{c[ERROR]} ⚠️{c[WARN]})"


def render_body(report: list[dict[str, Any]], groups: dict[str, Any], today: date) -> str:
    c = counts(report)
    lines: list[str] = []

    # ── 3줄 요약 ──
    lines.append(f"점검 {len(report)}건 — ✅{c[OK]} ⚠️{c[WARN]} ❌{c[ERROR]}")
    if is_baseline(groups):
        lines.append("첫 수집이라 전일 비교가 없습니다(다음 실행부터 변화만 보고).")
        lines.append(f"현재 이상 {len(groups['baseline'])}건.")
    else:
        lines.append(
            f"변화: 신규 {len(groups['new'])} · 재발 {len(groups['recurring'])} · 해소 {len(groups['resolved'])}"
        )
        if c[ERROR] == 0 and not groups["new"]:
            lines.append("차단성 이상은 없습니다.")
        else:
            lines.append("아래 '변화'를 먼저 확인하세요.")

    # ── 변화 ──
    lines.append("")
    lines.append("── 변화 ──")
    if is_baseline(groups):
        for ch in groups["baseline"]:
            lines.append(f"  {STATUS_MARK.get(ch.status, '?')} {ch.name} — {ch.detail}")
        if not groups["baseline"]:
            lines.append("  (이상 없음)")
    else:
        for ch in groups["new"]:
            lines.append(f"  [신규] {STATUS_MARK.get(ch.status, '?')} {ch.name} — {ch.detail}")
        for ch in groups["recurring"]:
            lines.append(f"  [재발 {ch.streak}일째] {STATUS_MARK.get(ch.status, '?')} {ch.name} — {ch.detail}")
        for ch in groups["resolved"]:
            lines.append(f"  [해소] {ch.name}")
        if not (groups["new"] or groups["recurring"] or groups["resolved"]):
            lines.append("  (전일과 동일)")

    # ── 전체 표 ──
    lines.append("")
    lines.append("── 전체 ──")
    for check in report:
        mark = STATUS_MARK.get(int(check.get("status", OK)), "?")
        lines.append(f"  {mark} {check.get('name', '')} — {check.get('detail', '')}")

    lines.append("")
    lines.append(FOOTER)
    return "\n".join(lines)


def build_mail(out_dir: Path | None = None) -> tuple[str, str, dict[str, Any], bool, str]:
    history = load_reports(out_dir or OUT_DIR)
    if not history:
        raise SystemExit("리포트가 없습니다 — health_check.py --json 을 먼저 실행하세요.")
    today, report = history[-1]
    groups = classify(history)
    ok, reason = should_send(groups, report, today)
    return render_subject(report, today), render_body(report, groups, today), groups, ok, reason


def main() -> int:
    parser = argparse.ArgumentParser(description="하네스 건강 diff + 메일")
    parser.add_argument("--out-dir", help="리포트 디렉터리")
    parser.add_argument("--to", default=MAIL_TO, help="수신자")
    parser.add_argument("--dry-run", action="store_true", help="발송 없이 본문만 출력")
    parser.add_argument("--force-send", action="store_true", help="조용한 날에도 발송")
    args = parser.parse_args()

    subject, body, _, should, reason = build_mail(Path(args.out_dir) if args.out_dir else None)

    if args.dry_run:
        print(f"[발송 판정] {should} — {reason}")
        print(subject)
        print("-" * 72)
        print(body)
        return 0

    if not should and not args.force_send:
        print(f"[skip] {reason}")
        return 0

    from ..common.mail import send

    send(subject, body, args.to)
    print(f"[sent] {reason} → {args.to}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
