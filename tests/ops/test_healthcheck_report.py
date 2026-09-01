"""OPS-HEALTHCHECK-NIGHTLY-WIRE — 야간 하네스 건강 보고 유닛 테스트.

diff 3분류(신규/재발 N일째/해소) · 조용한 날 미발송 · 월요일 확인 발송 · JSON 스키마.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from auto_agent_system.healthcheck.report_health_mail import (
    ERROR,
    OK,
    WARN,
    as_map,
    build_mail,
    classify,
    counts,
    is_baseline,
    load_reports,
    render_body,
    render_subject,
    should_send,
)


def _check(name: str, status: int = OK, detail: str = "") -> dict:
    return {
        "name": name,
        "status": status,
        "status_label": {OK: "✅ OK", WARN: "⚠  WARN", ERROR: "❌ ERROR"}[status],
        "detail": detail or f"{name} 상세",
        "evidence": [],
    }


def _write(out: Path, day: str, report: list[dict]) -> None:
    (out / f"health_{day}.json").write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")


MON = date(2026, 8, 31)  # 월요일
TUE = date(2026, 9, 1)  # 화요일


def test_weekday_fixture_sanity():
    assert MON.weekday() == 0 and TUE.weekday() == 1


# ── 스키마 / 적재 ────────────────────────────────────────────────────────────


def test_load_reports_sorted_and_parsed(tmp_path):
    _write(tmp_path, "20260901", [_check("A")])
    _write(tmp_path, "20260831", [_check("A"), _check("B")])
    rows = load_reports(tmp_path)
    assert [d for d, _ in rows] == [date(2026, 8, 31), date(2026, 9, 1)]
    assert len(rows[0][1]) == 2


def test_load_reports_skips_corrupt_and_foreign(tmp_path):
    _write(tmp_path, "20260901", [_check("A")])
    (tmp_path / "health_20260902.json").write_text("{ not json", encoding="utf-8")
    (tmp_path / "quant_20260901.json").write_text("[]", encoding="utf-8")  # 남의 파일
    (tmp_path / "health_bad.json").write_text("[]", encoding="utf-8")  # 이름 규칙 위반
    rows = load_reports(tmp_path)
    assert len(rows) == 1


def test_load_reports_rejects_non_list_payload(tmp_path):
    """health_check --json 은 리스트를 낸다. dict면 스키마 위반이라 무시."""
    (tmp_path / "health_20260901.json").write_text('{"checks": {}}', encoding="utf-8")
    assert load_reports(tmp_path) == []


def test_as_map_and_counts():
    report = [_check("A"), _check("B", WARN), _check("C", ERROR)]
    assert set(as_map(report)) == {"A", "B", "C"}
    assert counts(report) == {OK: 1, WARN: 1, ERROR: 1}


# ── diff 3분류 ───────────────────────────────────────────────────────────────


def test_classify_baseline_on_first_report():
    groups = classify([(TUE, [_check("A", ERROR), _check("B")])])
    assert is_baseline(groups)
    assert [c.name for c in groups["baseline"]] == ["A"]


def test_classify_new():
    history = [(MON, [_check("A"), _check("B")]), (TUE, [_check("A", ERROR), _check("B")])]
    groups = classify(history)
    assert [c.name for c in groups["new"]] == ["A"]
    assert groups["recurring"] == [] and groups["resolved"] == []


def test_classify_resolved():
    history = [(MON, [_check("A", ERROR)]), (TUE, [_check("A")])]
    groups = classify(history)
    assert [c.name for c in groups["resolved"]] == ["A"]


def test_classify_recurring_counts_streak():
    history = [
        (date(2026, 8, 29), [_check("A", ERROR)]),
        (date(2026, 8, 30), [_check("A", ERROR)]),
        (MON, [_check("A", ERROR)]),
        (TUE, [_check("A", ERROR)]),
    ]
    groups = classify(history)
    assert len(groups["recurring"]) == 1
    assert groups["recurring"][0].streak == 4


def test_classify_streak_breaks_on_recovery():
    history = [
        (date(2026, 8, 29), [_check("A", ERROR)]),
        (date(2026, 8, 30), [_check("A")]),  # 회복
        (MON, [_check("A", ERROR)]),
        (TUE, [_check("A", ERROR)]),
    ]
    assert classify(history)["recurring"][0].streak == 2


def test_classify_warn_counts_as_bad():
    """WARN도 '이상'으로 다룬다(ERROR만 보면 드리프트를 놓친다)."""
    history = [(MON, [_check("A")]), (TUE, [_check("A", WARN)])]
    assert [c.name for c in classify(history)["new"]] == ["A"]


def test_classify_handles_added_and_removed_checks():
    """점검 항목이 늘거나 준 날에도 터지지 않는다."""
    history = [(MON, [_check("A", ERROR)]), (TUE, [_check("B", ERROR)])]
    groups = classify(history)
    assert [c.name for c in groups["new"]] == ["B"]
    assert groups["resolved"] == []  # A는 사라진 것이지 해소가 아니다


def test_classify_empty_history():
    groups = classify([])
    assert is_baseline(groups) and groups["baseline"] == []


# ── 발송 규칙 ────────────────────────────────────────────────────────────────


def test_send_on_baseline():
    report = [_check("A")]
    ok, reason = should_send(classify([(TUE, report)]), report, TUE)
    assert ok and "baseline" in reason


def test_send_when_error_present():
    report = [_check("A", ERROR)]
    history = [(MON, [_check("A", ERROR)]), (TUE, report)]
    ok, reason = should_send(classify(history), report, TUE)
    assert ok and "ERROR" in reason


def test_send_on_new_issue():
    report = [_check("A", WARN)]
    history = [(MON, [_check("A")]), (TUE, report)]
    ok, reason = should_send(classify(history), report, TUE)
    assert ok and "신규" in reason


def test_send_on_resolved():
    report = [_check("A")]
    history = [(MON, [_check("A", WARN)]), (TUE, report)]
    ok, reason = should_send(classify(history), report, TUE)
    assert ok and "해소" in reason


def test_skip_on_quiet_day():
    """변화 0 · ERROR 0 인 평일은 보내지 않는다 — 노이즈 방지."""
    report = [_check("A"), _check("B", WARN)]
    history = [(date(2026, 8, 30), report), (TUE, report)]
    ok, reason = should_send(classify(history), report, TUE)
    assert not ok and "생략" in reason


def test_send_on_monday_even_when_quiet():
    """조용해도 월요일엔 보낸다 — 잡이 죽은 것과 조용한 것을 구별하려고."""
    report = [_check("A")]
    history = [(date(2026, 8, 30), report), (MON, report)]
    ok, reason = should_send(classify(history), report, MON)
    assert ok and "주간" in reason


def test_quiet_day_with_persistent_warn_still_skips():
    """같은 WARN이 계속되는 것만으로는 발송하지 않는다(재발 WARN은 조용히 누적)."""
    report = [_check("A", WARN)]
    history = [(date(2026, 8, 30), report), (TUE, report)]
    ok, _ = should_send(classify(history), report, TUE)
    assert not ok


# ── 렌더 ─────────────────────────────────────────────────────────────────────


def test_subject_shows_counts():
    subject = render_subject([_check("A", ERROR), _check("B", WARN), _check("C")], TUE)
    assert "9/1" in subject and "❌1" in subject and "⚠️1" in subject


def test_body_has_three_sections_and_streak():
    history = [
        (date(2026, 8, 30), [_check("A", ERROR), _check("B")]),
        (MON, [_check("A", ERROR), _check("B")]),
        (TUE, [_check("A", ERROR), _check("B", WARN)]),
    ]
    body = render_body(history[-1][1], classify(history), TUE)
    assert "── 변화 ──" in body and "── 전체 ──" in body
    assert "[재발 3일째]" in body
    assert "[신규]" in body


def test_body_baseline_wording():
    report = [_check("A", ERROR)]
    body = render_body(report, classify([(TUE, report)]), TUE)
    assert "첫 수집" in body


def test_body_quiet_day_says_identical():
    report = [_check("A")]
    history = [(MON, report), (TUE, report)]
    body = render_body(report, classify(history), TUE)
    assert "(전일과 동일)" in body


# ── build_mail 통합 ──────────────────────────────────────────────────────────


def test_build_mail_end_to_end(tmp_path):
    _write(tmp_path, "20260831", [_check("A", ERROR), _check("B")])
    _write(tmp_path, "20260901", [_check("A"), _check("B")])
    subject, body, groups, should, reason = build_mail(tmp_path)
    assert "❌0" in subject
    assert [c.name for c in groups["resolved"]] == ["A"]
    assert should and "해소" in reason
    assert "[해소] A" in body


def test_build_mail_raises_without_reports(tmp_path):
    with pytest.raises(SystemExit):
        build_mail(tmp_path)
