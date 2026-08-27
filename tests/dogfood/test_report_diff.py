"""AGENT-S1 — 전일 대비 diff 3분류(신규 / 재발 N일째 / 해소) + 본문 렌더."""
import json
from datetime import date
from pathlib import Path

from auto_agent_system.dogfood import report_mail as rm


def _report(run_date: str, checks: dict[str, str], session: str = "2026-08-26") -> dict:
    """checks = {키: status}."""
    built = {
        k: {"status": v, "value": None, "threshold": None, "note": f"{k} 메모"}
        for k, v in checks.items()
    }
    return {
        "schema_version": 1,
        "run_date": run_date,
        "generated_at": f"{run_date}T20:20:00+00:00",
        "session_date": session,
        "market": {"run_date_is_trading_day": True, "run_date_holiday": None},
        "auth_mode": "token",
        "summary": {
            "total": len(built),
            "passed": sum(1 for c in built.values() if c["status"] == "ok"),
            "warn": sum(1 for c in built.values() if c["status"] == "warn"),
            "failed": sum(1 for c in built.values() if c["status"] == "fail"),
        },
        "checks": built,
    }


def _write(tmp_path: Path, report: dict) -> None:
    stamp = report["run_date"].replace("-", "")
    (tmp_path / f"quant_{stamp}.json").write_text(json.dumps(report), encoding="utf-8")


def test_first_run_is_baseline_not_all_new(tmp_path):
    """첫날은 비교 대상이 없다 — 전 항목을 '신규'로 쏟아내면 안 된다."""
    _write(tmp_path, _report("2026-08-27", {"a": "ok", "b": "fail"}))
    history = rm.load_reports(tmp_path)
    groups = rm.classify(history)

    assert rm.is_baseline(groups) is True
    assert [c.key for c in groups["baseline"]] == ["b"]
    assert groups["new"] == [] and groups["recurring"] == [] and groups["resolved"] == []


def test_new_recurring_resolved_three_way_split(tmp_path):
    _write(tmp_path, _report("2026-08-26", {"a": "ok", "b": "fail", "c": "fail"}))
    _write(tmp_path, _report("2026-08-27", {"a": "fail", "b": "fail", "c": "ok"}))
    groups = rm.classify(rm.load_reports(tmp_path))

    assert [c.key for c in groups["new"]] == ["a"]        # ok → fail
    assert [c.key for c in groups["recurring"]] == ["b"]  # fail → fail
    assert [c.key for c in groups["resolved"]] == ["c"]   # fail → ok
    assert rm.is_baseline(groups) is False


def test_recurring_streak_counts_consecutive_days(tmp_path):
    for day in ("2026-08-24", "2026-08-25", "2026-08-26", "2026-08-27"):
        _write(tmp_path, _report(day, {"b": "fail"}))
    groups = rm.classify(rm.load_reports(tmp_path))
    assert groups["recurring"][0].streak == 4


def test_streak_resets_after_a_good_day(tmp_path):
    _write(tmp_path, _report("2026-08-24", {"b": "fail"}))
    _write(tmp_path, _report("2026-08-25", {"b": "ok"}))
    _write(tmp_path, _report("2026-08-26", {"b": "fail"}))
    _write(tmp_path, _report("2026-08-27", {"b": "fail"}))
    groups = rm.classify(rm.load_reports(tmp_path))
    assert groups["recurring"][0].streak == 2


def test_warn_counts_as_abnormal(tmp_path):
    """warn도 '정상 아님' — 조용히 통과시키면 경고가 무의미해진다."""
    _write(tmp_path, _report("2026-08-26", {"a": "ok"}))
    _write(tmp_path, _report("2026-08-27", {"a": "warn"}))
    groups = rm.classify(rm.load_reports(tmp_path))
    assert [c.key for c in groups["new"]] == ["a"]


def test_key_absent_yesterday_is_new_not_recurring(tmp_path):
    _write(tmp_path, _report("2026-08-26", {"a": "ok"}))
    _write(tmp_path, _report("2026-08-27", {"a": "ok", "z": "fail"}))
    groups = rm.classify(rm.load_reports(tmp_path))
    assert [c.key for c in groups["new"]] == ["z"]
    assert groups["recurring"] == []


def test_no_change_day_body_is_short(tmp_path):
    """변화 0건이면 상세 표 없이 요약으로 끝난다(길면 안 읽힌다)."""
    _write(tmp_path, _report("2026-08-26", {"a": "ok"}))
    _write(tmp_path, _report("2026-08-27", {"a": "ok"}))
    history = rm.load_reports(tmp_path)
    body = rm.render_body(history[-1][1], rm.classify(history))

    assert "전일 대비 변화 없음." in body
    assert "■ 전체 상세" not in body
    assert body.rstrip().endswith(rm.FOOTER)


def test_body_lists_each_group_with_streak(tmp_path):
    _write(tmp_path, _report("2026-08-26", {"a": "ok", "b": "fail", "c": "fail"}))
    _write(tmp_path, _report("2026-08-27", {"a": "fail", "b": "fail", "c": "ok"}))
    history = rm.load_reports(tmp_path)
    body = rm.render_body(history[-1][1], rm.classify(history))

    assert "■ 신규" in body and "■ 재발" in body and "■ 해소" in body
    assert "2일째" in body
    assert "■ 전체 상세" in body


def test_subject_format(tmp_path):
    report = _report("2026-08-27", {"a": "ok", "b": "fail"})
    assert rm.render_subject(report) == "Stock-Vis 야간 점검 — 8/27 (정량 1/2 통과)"


def test_holiday_is_stated_in_summary(tmp_path):
    report = _report("2026-08-27", {"a": "ok"})
    report["market"] = {"run_date_is_trading_day": False, "run_date_holiday": "Christmas Day"}
    body = rm.render_body(report, rm.classify([(date(2026, 8, 27), report)]))
    assert "휴장(Christmas Day)" in body


def test_unauthenticated_mode_is_disclosed(tmp_path):
    report = _report("2026-08-27", {"a": "ok"})
    report["auth_mode"] = "unauthenticated"
    body = rm.render_body(report, rm.classify([(date(2026, 8, 27), report)]))
    assert "무인증 모드" in body


def test_malformed_report_file_is_skipped(tmp_path):
    _write(tmp_path, _report("2026-08-26", {"a": "ok"}))
    (tmp_path / "quant_20260827.json").write_text("{ not json", encoding="utf-8")
    (tmp_path / "quant_notadate.json").write_text("{}", encoding="utf-8")
    history = rm.load_reports(tmp_path)
    assert [d.isoformat() for d, _ in history] == ["2026-08-26"]
