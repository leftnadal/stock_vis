"""
앵커 as_of 계약 회귀 (DSS-ASOF-1-R2 §1, D-ASOF-POPULATION).

🔴 동결 목록(`ANCHOR_EXEMPTIONS`)에 항목을 추가하는 것은 **사람의 결정**이지
   테스트를 통과시키는 수단이 아니다. 새 앵커가 규칙을 어기면 RED가 옳다 —
   RED를 끄려면 적재를 고치거나, 사람이 근거를 적어 동결하거나 둘 중 하나다.

as_of_week 규칙은 **자동 주간 발화에만** 적용 가능하다. 사람이 만든 소급 백필·임시 수집은
실행 시각이 데이터 내용과 무관하므로 관측시각 기반 추론이 원리적으로 불가능하다.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from packages.shared.market_week import (
    ANCHOR_EXEMPTIONS,
    find_anchor_violations,
    is_anchor_exempt,
)

ET = ZoneInfo("America/New_York")


def _et(y, m, d, hh, mm):
    return datetime(y, m, d, hh, mm, tzinfo=ET)


# 2026-09-16 실측 기준 동결 4건 — 변경 시 근거를 DECISIONS에 남길 것.
def test_exemption_list_is_exactly_the_four_recorded_entries():
    assert set(ANCHOR_EXEMPTIONS) == {
        ("SymbolDemandSignal", date(2026, 7, 24)),
        ("SymbolDemandSignal", date(2026, 7, 31)),
        ("SymbolDemandSignal", date(2026, 8, 7)),
        ("EstimateSnapshot", date(2026, 7, 29)),
    }


def test_every_exemption_carries_a_reason():
    for key, reason in ANCHOR_EXEMPTIONS.items():
        assert reason.strip(), f"{key}에 근거 문구가 없다"


def test_is_anchor_exempt_is_model_scoped():
    """동결은 (모델, 앵커) 쌍이다 — 날짜만으로 다른 모델까지 면제되지 않는다."""
    assert is_anchor_exempt("SymbolDemandSignal", date(2026, 7, 31)) is True
    assert is_anchor_exempt("EstimateSnapshot", date(2026, 7, 31)) is False


# ── 자동 발화 12건은 규칙을 지킨다(직전 세션 실측 전수) ──────────────────────
def test_automatic_firings_pass():
    rows = [
        (date(2026, 7, 17), _et(2026, 7, 18, 7, 9)),    # 토 catch-up
        (date(2026, 7, 24), _et(2026, 7, 27, 22, 48)),  # 월 catch-up
        (date(2026, 7, 31), _et(2026, 7, 31, 16, 30)),
        (date(2026, 8, 7), _et(2026, 8, 7, 16, 30)),
        (date(2026, 8, 14), _et(2026, 8, 14, 16, 30)),
        (date(2026, 8, 21), _et(2026, 8, 21, 16, 30)),
        (date(2026, 8, 28), _et(2026, 8, 28, 16, 30)),
        (date(2026, 9, 4), _et(2026, 9, 4, 16, 30)),
    ]
    assert find_anchor_violations("EstimateSnapshot", rows) == []


def test_exempted_rows_are_skipped():
    """백필 3건은 as_of가 08-14로 붕괴하지만 동결이므로 위반으로 세지 않는다."""
    backfill_at = _et(2026, 8, 15, 21, 1)
    rows = [(d, backfill_at) for d in
            (date(2026, 7, 24), date(2026, 7, 31), date(2026, 8, 7))]
    assert find_anchor_violations("SymbolDemandSignal", rows) == []
    # 같은 관측시각이라도 동결되지 않은 앵커는 잡힌다
    assert len(find_anchor_violations("SymbolDemandSignal",
                                      [(date(2026, 8, 28), backfill_at)])) == 1


def test_new_drifted_anchor_is_red():
    """🔑 새 앵커가 규칙을 어기면 RED. 이것을 끄는 방법은 '테스트 수정'이 아니다."""
    viol = find_anchor_violations(
        "EstimateSnapshot", [(date(2026, 9, 12), _et(2026, 9, 12, 15, 3))]
    )
    assert viol == [(date(2026, 9, 12), _et(2026, 9, 12, 15, 3), date(2026, 9, 11))]


def test_empty_population_is_contract_satisfied():
    assert find_anchor_violations("EstimateSnapshot", []) == []
