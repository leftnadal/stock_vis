"""health_check TASKQUEUE 주장-vs-증거 advisory 가드 자기검증 (지시서⑫ C3).

순수함수 `_evaluate_claim_evidence` 2케이스:
  - 불일치(스테일): landed 증거(DECISIONS 종결 + 산출물 존재)가 있는데 TASKQUEUE 가
    landed 를 ack 하지 않으면 → 경고 목록에 잡힘(스테일 조기 감지).
  - 정합: TASKQUEUE 가 landed ack 토큰을 가지면 → 경고 0(오탐 없음, retained 이력 무해).
advisory-only: 이 가드는 WARN 만 내고 ERROR 를 내지 않는다(가드 함수 자체가 status 미결정,
_evaluate 는 목록만 반환) → pytest·health pass/fail baseline 무변경.
"""

from scripts.health_check import _CLAIM_EVIDENCE_RULES, _evaluate_claim_evidence

_RULES = [
    {
        "label": "DEMO-TRACK",
        "decisions_landed": "DEMO-TRACK 실행 완료",
        "artifact": "packages/demo/core.py",
        "ack_tokens": ["종결·LANDED"],
    }
]


def test_stale_claim_detected_when_landed_but_no_ack():
    """landed 증거 有 + TASKQUEUE ack 無 → 경고 1건(스테일 감지)."""
    tq = "| DEMO-TRACK | ... | DORMANT·미착수 |"  # ack 토큰 없음
    dec = "## DEMO-TRACK 실행 완료 (landed) ..."
    mism = _evaluate_claim_evidence(tq, dec, lambda a: True, _RULES)
    assert len(mism) == 1
    assert "DEMO-TRACK" in mism[0]


def test_consistent_when_taskqueue_acknowledges_landed():
    """landed 증거 有 + TASKQUEUE ack 有(종결·LANDED) → 경고 0(정합, 오탐 없음)."""
    tq = "## [종결·LANDED] DEMO-TRACK ... (이력 보존용 옛 DORMANT 문구도 남아있음)"
    dec = "## DEMO-TRACK 실행 완료 (landed) ..."
    mism = _evaluate_claim_evidence(tq, dec, lambda a: True, _RULES)
    assert mism == []


def test_no_evidence_no_warning():
    """landed 증거 없음(산출물 부재) → 검증 대상 아님, 경고 0."""
    tq = "| DEMO-TRACK | ... | DORMANT |"
    dec = "## DEMO-TRACK 실행 완료 ..."
    mism = _evaluate_claim_evidence(tq, dec, lambda a: False, _RULES)  # artifact 부재
    assert mism == []


def test_current_repo_boundary_llm_rule_is_consistent():
    """현행 repo 규칙(BOUNDARY-LLM)이 실제 파일과 정합(WARN 유발 안 함)."""
    from scripts.health_check import check_taskqueue_claim_vs_evidence, OK

    # C1 정합 후 실제 TASKQUEUE/DECISIONS/artifact 대조 → OK 여야 함.
    assert _CLAIM_EVIDENCE_RULES  # 규칙 최소 1건
    result = check_taskqueue_claim_vs_evidence()
    assert result.status == OK, f"advisory 가드가 현행 repo에서 WARN: {result.detail}"
