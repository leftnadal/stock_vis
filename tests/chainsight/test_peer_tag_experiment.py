"""⑳-3 S3-MINDMAP 패치1 — L2-X PEER 추측 태깅 실험 하네스."""

from apps.chain_sight.management.commands.peer_tag_experiment import (
    PER_CELL,
    TARGET,
    aggregate,
    build_experiment_prompt,
    build_sample,
)


class TestPrompt:
    def test_variant_a_symbols_only(self):
        row = {"symbol_a": "NVDA", "symbol_b": "AMD", "prompt_variant": "A"}
        _, contents = build_experiment_prompt(row, {"NVDA": "Nvidia"}, {"NVDA": "Semiconductors"})
        assert "NVDA" in contents[0] and "AMD" in contents[0]
        assert "Nvidia" not in contents[0]  # ㉮는 회사명 없음
        assert "Semiconductors" not in contents[0]

    def test_variant_b_includes_name_industry(self):
        row = {"symbol_a": "NVDA", "symbol_b": "AMD", "prompt_variant": "B"}
        _, contents = build_experiment_prompt(
            row, {"NVDA": "Nvidia", "AMD": "AMD Inc"}, {"NVDA": "Semiconductors", "AMD": "Semiconductors"},
        )
        assert "Nvidia" in contents[0] and "Semiconductors" in contents[0]


class TestSampleGate:
    def test_halt_when_population_insufficient(self):
        # 실 데이터 모사: mcap 보유 심볼 소수 → 모집단 < 240 → HALT
        peers = [{"symbol_a": f"A{i}", "symbol_b": f"B{i}"} for i in range(300)]
        mcap = {"A0": 100, "B0": 200}  # 극소수만 mcap
        ind = {"A0": "X", "B0": "Y"}
        sample, halt = build_sample(peers, mcap, ind)
        assert sample == []
        assert halt and "mcap 게이트 HALT" in halt

    def test_stratified_sample_when_sufficient(self):
        # 합성 충분 모집단: 6구획 각 ≥ PER_CELL
        peers, mcap, ind = [], {}, {}
        n = 0
        # mcap 3분위 × industry 동일/상이 각 (PER_CELL+5)쌍 생성
        for tier, base in [("lo", 10), ("mid", 1000), ("hi", 100000)]:
            for same in (True, False):
                for k in range(PER_CELL + 5):
                    a, b = f"{tier}{same}A{k}", f"{tier}{same}B{k}"
                    peers.append({"symbol_a": a, "symbol_b": b})
                    mcap[a] = base + k
                    mcap[b] = base + k + 1
                    ind[a] = "SameInd"
                    ind[b] = "SameInd" if same else "OtherInd"
                    n += 1
        sample, halt = build_sample(peers, mcap, ind)
        assert halt is None, halt
        assert len(sample) == TARGET  # 240
        # ㉮㉯ 균형: 구획당 20/20
        variants = [r["prompt_variant"] for r in sample]
        assert variants.count("A") == TARGET // 2
        assert variants.count("B") == TARGET // 2
        # 6구획 커버
        cells = {(r["mcap_tercile"], r["industry_same"]) for r in sample}
        assert len(cells) == 6

    def test_sample_is_deterministic(self):
        peers, mcap, ind = _synthetic()
        s1, _ = build_sample(peers, mcap, ind)
        s2, _ = build_sample(peers, mcap, ind)
        assert [r["symbol_a"] for r in s1] == [r["symbol_a"] for r in s2]  # 시드 고정


class TestAggregate:
    def test_per_cell_and_variant(self):
        rows = [
            {"mcap_tercile": "상", "industry_same": "동일", "prompt_variant": "A", "verdict": "BETTER"},
            {"mcap_tercile": "상", "industry_same": "동일", "prompt_variant": "B", "verdict": "SAME"},
            {"mcap_tercile": "상", "industry_same": "동일", "prompt_variant": "A", "verdict": ""},  # 미채움 제외
        ]
        agg = aggregate(rows)
        assert agg["by_cell"][("상", "동일")] == {"BETTER": 1, "SAME": 1}
        assert agg["by_variant"]["A"] == {"BETTER": 1}
        assert agg["by_variant"]["B"] == {"SAME": 1}


def _synthetic():
    peers, mcap, ind = [], {}, {}
    for tier, base in [("lo", 10), ("mid", 1000), ("hi", 100000)]:
        for same in (True, False):
            for k in range(PER_CELL + 5):
                a, b = f"{tier}{same}A{k}", f"{tier}{same}B{k}"
                peers.append({"symbol_a": a, "symbol_b": b})
                mcap[a] = base + k
                mcap[b] = base + k + 1
                ind[a] = "SameInd"
                ind[b] = "SameInd" if same else "OtherInd"
    return peers, mcap, ind
