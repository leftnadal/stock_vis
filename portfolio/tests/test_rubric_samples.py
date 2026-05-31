"""Rubric §B.1 sample 5건 + Slice 8 10단계 척도 정합성 회귀."""

from pathlib import Path

RUBRIC_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "portfolio"
    / "coach"
    / "manual_eval_rubric.md"
)


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


# ============================================================
# Slice 8 Part 1 Step 0-3 #26 — 10단계 척도 + 분포 폭 게이트 명문화 (4건)
# ============================================================


def test_rubric_slice8_10_scale_present():
    """§F. Slice 8 10단계 척도 + §F.1 Naturalness + §F.2 Insight 명시."""
    content = RUBRIC_PATH.read_text(encoding="utf-8")
    assert "Slice 8 10단계 척도" in content
    assert "§F.1 Naturalness" in content
    assert "§F.2 Insight" in content
    # 10단계 점수 anchor 모두 존재
    for score in range(1, 11):
        assert f"**{score}**" in content, f"10단계 {score}점 anchor 누락"


def test_rubric_slice8_polar_anchors_present():
    """§F.3 양극단 앵커: 1점 (S7 75% 구체성 부족 패턴) + 10점 (raw + 시계열 + 동종 비교)."""
    content = RUBRIC_PATH.read_text(encoding="utf-8")
    assert "§F.3 양극단 앵커" in content
    assert "1점 앵커" in content
    assert "10점 앵커" in content
    # 10점 anchor 내용 검증 — raw + 시계열 변화율 + 동종 비교
    assert "4분기 전" in content or "4Q" in content  # 시계열 변화율
    assert "P75" in content or "P50" in content  # 동종 비교


def test_rubric_5_to_10_mapping_table_present():
    """§G. 5단계 → 10단계 매핑표 + 재평가 금지 노트."""
    content = RUBRIC_PATH.read_text(encoding="utf-8")
    assert "5단계 → 10단계 매핑표" in content
    # 매핑표 entries
    for v_10 in ("1-2", "3-4", "5-6", "7-8", "9-10"):
        assert v_10 in content, f"매핑 → {v_10} 누락"
    # 재평가 금지
    assert "재평가 금지" in content


def test_rubric_distribution_width_gate_rule_codified():
    """§C.7 분포 폭 자동 게이트 룰 명문화 (Slice 8 Step 0-3 KPI)."""
    content = RUBRIC_PATH.read_text(encoding="utf-8")
    # 분포 폭 자동 게이트 명시
    assert "분포 폭" in content
    assert "≥ 3.0" in content
    # 자연 close / keep_open 룰
    assert "자연 close" in content
    assert "keep_open" in content
    assert "Slice 9" in content  # 재후보 등록
