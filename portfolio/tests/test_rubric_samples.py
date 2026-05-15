"""Rubric §B.1 sample 5건 정합성 회귀 (Slice 7 Part 4 §2)."""

from pathlib import Path

RUBRIC_PATH = Path(__file__).resolve().parents[2] / "docs" / "portfolio" / "coach" / "manual_eval_rubric.md"


def test_rubric_has_5_samples():
    content = RUBRIC_PATH.read_text(encoding="utf-8")
    assert content.count("### Sample") >= 5


def test_rubric_sample_score_spectrum():
    """Sample 1~5가 1~5점 spectrum 다양성 cover (분포 폭 ≥ 3 확보)."""
    content = RUBRIC_PATH.read_text(encoding="utf-8")
    # 1점·5점 양극단 사용 확인 (분포 폭 KPI 충족 신호)
    assert "naturalness=1" in content
    assert "naturalness=5" in content
    assert "insight=1" in content
    assert "insight=5" in content
    # 중간 점수도 존재
    assert "naturalness=3" in content
    assert "insight=3" in content


def test_rubric_sample_rationale_present():
    """각 sample에 점수 사유 명시 (anchoring 학습용)."""
    content = RUBRIC_PATH.read_text(encoding="utf-8")
    assert "Naturalness 1점 사유" in content
    assert "Insight 1점 사유" in content
    assert "Naturalness 5점 사유" in content
    assert "Insight 5점 사유" in content
