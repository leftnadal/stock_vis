"""health_check PROGRESS 신선도(시간기반, B2) 자기검증 — DECISIONS D-OPS-HCHECK-B2.

순수함수 `is_progress_stale`의 2방향 회귀(이 세션의 행위 변경 근거):
  - 방향 1 (fast-main 오발 0): PROGRESS가 최근이면 main이 몇 커밋 앞서 있어도 PASS.
    해시 대조를 안 하므로 fast-main/동시쓰기와 무관 — 구설계의 self-ref 오발 소멸 입증.
  - 방향 2 (진짜 방치 차단): 임계 초과 방치는 여전히 blocking — detection 보존 입증.
  - 경계값(정확히 M, M 직후) — strict '>' 반경계 확인.
"""

from scripts.health_check import PROGRESS_STALE_THRESHOLD_H, is_progress_stale

HOUR = 3600
NOW = 1_782_984_843  # 고정 기준 epoch(테스트 결정성 — 벽시계 미의존)


def test_fresh_progress_not_stale_regardless_of_main_advance():
    # 1h 전 갱신 → 신선. 해시 대조가 없으므로 main이 여러 커밋 앞서도 PASS(오발 0).
    assert is_progress_stale(NOW - 1 * HOUR, NOW, 72.0) is False


def test_abandoned_progress_is_stale():
    # 96h(>72h) 방치 → blocking 유지(진짜 방치 차단 보존).
    assert is_progress_stale(NOW - 96 * HOUR, NOW, 72.0) is True


def test_boundary_exactly_at_threshold_not_stale():
    # 정확히 72h → strict '>' 이므로 아직 stale 아님.
    assert is_progress_stale(NOW - 72 * HOUR, NOW, 72.0) is False


def test_boundary_just_over_threshold_is_stale():
    assert is_progress_stale(NOW - 72 * HOUR - 1, NOW, 72.0) is True


def test_default_threshold_is_72h():
    # 확정 M=72h(STEP 0 실측: 활성 max gap ~22.6h + 주말 마진) 회귀 잠금.
    assert PROGRESS_STALE_THRESHOLD_H == 72.0
