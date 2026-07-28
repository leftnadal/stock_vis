"""health_check stale pending 'blocked(외부 의존)' 구분 자기검증 — D-HEALTH-BLOCKED-DISTINCTION.

순수함수 `evaluate_stale_pending(progress_text, tq_text, today)`의 결정성 검증:
  - blocked(dep=실존 ID)       → WARN 유지(승격 후에도 FAIL 아님)
  - blocked(dep=미실존 ID)     → 무효 → 일반 stale(승격 후 FAIL) + 무효 경고
  - 비-blocked 순수 stale       → 승격 전 WARN / 승격 후 FAIL
  - 현행 통과(신선/해소 부기)   → OK 무회귀
today를 주입해 승격 전/후를 결정적으로 검증(벽시계 미의존).
"""

from datetime import date

from scripts.health_check import (
    ERROR,
    OK,
    STALE_FAIL_PROMOTE_DATE,
    WARN,
    evaluate_stale_pending,
)

# 승격 전/후 기준일 (STALE_FAIL_PROMOTE_DATE = 2026-07-20)
BEFORE = date(2026, 7, 18)  # 승격 전
AFTER = date(2026, 7, 25)   # 승격 후

# 오래된(age > 3) pending 블록을 만들 기준 날짜 문자열
OLD = "2026-07-10"

TQ = """| ID | Task | Agent | Depends On | Status | 근거/비고 |
| TH-RUNTIME-DEPLOY | TH 트랙 정식 머지 | @infra | ... | blocked | ... |
"""


def _pending(extra: str = "") -> str:
    return f"> ⏸️ **{OLD} 어떤 배포 포기 (사유)**{extra}: 본문 ...\n"


def test_blocked_valid_dep_stays_warn_even_after_promote():
    # blocked(dep=실존) → 승격 후에도 WARN 유지(FAIL 제외)
    text = _pending(" — `blocked(dep=TH-RUNTIME-DEPLOY)`")
    r_before = evaluate_stale_pending(text, TQ, BEFORE)
    r_after = evaluate_stale_pending(text, TQ, AFTER)
    assert r_before.status == WARN
    assert r_after.status == WARN  # 승격 후에도 FAIL 아님
    assert any("blocked(dep=TH-RUNTIME-DEPLOY) 유효" in e for e in r_after.evidence)


def test_blocked_invalid_dep_is_treated_as_pure_stale_and_warned():
    # blocked(dep=미실존) → 무효 → 일반 stale: 승격 후 FAIL + 무효 경고
    text = _pending(" — `blocked(dep=NOPE-NOT-A-TASK)`")
    r_before = evaluate_stale_pending(text, TQ, BEFORE)
    r_after = evaluate_stale_pending(text, TQ, AFTER)
    assert r_before.status == WARN            # 승격 전
    assert r_after.status == ERROR            # 승격 후 FAIL
    assert "무효 blocked" in r_after.detail
    assert any("무효 blocked" in e for e in r_after.evidence)


def test_pure_stale_warn_before_fail_after_promote():
    # 비-blocked 순수 stale → 승격 전 WARN / 승격 후 FAIL
    text = _pending()
    assert evaluate_stale_pending(text, TQ, BEFORE).status == WARN
    assert evaluate_stale_pending(text, TQ, AFTER).status == ERROR


def test_no_stale_is_ok_regression():
    # ⏸️ 없음 → OK (현행 통과 무회귀)
    assert evaluate_stale_pending("> ✅ 정상 블록\n", TQ, AFTER).status == OK
    # 해소 델타(LANDED) 부기된 ⏸️ → 억제 → OK
    resolved = f"> ⏸️ **{OLD} 배포 LANDED**: 완료\n"
    assert evaluate_stale_pending(resolved, TQ, AFTER).status == OK


def test_promote_date_constant_is_gate():
    # 승격일 상수가 게이트 경계 — 경계 직전/당일
    text = _pending()
    assert evaluate_stale_pending(text, TQ, STALE_FAIL_PROMOTE_DATE).status == ERROR  # 당일 승격
    day_before = date(2026, 7, 19)
    assert evaluate_stale_pending(text, TQ, day_before).status == WARN
