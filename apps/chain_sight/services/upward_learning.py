"""
RelationConfidence 상향 학습 루프 — 전이 로직 (D1).

설계: docs/features/chain-sight/relation_confidence_upward_loop.md
철학: B(비대칭 보수 — 이중 임계 + streak) + C(Tier-1 fast-path 1단계).

임계 상수는 하향(`relation_tasks.py:406 check_stale_and_decay`)이 하드코딩(90/60/30일)인
관례와 동일하게 **모듈 상수**로 둔다(신규 로더 만들지 않음 — 설계 §7). 값 근거는 정책표
`docs/chain_sight/update_v2/RELATION_CONFIDENCE.md`(truth_score confirmed 85·probable 60·weak 35).
D2 튜닝 게이트에서 실데이터로 재조정한다.
"""

from django.utils import timezone

# 강도 사다리 (hidden < weak < probable < confirmed). stale = confirmed cold(측면).
LADDER = ["hidden", "weak", "probable", "confirmed"]

# 임계 (정책표 근거 — probable 대표값 60. 상향 = 하향 + margin의 anti-whipsaw 이중 임계).
UPWARD_THRESHOLD = 60   # score([0,100]) ≥ 이 값이어야 상향 후보
STREAK_MIN = 3          # 연속 재확인 ≥ 이 틱(B 보수 — 하루살이 신호 차단)

# T-3b ⓓ-2 B-2: 구 seed(≥85→confirmed) 규칙을 엔진으로 이관 — score≥이 값이면 confirmed 직행.
# 상수 단일 출처: seed(services/sec_pipeline/tasks.py 신규 pair 초기값)는 이 상수를 import(중복 정의 금지).
#
# status 권위 도메인 분할(B-0 감사 확정 — 제4 기록자 update_relation_confidence 도메인 승인):
#   - 비-market(truth) status 권위 = 이 엔진(상향: highscore/fast-path/streak 3경로)
#                                    + decay(하향 전담, relation_tasks.check_stale_and_decay).
#     seed(sec_pipeline)는 기존 pair status 무기록 — flap 소멸.
#   - market status 관할 = update_relation_confidence 베이스라인(매 틱 직접 재산정,
#     upward 제외 대상 — 이중관리 방지). 본 엔진 밖(비-market만 처리).
HIGHSCORE_THRESHOLD = 85


def upgrade_one_step(status: str) -> str:
    """사다리 1칸 상향. stale→probable(재획득 특례), confirmed 상한."""
    if status == "stale":
        return "probable"  # confirmed 직행 금지 (B)
    if status in LADDER:
        i = LADDER.index(status)
        return LADDER[min(i + 1, len(LADDER) - 1)]
    return status


def recompute_truth_score(pair, trajectory=None) -> float:
    """
    정책표 기반 truth_score 재계산 (D1 최소 — 기존 값 유지 폴백).
    D2에서 궤적(trajectory) 반영 정교화. 현재는 pair.truth_score 폴백.
    """
    return float(getattr(pair, "truth_score", 0) or 0)


def is_tier1_authoritative(evidence_this_tick) -> bool:
    """Tier-1(API 직접: FMP/Finnhub/SEC) 권위 증거인가. 정책표 Evidence Tier 1."""
    if not evidence_this_tick:
        return False
    tier = None
    if isinstance(evidence_this_tick, dict):
        tier = evidence_this_tick.get("tier") or evidence_this_tick.get("evidence_tier_best")
    else:
        tier = getattr(evidence_this_tick, "evidence_tier_best", None)
    return tier == 1


def _upgrade(pair, now):
    new = upgrade_one_step(pair.relation_status)
    if new != pair.relation_status:
        pair.relation_status = new
        pair.last_upgraded_at = now


def apply_upward_learning(pair, evidence_this_tick, trajectory=None, *,
                          score=None, is_tier1=None, now=None):
    """
    증거로 재확인된 pair를 위로 되돌림 (1단계/틱, highscore는 confirmed 직행).
    충돌 배타: 증거無 → no-op(하향 경로가 처리). 증거有 → 상향 평가.
    score/is_tier1은 미지정 시 내부 계산, 지정 시 사용(테스트 주입).

    T-3b 반환 변경: 승급 경로 문자열('highscore'|'fastpath'|'streak') 또는 None(무승급).
      (구 bool 반환의 진리값 호환 — 호출부 `if did:` 그대로 동작. 경로 구분은 로그 3튜플용.)

    T-3b ⓔ 멱등 상태 기반화:
      - 이미 confirmed면 상한 — 모든 경로 skip(no-op, save도 태스크에서 skip).
      - fastpath_triggered_at은 최초 1회만 기록(기존 값 보존 — 오상향 witness 불변).
      - last_upgraded_at은 실제 상태 전이 시에만 갱신(_upgrade가 보장).
    """
    if not evidence_this_tick:
        return None  # 하향 경로가 처리 — 이 함수는 no-op
    if pair.relation_status == "confirmed":
        return None  # ⓔ 상한 도달 — 재승급 churn 차단 (last_computed_at도 불변, 태스크가 skip)
    now = now or timezone.now()
    if score is None:
        score = recompute_truth_score(pair, trajectory)
    if is_tier1 is None:
        is_tier1 = is_tier1_authoritative(evidence_this_tick)

    path = None
    if score >= HIGHSCORE_THRESHOLD:
        # ⓓ-2 B-2 highscore: 구 seed ≥85 규칙 이관 — confirmed 직행(권위 즉시 반영).
        before = pair.relation_status
        pair.relation_status = "confirmed"
        if pair.relation_status != before:
            pair.last_upgraded_at = now
            path = "highscore"
    elif is_tier1 and score >= UPWARD_THRESHOLD:
        # C fast-path: streak 면제, 최대 1단계
        before = pair.relation_status
        _upgrade(pair, now)
        if pair.relation_status != before:
            if pair.fastpath_triggered_at is None:  # ⓔ 최초 1회만 기록(보존)
                pair.fastpath_triggered_at = now
            path = "fastpath"
    else:
        # B 일반: streak 누적 → 이중 임계 충족 시 1단계
        pair.evidence_streak += 1
        if score >= UPWARD_THRESHOLD and pair.evidence_streak >= STREAK_MIN:
            before = pair.relation_status
            _upgrade(pair, now)
            if pair.relation_status != before:
                pair.evidence_streak = 0  # 승급 후 리셋
                path = "streak"

    pair.last_computed_at = now
    return path
