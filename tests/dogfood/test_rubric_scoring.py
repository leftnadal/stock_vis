"""AGENT-S2 — 루브릭 채점 유닛 테스트.

핵심 계약: **화면에서 추출한 텍스트만** 근거가 된다. 인용이 없거나 화면에 없는
문구를 인용하면 그 채점은 무효다(모델 사전지식으로 화면을 평가하는 것을 막는 장치).
"""

from __future__ import annotations

import json
from datetime import date

import pytest

from auto_agent_system.dogfood.report_mail import (
    load_rubric,
    render_rubric_section,
    render_subject,
)
from auto_agent_system.dogfood.score_rubric import (
    average,
    build_report,
    load_previous,
    parse_response,
    screen_texts,
    validate_scores,
)
from auto_agent_system.dogfood.targets import rubric_targets

SCREEN_TEXT = "오늘 시장은 상승 후반 경계 국면입니다. 데이터 기준일 2026-09-02."


@pytest.fixture
def first_target():
    targets = rubric_targets()
    assert targets, "루브릭 대상 화면이 0건 — 가이드 데이터 확인 필요"
    return targets[0]


def _rendered(target, text: str = SCREEN_TEXT, authenticated: bool = True) -> dict:
    return {
        "authenticated": authenticated,
        "screens": [
            {
                "id": target.id,
                "route": target.route,
                "ok": True,
                "regions": [{"anchor": "a1", "found": True, "text": text}],
                "fallback_text": "",
            }
        ],
    }


# ── 대상 선정 ────────────────────────────────────────────────────────────────


def test_rubric_targets_are_confirmed_with_core_question():
    targets = rubric_targets()
    assert targets
    assert all(t.review_status == "confirmed" for t in targets)
    assert all(t.core_question for t in targets)
    assert all(t.learnings for t in targets)


def test_rubric_targets_sorted_by_flow_stage():
    stages = [t.flow_stage for t in rubric_targets()]
    assert stages == sorted(stages)


# ── 응답 파싱 ────────────────────────────────────────────────────────────────


def test_parse_plain_json():
    assert parse_response('{"scores": [], "wish": ""}')["scores"] == []


def test_parse_code_fenced_json():
    raw = 'here you go\n```json\n{"scores": [], "wish": "x"}\n```\n감사합니다'
    assert parse_response(raw)["wish"] == "x"


def test_parse_json_with_surrounding_prose():
    raw = '설명입니다.\n{"scores": [], "wish": ""}\n끝.'
    assert parse_response(raw)["scores"] == []


def test_parse_raises_without_json():
    with pytest.raises(ValueError):
        parse_response("JSON이 없는 응답입니다")


# ── 인용 검증 (핵심 계약) ────────────────────────────────────────────────────


def test_valid_quote_scores(first_target):
    texts = screen_texts(_rendered(first_target))
    data = {
        "scores": [
            {"id": first_target.id, "score": 4, "reason": "국면을 말해줍니다.", "quote": "상승 후반 경계 국면"}
        ]
    }
    rows = validate_scores(data, texts)
    assert rows[0]["score"] == 4 and rows[0]["invalid"] is None


def test_missing_quote_is_invalid(first_target):
    texts = screen_texts(_rendered(first_target))
    data = {"scores": [{"id": first_target.id, "score": 5, "reason": "좋습니다.", "quote": ""}]}
    rows = validate_scores(data, texts)
    assert rows[0]["score"] is None and rows[0]["invalid"] == "인용 없음"


def test_too_short_quote_is_invalid(first_target):
    """짧은 인용은 우연히 일치할 수 있어 무효로 다룬다."""
    texts = screen_texts(_rendered(first_target))
    data = {"scores": [{"id": first_target.id, "score": 5, "reason": "r", "quote": "오늘"}]}
    assert validate_scores(data, texts)[0]["invalid"] == "인용 없음"


def test_hallucinated_quote_is_invalid(first_target):
    """화면에 없는 문구를 인용하면 무효 — 사전지식 평가 차단 장치."""
    texts = screen_texts(_rendered(first_target))
    data = {
        "scores": [
            {"id": first_target.id, "score": 5, "reason": "r", "quote": "RSI 과매수 구간 진입"}
        ]
    }
    assert validate_scores(data, texts)[0]["invalid"] == "인용 불일치(화면에 없는 문구)"


def test_quote_matching_ignores_whitespace_and_smart_quotes(first_target):
    texts = screen_texts(_rendered(first_target))
    data = {
        "scores": [
            {"id": first_target.id, "score": 3, "reason": "r", "quote": "상승   후반 “경계” 국면".replace("“경계”", "경계")}
        ]
    }
    assert validate_scores(data, texts)[0]["invalid"] is None


def test_out_of_range_score_is_invalid(first_target):
    texts = screen_texts(_rendered(first_target))
    data = {
        "scores": [{"id": first_target.id, "score": 9, "reason": "r", "quote": "상승 후반 경계 국면"}]
    }
    assert validate_scores(data, texts)[0]["invalid"] == "점수 범위 밖"


