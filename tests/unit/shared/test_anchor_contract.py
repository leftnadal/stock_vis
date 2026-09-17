"""
앵커 as_of 계약 회귀 (DSS-ASOF-1-R2 §1 + 애든덤 §2, D-ASOF-POPULATION·D-ASOF-EXEMPT-0912).

🔴 **동결 항목은 사유코드를 갖는다. 사유코드 없이 추가할 수 없고, 새 사유코드를 만드는 것은
   디렉터 결정이다.** 예외는 "테스트가 빨개서"가 아니라 사유 카테고리에 해당해서 들어간다.
   어느 카테고리에도 맞지 않는 새 앵커는 여전히 진짜 신호다 — RED가 옳다.
   이 장치가 없으면 동결 목록은 테스트 무마용 쓰레기통이 된다.

as_of_week 규칙은 **자동 주간 발화**에만 적용 가능하다. 사람이 만든 소급 백필·임시 수집은
실행 시각이 데이터 내용과 무관하므로 관측시각 기반 추론이 원리적으로 불가능하다.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from packages.shared.market_week import (
    ANCHOR_EXEMPTIONS,
    EXEMPT_INCIDENT_PRESERVED,
    EXEMPT_MANUAL_ADHOC,
    EXEMPT_MANUAL_BACKFILL,
    EXEMPT_REASON_CODES,
    exemption_reason,
    find_anchor_violations,
    is_anchor_exempt,
)

ET = ZoneInfo("America/New_York")


def _et(y, m, d, hh, mm):
    return datetime(y, m, d, hh, mm, tzinfo=ET)


# ── 동결 목록 구조 잠금 (쓰레기통화 방지) ────────────────────────────────────
def test_every_exemption_has_a_known_reason_code():
    """🔑 사유코드 없이는(또는 미등록 코드로는) 동결 항목을 추가할 수 없다."""
    for key, value in ANCHOR_EXEMPTIONS.items():
        assert isinstance(value, tuple) and len(value) == 2, (
            f"{key}: 값은 (사유코드, 근거) 튜플이어야 한다"
        )
        code, reason = value
        assert code in EXEMPT_REASON_CODES, (
            f"{key}: 미등록 사유코드 {code!r}. 새 사유코드를 만드는 것은 디렉터 결정이다."
        )
        assert reason.strip(), f"{key}: 근거 문구가 비었다"


def test_reason_codes_are_exactly_the_three_recorded():
    """새 카테고리 신설은 디렉터 결정 — 코드 추가만으로 통과시키지 않는다."""
    assert EXEMPT_REASON_CODES == {
        EXEMPT_MANUAL_BACKFILL,
        EXEMPT_MANUAL_ADHOC,
        EXEMPT_INCIDENT_PRESERVED,
    }


def test_exemption_list_is_exactly_the_six_recorded_entries():
    """2026-09-17 기준 동결 6건. 변경 시 DECISIONS에 근거를 남길 것."""
    assert set(ANCHOR_EXEMPTIONS) == {
        ("SymbolDemandSignal", date(2026, 7, 24)),
        ("SymbolDemandSignal", date(2026, 7, 31)),
        ("SymbolDemandSignal", date(2026, 8, 7)),
        ("EstimateSnapshot", date(2026, 7, 29)),
        ("EstimateSnapshot", date(2026, 9, 12)),
        ("SymbolDemandSignal", date(2026, 9, 12)),
    }


@pytest.mark.parametrize(
    "key, code",
    [
        (("SymbolDemandSignal", date(2026, 7, 24)), EXEMPT_MANUAL_BACKFILL),
        (("EstimateSnapshot", date(2026, 7, 29)), EXEMPT_MANUAL_ADHOC),
        (("EstimateSnapshot", date(2026, 9, 12)), EXEMPT_INCIDENT_PRESERVED),
        (("SymbolDemandSignal", date(2026, 9, 12)), EXEMPT_INCIDENT_PRESERVED),
    ],
)
def test_each_entry_carries_the_right_category(key, code):
    assert exemption_reason(*key)[0] == code


def test_incident_preserved_is_only_for_0912():
    """사건 보존 사유는 09-12 두 건에만 붙는다 — 편의상 확대 금지."""
    incident = {k for k, (c, _) in ANCHOR_EXEMPTIONS.items() if c == EXEMPT_INCIDENT_PRESERVED}
    assert {a for _, a in incident} == {date(2026, 9, 12)}


def test_is_anchor_exempt_is_model_scoped():
    """동결은 (모델, 앵커) 쌍이다 — 날짜만으로 다른 모델까지 면제되지 않는다."""
    assert is_anchor_exempt("SymbolDemandSignal", date(2026, 7, 31)) is True
    assert is_anchor_exempt("EstimateSnapshot", date(2026, 7, 31)) is False


def test_2026_09_11_backfill_is_not_exempt():
    """🔑 09-11 백필분은 동결이 **불필요**하다 — created_at을 원본(09-12 15:03 ET)으로
    유지하므로 as_of_week == 09-11 == anchor 로 규칙을 그대로 만족한다."""
    assert is_anchor_exempt("EstimateSnapshot", date(2026, 9, 11)) is False
    assert find_anchor_violations(
        "EstimateSnapshot", [(date(2026, 9, 11), _et(2026, 9, 12, 15, 3))]
    ) == []


# ── 자동 발화는 규칙을 지킨다 ────────────────────────────────────────────────
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
    """🔑 사유 카테고리에 없는 새 앵커가 규칙을 어기면 RED. 끄는 방법은 '테스트 수정'이 아니다."""
    drift = _et(2026, 10, 3, 15, 0)   # 가상의 토요일 드리프트
    viol = find_anchor_violations("EstimateSnapshot", [(date(2026, 10, 3), drift)])
    assert viol == [(date(2026, 10, 3), drift, date(2026, 10, 2))]


def test_empty_population_is_contract_satisfied():
    assert find_anchor_violations("EstimateSnapshot", []) == []
