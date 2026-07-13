"""
RelationConfidence 상향 학습 루프 D1 — 전이 함수 단위 테스트 (합성, 실데이터 불요).

설계: docs/features/chain-sight/relation_confidence_upward_loop.md
철학: B(비대칭 보수, 이중임계+streak) + C(Tier-1 fast-path 1단계).
"""

import pytest

from apps.chain_sight.services.upward_learning import (
    STREAK_MIN,
    UPWARD_THRESHOLD,
    apply_upward_learning,
    upgrade_one_step,
)


def _pair(status="hidden", streak=0):
    """unsaved RelationConfidence 인스턴스 (순수 전이 로직 테스트 — DB 불요)."""
    from apps.chain_sight.models import RelationConfidence

    return RelationConfidence(
        symbol_a="AAA", symbol_b="BBB", relation_type="SUPPLIES_TO",
        relation_category="truth", relation_status=status, evidence_streak=streak,
    )


class TestUpgradeOneStep:
    """사다리 순수함수: hidden<weak<probable<confirmed, stale→probable, confirmed 상한."""

    @pytest.mark.parametrize("cur,nxt", [
        ("hidden", "weak"),
        ("weak", "probable"),
        ("probable", "confirmed"),
        ("confirmed", "confirmed"),  # 상한
        ("stale", "probable"),       # 특례 재획득(confirmed 직행 금지)
    ])
    def test_ladder(self, cur, nxt):
        assert upgrade_one_step(cur) == nxt


class TestApplyUpwardLearning:
    def test_no_evidence_is_noop(self):
        """충돌 배타: 증거無 → no-op (하향 경로가 처리). streak/status 불변."""
        p = _pair("weak", streak=2)
        apply_upward_learning(p, evidence_this_tick=None, score=99, is_tier1=True)
        assert p.relation_status == "weak"
        assert p.evidence_streak == 2  # 리셋도 증가도 안 함(태스크 레벨에서 리셋)
        assert p.last_upgraded_at is None

    def test_general_upgrade_requires_streak_and_threshold(self):
        """일반(B): streak≥MIN + score≥임계에서 1단계 승급 + streak 리셋."""
        p = _pair("hidden", streak=STREAK_MIN - 1)
        # 이번 틱으로 streak가 MIN 도달 + score 충족 → 승급
        apply_upward_learning(p, evidence_this_tick={"t": 1}, score=UPWARD_THRESHOLD, is_tier1=False)
        assert p.relation_status == "weak"
        assert p.evidence_streak == 0  # 승급 후 리셋
        assert p.last_upgraded_at is not None

    def test_general_no_upgrade_below_streak(self):
        """streak 미달 → 승급 안 함, streak만 증가."""
        p = _pair("hidden", streak=0)
        apply_upward_learning(p, evidence_this_tick={"t": 1}, score=UPWARD_THRESHOLD, is_tier1=False)
        assert p.relation_status == "hidden"
        assert p.evidence_streak == 1

    def test_general_no_upgrade_below_threshold(self):
        """score 미달 → streak 충분해도 승급 안 함."""
        p = _pair("weak", streak=STREAK_MIN)
        apply_upward_learning(p, evidence_this_tick={"t": 1}, score=UPWARD_THRESHOLD - 1, is_tier1=False)
        assert p.relation_status == "weak"

    def test_stale_recovery_to_probable(self):
        """stale + 재확인 → probable (confirmed 직행 금지)."""
        p = _pair("stale", streak=STREAK_MIN)
        apply_upward_learning(p, evidence_this_tick={"t": 1}, score=UPWARD_THRESHOLD, is_tier1=False)
        assert p.relation_status == "probable"

    def test_fastpath_tier1_immediate_one_step(self):
        """C fast-path: Tier-1 + score≥임계 → streak 무관 1단계 즉시, fastpath 기록."""
        p = _pair("weak", streak=0)
        apply_upward_learning(p, evidence_this_tick={"t": 1}, score=UPWARD_THRESHOLD, is_tier1=True)
        assert p.relation_status == "probable"  # 1단계만
        assert p.fastpath_triggered_at is not None
        assert p.last_upgraded_at is not None

    def test_fastpath_below_threshold_no_upgrade(self):
        """Tier-1이라도 상향임계 미달이면 승급 안 함."""
        p = _pair("weak", streak=0)
        apply_upward_learning(p, evidence_this_tick={"t": 1}, score=UPWARD_THRESHOLD - 1, is_tier1=True)
        assert p.relation_status == "weak"
        assert p.fastpath_triggered_at is None

    def test_last_computed_at_always_set_when_evidence(self):
        """증거 있으면 last_computed_at 기록(드리프트 해소)."""
        p = _pair("hidden")
        apply_upward_learning(p, evidence_this_tick={"t": 1}, score=0, is_tier1=False)
        assert p.last_computed_at is not None

    # ── T-3b ⓓ-2 B-2 highscore 경로 + ⓔ 멱등 ──

    def test_highscore_jumps_directly_to_confirmed(self):
        """(g) score≥HIGHSCORE(85) → confirmed 직행(fast-path 1단계 아님). 구 seed 규칙 이관."""
        from apps.chain_sight.services.upward_learning import HIGHSCORE_THRESHOLD

        p = _pair("weak", streak=0)  # 사다리상 2칸 아래
        path = apply_upward_learning(
            p, evidence_this_tick={"t": 1}, score=HIGHSCORE_THRESHOLD, is_tier1=True)
        assert p.relation_status == "confirmed"  # 직행 (weak→probable 1단계가 아님)
        assert path == "highscore"
        assert p.last_upgraded_at is not None

    def test_confirmed_is_noop_ceiling(self):
        """(g/ⓔ) 이미 confirmed면 어떤 경로도 no-op(멱등 상한). last_computed_at도 불변."""
        p = _pair("confirmed")
        path = apply_upward_learning(
            p, evidence_this_tick={"t": 1}, score=99, is_tier1=True)
        assert path is None
        assert p.relation_status == "confirmed"
        assert p.last_computed_at is None  # skip = 마커도 안 씀 (태스크가 save skip)

    def test_return_is_path_string_or_none(self):
        """반환 규격: 승급 경로 문자열 또는 None(구 bool 진리값 호환)."""
        up = _pair("weak")
        assert apply_upward_learning(up, {"t": 1}, score=60, is_tier1=True) == "fastpath"
        noop = _pair("weak")
        assert apply_upward_learning(noop, evidence_this_tick=None, score=99) is None