def test_missing_screen_is_marked_unscored(first_target):
    texts = screen_texts(_rendered(first_target))
    rows = validate_scores({"scores": []}, texts)
    assert all(r["invalid"] == "미채점" for r in rows)


def test_all_targets_present_even_when_model_returns_subset(first_target):
    """전체 중단 금지 — 대상 화면 수만큼 행이 나온다."""
    texts = screen_texts(_rendered(first_target))
    data = {"scores": [{"id": first_target.id, "score": 3, "reason": "r", "quote": "상승 후반 경계 국면"}]}
    assert len(validate_scores(data, texts)) == len(rubric_targets())


# ── fallback_text 경로 ───────────────────────────────────────────────────────


def test_screen_texts_uses_fallback_when_no_regions(first_target):
    rendered = {
        "screens": [
            {"id": first_target.id, "regions": [], "fallback_text": "대체 본문 텍스트입니다"}
        ]
    }
    assert "대체 본문" in screen_texts(rendered)[first_target.id]


# ── 평균·diff ────────────────────────────────────────────────────────────────


def test_average_ignores_invalid():
    rows = [{"score": 4}, {"score": 2}, {"score": None}]
    assert average(rows) == 3.0


def test_average_none_when_all_invalid():
    assert average([{"score": None}]) is None


def test_load_previous_picks_latest_before_today(tmp_path):
    (tmp_path / "rubric_20260901.json").write_text(
        json.dumps({"scores": [{"id": "a", "score": 2}]}), encoding="utf-8"
    )
    (tmp_path / "rubric_20260830.json").write_text(
        json.dumps({"scores": [{"id": "a", "score": 5}]}), encoding="utf-8"
    )
    assert load_previous(tmp_path, date(2026, 9, 2)) == {"a": 2}


def test_load_previous_excludes_today(tmp_path):
    (tmp_path / "rubric_20260902.json").write_text(
        json.dumps({"scores": [{"id": "a", "score": 2}]}), encoding="utf-8"
    )
    assert load_previous(tmp_path, date(2026, 9, 2)) == {}


def test_build_report_computes_delta(tmp_path, first_target):
    (tmp_path / "rubric_20260901.json").write_text(
        json.dumps({"scores": [{"id": first_target.id, "score": 2}]}), encoding="utf-8"
    )
    data = {
        "scores": [{"id": first_target.id, "score": 4, "reason": "r", "quote": "상승 후반 경계 국면"}],
        "wish": "",
    }
    report = build_report(_rendered(first_target), data, tmp_path, date(2026, 9, 2))
    row = next(r for r in report["scores"] if r["id"] == first_target.id)
    assert row["prev_score"] == 2 and row["delta"] == 2


# ── 메일 섹션 ────────────────────────────────────────────────────────────────


def test_mail_section_absent_rubric_says_unmeasurable():
    lines = render_rubric_section(None, "렌더 실패")
    assert any("측정 불가(렌더 실패)" in x for x in lines)


def test_mail_section_shows_scores_and_worst_quote():
    rubric = {
        "authenticated": True,
        "average": 3.0,
        "invalid_count": 0,
        "wish": "신선도 배지를 위로",
        "scores": [
            {"id": "a", "title": "대시보드", "score": 4, "delta": 1, "reason": "r1", "quote": "q1"},
            {"id": "b", "title": "모니터", "score": 2, "delta": -1, "reason": "낮은 이유", "quote": "화면 인용문"},
        ],
    }
    body = "\n".join(render_rubric_section(rubric))
    assert "대시보드 — 4/5 ▲1" in body
    assert "모니터 — 2/5 ▼1" in body
    assert "최저 화면: 모니터 (2/5)" in body
    assert "화면 인용문" in body
    assert "있으면 좋겠다: 신선도 배지를 위로" in body


def test_mail_section_marks_unscored_rows():
    rubric = {"authenticated": True, "scores": [{"id": "a", "title": "X", "invalid": "인용 없음"}]}
    body = "\n".join(render_rubric_section(rubric))
    assert "채점 불가(인용 없음)" in body


def test_mail_section_warns_when_unauthenticated():
    rubric = {"authenticated": False, "scores": []}
    assert any("미인증" in x for x in render_rubric_section(rubric))


def test_subject_includes_average_when_present():
    report = {"summary": {"passed": 8, "total": 9}, "run_date": "2026-09-02"}
    assert "루브릭 평균 3.4/5" in render_subject(report, {"average": 3.4})


def test_subject_unchanged_without_rubric():
    """행위보존 — 2단계 산출물이 없으면 기존 제목 그대로."""
    report = {"summary": {"passed": 8, "total": 9}, "run_date": "2026-09-02"}
    assert render_subject(report) == "Stock-Vis 야간 점검 — 9/2 (정량 8/9 통과)"


def test_load_rubric_missing_returns_none(tmp_path):
    assert load_rubric(tmp_path, date(2026, 9, 2)) is None


def test_load_rubric_corrupt_returns_none(tmp_path):
    (tmp_path / "rubric_20260902.json").write_text("{ broken", encoding="utf-8")
    assert load_rubric(tmp_path, date(2026, 9, 2)) is None
