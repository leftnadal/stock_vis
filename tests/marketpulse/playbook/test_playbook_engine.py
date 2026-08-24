"""Playbook evaluator 단위 테스트 (1.6-S1) — 합성 신호로 판정 고정(DB 무관).

점등 카운트·부분 점등·pending(전 대기)·data_as_of·load_chains 로스터 8종.
"""

from __future__ import annotations

from apps.market_pulse.playbook.context import PlaybookContext
from apps.market_pulse.playbook.engine import (
    STATE_ACTIVE,
    STATE_DORMANT,
    STATE_PARTIAL,
    STATE_PENDING,
    evaluate_chain,
    load_chains,
)


def _ctx(signals: dict, as_of: dict | None = None) -> PlaybookContext:
    return PlaybookContext(signals=signals, data_as_of=as_of or {})


CHAIN_3 = {
    "id": "c3",
    "name": "테스트3",
    "narrative": "n",
    "cadence": "daily",
    "conditions": [
        {"signal": "a", "op": ">=", "threshold": 1.0, "label": "A"},
        {"signal": "b", "op": ">=", "threshold": 1.0, "label": "B"},
        {"signal": "c", "op": "<=", "threshold": -1.0, "label": "C"},
    ],
}


class TestPartialLighting:
    def test_전점등_active(self):
        r = evaluate_chain(_ctx({"a": 2.0, "b": 1.5, "c": -2.0}), CHAIN_3)
        assert r["state"] == STATE_ACTIVE
        assert (r["lit_count"], r["total"]) == (3, 3)

    def test_부분점등_partial(self):
        r = evaluate_chain(_ctx({"a": 2.0, "b": 0.0, "c": 0.0}), CHAIN_3)
        assert r["state"] == STATE_PARTIAL
        assert r["lit_count"] == 1

    def test_무점등_dormant(self):
        r = evaluate_chain(_ctx({"a": 0.0, "b": 0.0, "c": 0.0}), CHAIN_3)
        assert r["state"] == STATE_DORMANT
        assert r["lit_count"] == 0

    def test_전_신호부재_pending(self):
        # 신호 자체가 없으면(None) 판정 불가 = 대기
        r = evaluate_chain(_ctx({}), CHAIN_3)
        assert r["state"] == STATE_PENDING

    def test_일부부재는_대기가_아니라_남은것으로_판정(self):
        # a 점등 + b/c 부재 → missing<total 이므로 partial(오판정 금지: 부재는 미점등)
        r = evaluate_chain(_ctx({"a": 2.0}), CHAIN_3)
        assert r["state"] == STATE_PARTIAL
        assert r["lit_count"] == 1
        # 부재 조건은 lit=None으로 표기(FE "데이터 대기" 렌더)
        lits = [c["lit"] for c in r["conditions"]]
        assert lits == [True, None, None]


class TestPersistenceAndOps:
    def test_lt_op_역전_점등(self):
        chain = {"id": "v", "name": "v", "conditions": [{"signal": "ratio", "op": "<", "threshold": 1.0, "label": "R"}]}
        assert evaluate_chain(_ctx({"ratio": 0.95}), chain)["state"] == STATE_ACTIVE
        assert evaluate_chain(_ctx({"ratio": 1.05}), chain)["state"] == STATE_DORMANT

    def test_persistence_신호_1점등(self):
        chain = {"id": "p", "name": "p", "conditions": [{"signal": "persist", "op": ">=", "threshold": 1.0, "label": "P"}]}
        assert evaluate_chain(_ctx({"persist": 1.0}), chain)["state"] == STATE_ACTIVE
        assert evaluate_chain(_ctx({"persist": 0.0}), chain)["state"] == STATE_DORMANT


class TestDataAsOf:
    def test_가장_오래된_기준일_지배(self):
        as_of = {"a": "2026-08-24", "b": "2026-08-14", "c": "2026-08-20"}
        r = evaluate_chain(_ctx({"a": 0, "b": 0, "c": 0}, as_of), CHAIN_3)
        assert r["data_as_of"] == "2026-08-14"  # weekly 신호가 지배


class TestRoster:
    def test_로스터_8종_확정(self):
        chains = load_chains(force=True)["chains"]
        ids = [c["id"] for c in chains]
        assert len(ids) == 8
        assert ids == [
            "risk_off", "credit_stress", "rate_shock", "vol_term_inversion",
            "concentration_fragility", "curve_shift", "dollar_squeeze", "financial_tightening",
        ]

    def test_weekly_체인_1종_financial_tightening(self):
        chains = load_chains(force=True)["chains"]
        weekly = [c["id"] for c in chains if c.get("cadence") == "weekly"]
        assert weekly == ["financial_tightening"]

    def test_서사_위기어휘_금지(self):
        # 카피 게이트: narrative에 "위기" 프레이밍 금지
        chains = load_chains(force=True)["chains"]
        for c in chains:
            assert "위기" not in (c.get("narrative") or "")
            assert "crisis" not in (c.get("narrative") or "").lower()
