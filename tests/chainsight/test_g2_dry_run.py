"""G2 dry-run 하네스 순수함수 테스트 (TH-C3-LLM-DICT-1, 3f 종결).

복원 산식(final_confirmed.cell/ov_refs/agg)의 tally 로직을 합성 픽스처로 검증한다.
DB 비의존(순수함수만) — CI 에서 격리 실행 가능. 목표치 92/19/0/0 재현은 별도 3f 집행
(관리 명령 --date-cut) 에서 실측한다(여기서는 로직 정확성만).
"""
from collections import Counter

from apps.chain_sight.services.g2_dry_run import (
    classify_cell,
    credit_refs,
    tally_after_credit,
    want_set,
)


class TestWantSet:
    def test_none_and_empty(self):
        assert want_set("none") == frozenset()
        assert want_set("") == frozenset()
        assert want_set(None) == frozenset()

    def test_single_and_csv(self):
        assert want_set("Technology") == frozenset({"Technology"})
        assert want_set("Technology, Energy") == frozenset({"Technology", "Energy"})


class TestClassifyCell:
    def test_real_pollute(self):
        # want 있음(real) + prod 가 want 밖 섹터 생성(pollute)
        assert classify_cell(frozenset({"Industrials"}), frozenset({"Technology"})) == "real_pollute"

    def test_real_noeffect(self):
        # want 있음(real) + prod 가 want 를 초과하지 않음(noeffect): prod=want
        assert classify_cell(frozenset({"Technology"}), frozenset({"Technology"})) == "real_noeffect"
        # prod 공집합(현행 규칙 무매칭) 도 noeffect
        assert classify_cell(frozenset(), frozenset({"Technology"})) == "real_noeffect"

    def test_none_pollute(self):
        # want 없음(none) + prod 가 (엉뚱한) 섹터 생성(pollute → 제거=실감소)
        assert classify_cell(frozenset({"Technology"}), frozenset()) == "none_pollute"

    def test_none_noeffect(self):
        # want 없음(none) + prod 도 공집합(pseudo 토큰만 → 델타 0)
        assert classify_cell(frozenset(), frozenset()) == "none_noeffect"

    def test_pollute_needs_extra_sector(self):
        # prod ⊆ want 면 초과분 없음 → noeffect (prod 가 want 부분집합)
        assert classify_cell(frozenset({"Technology"}), frozenset({"Technology", "Energy"})) == "real_noeffect"


class TestCreditRefs:
    ENT = frozenset({"Technology", "Energy", "Financial Services"})

    def test_none_zero(self):
        assert credit_refs("none", self.ENT) == []
        assert credit_refs("", self.ENT) == []

    def test_reassign_intersect_entities(self):
        assert credit_refs("Technology", self.ENT) == ["Technology"]
        # entities 밖 섹터는 제외
        assert credit_refs("Technology, Materials", self.ENT) == ["Technology"]

    def test_multi_credit(self):
        assert sorted(credit_refs("Technology, Energy", self.ENT)) == ["Energy", "Technology"]


class TestTallyAfterCredit:
    def test_credits_accumulate_by_cell(self):
        # cell_of: term→셀, refs_after: term→크레딧수
        cell_of = {"a": "real_pollute", "b": "real_noeffect", "c": "none_pollute"}
        refs_after = {"a": 1, "b": 1, "c": 0}
        # 코퍼스: a 3회, b 2회, c 5회, 미등재 z 4회
        corpus = ["a", "a", "a", "b", "b", "c", "c", "c", "c", "c", "z", "z", "z", "z"]
        got = tally_after_credit(corpus, cell_of, refs_after)
        assert got["real_pollute"] == 3   # a×3 × 크레딧1
        assert got["real_noeffect"] == 2  # b×2 × 크레딧1
        assert got["none_pollute"] == 0   # c×5 × 크레딧0 (제거)
        assert got.get("none_noeffect", 0) == 0

    def test_multi_credit_term(self):
        cell_of = {"m": "real_pollute"}
        refs_after = {"m": 2}   # 2개 섹터 재배정
        got = tally_after_credit(["m", "m"], cell_of, refs_after)
        assert got["real_pollute"] == 4   # 2회 등장 × 크레딧2

    def test_unregistered_terms_ignored(self):
        got = tally_after_credit(["x", "y", "z"], {}, {})
        assert got == Counter()
