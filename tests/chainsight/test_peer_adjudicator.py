"""⑳-3 L2-X 자동 판정기 — grounding/market/cross 결정론 판정 (LLM 무호출)."""

from apps.chain_sight.services.peer_adjudicator import (
    ground_claim,
    market_flag,
    overconfident,
    quartiles,
    load_dict,
)

DCT = {
    "반도체": ["semiconductor"],
    "메모리": ["memory"],
    "스토리지": ["storage"],
    "결제": ["payment"],
}


class TestGroundClaim:
    def test_clearly_grounded(self):
        # claim 용어(semiconductor·memory·반도체·메모리)가 desc에 존재 → 높은 ratio
        r = ground_claim(
            claim="반도체 및 메모리. semiconductor memory storage.",
            symbol_a="AAA", symbol_b="BBB",
            desc_a="A semiconductor and memory company.",
            desc_b="B makes memory and storage chips.", dct=DCT,
        )
        assert r["grounded_ratio"] == 1.0  # 전 용어 desc 존재
        assert r["ungrounded_terms"] == []

    def test_clearly_ungrounded(self):
        # claim이 banking을 주장하나 desc는 반도체 → ungrounded
        r = ground_claim(
            claim="결제 및 뱅킹. payment banking services.",
            symbol_a="AAA", symbol_b="BBB",
            desc_a="A semiconductor foundry.",
            desc_b="B makes memory chips.", dct=DCT,
        )
        assert r["grounded_ratio"] < 0.5
        assert "payment" in r["ungrounded_terms"] or "결제" in r["ungrounded_terms"]

    def test_symbol_tokens_excluded(self):
        # 심볼 MCO/NDAQ는 추출 제외(desc에 있어도 grounding 증거 무의미)
        r = ground_claim(
            claim="MCO는 신용, NDAQ는 데이터. rating and data.",
            symbol_a="MCO", symbol_b="NDAQ",
            desc_a="MCO provides ratings.", desc_b="NDAQ provides data.",
            dct={"신용": ["rating", "credit"], "데이터": ["data"]},
        )
        # 영어 토큰 rating/data만(심볼 제외). 둘 다 desc에 있음
        assert "mco" not in [t for t in r["ungrounded_terms"]]
        assert "ndaq" not in [t for t in r["ungrounded_terms"]]

    def test_synonym_grounding(self):
        r = ground_claim(
            claim="반도체 회사", symbol_a="A", symbol_b="B",
            desc_a="semiconductor manufacturer", desc_b="chip maker", dct=DCT,
        )
        assert r["grounded_syn"] == 1  # 반도체→semiconductor 매칭

    def test_dict_gap_surfaced(self):
        # 사전 미수록 도메인어는 dict_gap으로 표면화(보충 대상)
        r = ground_claim(
            claim="항공우주 부품을 생산한다", symbol_a="A", symbol_b="B",
            desc_a="aerospace parts", desc_b="components", dct=DCT,
        )
        assert any("항공" in g or "생산" in g for g in r["dict_gap_terms"])


class TestQuartiles:
    def test_q1_q3(self):
        q1, q3 = quartiles([1, 2, 3, 4, 5, 6, 7, 8])
        assert q1 <= q3

    def test_empty(self):
        assert quartiles([]) == (None, None)
        assert quartiles([None, None]) == (None, None)


class TestMarketFlag:
    def test_high_conf_low_corr_flags(self):
        # conf 상위(0.95≥conf_q3=0.9) ∧ 상관 하위(0.1≤corr_q1=0.3) → 불일치
        assert market_flag(0.1, 0.95, corr_q1=0.3, conf_q3=0.9) is True

    def test_otherwise_no_flag(self):
        assert market_flag(0.8, 0.95, corr_q1=0.3, conf_q3=0.9) is False  # 상관 높음
        assert market_flag(0.1, 0.5, corr_q1=0.3, conf_q3=0.9) is False   # conf 낮음
        assert market_flag(None, 0.95, 0.3, 0.9) is False                  # 상관 결측


class TestOverconfident:
    def test_known_fact_low_grounded(self):
        assert overconfident("known_fact", 0.1, gr_q1=0.3) is True

    def test_not_known_fact(self):
        assert overconfident("inference", 0.1, gr_q1=0.3) is False

    def test_high_grounded(self):
        assert overconfident("known_fact", 0.9, gr_q1=0.3) is False


def test_real_dict_loads():
    d = load_dict()
    assert "반도체" in d and "금융" in d
    assert isinstance(d["반도체"], list)