@pytest.mark.django_db
class TestMigrationNondestructive:
    def test_additive_fields_default_and_existing_unchanged(self):
        """마이그레이션 0015 무손상: 신규 필드 default/null, 기존 필드 불변."""
        from apps.chain_sight.models import RelationConfidence

        r = RelationConfidence.objects.create(
            symbol_a="XX", symbol_b="YY", relation_type="PEER_OF",
            relation_category="truth", relation_status="confirmed", truth_score=85,
        )
        r.refresh_from_db()
        # 신규 additive 필드
        assert r.evidence_streak == 0
        assert r.last_upgraded_at is None
        assert r.last_downgraded_at is None
        assert r.last_computed_at is None
        assert r.fastpath_triggered_at is None
        # 기존 필드 불변
        assert r.relation_status == "confirmed"
        assert r.truth_score == 85


@pytest.mark.django_db
class TestTaskFlagOff:
    def test_task_is_noop_when_flag_off(self, settings):
        """flag-off → 상향 task는 no-op(실발화 없음). T-3b: prod .env=true라 앰비언트
        의존 제거 — 명시적 flag-off로 결정적 검증(모든 환경 GREEN)."""
        from apps.chain_sight.tasks.relation_tasks import apply_upward_learning_task

        settings.CHAINSIGHT_UPWARD_LEARNING_ENABLED = False
        result = apply_upward_learning_task.apply().result
        # D2 v5.1: 반환 규격에 evaluated/fastpath 추가(flag-off도 일관 shape).
        assert result == {"enabled": False, "evaluated": 0, "upgraded": 0, "fastpath": 0}
