"""SCB-CONTEXT-S2 — AnalystGradeChange dedup·멱등 계약 테스트 (D-SCB-GRADES-KEY-1).

배선(수집 호출자)과 무관한 적재 계약만 검증한다. rate-limit 중단(③)은 배선 결정 후.
표본은 §1-B 실측 원문에서 가져왔다(9심볼 6,137행, 2026-09-19).
"""
import pytest

from packages.shared.stocks.models import AnalystGradeChange
from packages.shared.stocks.services.grade_change_writer import (
    dedup_grade_rows,
    upsert_grade_changes,
)


def _row(symbol, date, company, prev, new, action):
    return {
        "symbol": symbol, "date": date, "gradingCompany": company,
        "previousGrade": prev, "newGrade": new, "action": action,
    }


# §1-B 실측: 전 6필드가 완전히 동일한 유일한 중복군.
IDENTICAL_PAIR = [
    _row("AAPL", "2023-06-16", "Jefferies", "Buy", "Buy", "maintain"),
    _row("AAPL", "2023-06-16", "Jefferies", "Buy", "Buy", "maintain"),
]
# §1-B 실측: 같은 날·같은 기관인데 내용이 상반된 실제 사례(보존되어야 한다).
DIVERGENT_PAIR = [
    _row("TSLA", "2018-05-05", "Argus", "Buy", "Hold", "downgrade"),
    _row("TSLA", "2018-05-05", "Argus", "Hold", "Buy", "upgrade"),
]


class TestDedupPure:
    """dedup_grade_rows — 순수 함수(DB 무접촉)."""

    def test_identical_rows_collapse_with_count(self):
        """④ 완전동일 2행 → 1행 + source_row_count=2 (정보 손실 0)."""
        out = dedup_grade_rows(IDENTICAL_PAIR)
        assert len(out) == 1
        assert out[0]["source_row_count"] == 2
        assert out[0]["symbol"] == "AAPL"
        assert out[0]["new_grade"] == "Buy"

    def test_divergent_same_day_same_company_both_preserved(self):
        """⑤ 같은 날·같은 기관이라도 내용이 다르면 별 행 — 이 설계의 핵심 계약."""
        out = dedup_grade_rows(DIVERGENT_PAIR)
        assert len(out) == 2
        assert {r["source_row_count"] for r in out} == {1}
        assert {(r["previous_grade"], r["new_grade"], r["action"]) for r in out} == {
            ("Buy", "Hold", "downgrade"),
            ("Hold", "Buy", "upgrade"),
        }

    def test_empty_input_is_not_an_error(self):
        """② 빈 응답은 에러가 아니라 무작업."""
        assert dedup_grade_rows([]) == []
        assert dedup_grade_rows(None) == []

    def test_missing_required_fields_dropped_not_raised(self):
        """symbol·date 결손 행은 예외가 아니라 제외."""
        out = dedup_grade_rows([
            _row("", "2026-01-01", "X", "Buy", "Buy", "maintain"),
            _row("AAPL", "", "X", "Buy", "Buy", "maintain"),
            _row("AAPL", "not-a-date", "X", "Buy", "Buy", "maintain"),
            _row("aapl", "2026-01-01", "X", "Buy", "Buy", "maintain"),  # 소문자 정규화
        ])
        assert len(out) == 1
        assert out[0]["symbol"] == "AAPL"


@pytest.mark.django_db
class TestUpsertIdempotent:
    """upsert_grade_changes — 멱등 계약."""

    def test_same_payload_twice_is_stable(self):
        """① 같은 응답 2회 적용 → 행 수 불변 + source_row_count 동일."""
        payload = IDENTICAL_PAIR + DIVERGENT_PAIR

        first = upsert_grade_changes(payload)
        assert first == {"created": 3, "updated": 0, "rows_in": 4, "rows_out": 3}
        assert AnalystGradeChange.objects.count() == 3

        second = upsert_grade_changes(payload)
        assert second["created"] == 0
        assert second["updated"] == 3
        assert AnalystGradeChange.objects.count() == 3  # 행 수 불변

        aapl = AnalystGradeChange.objects.get(symbol="AAPL", grading_company="Jefferies")
        assert aapl.source_row_count == 2  # 카운트도 동일값 유지

    def test_empty_payload_writes_nothing(self):
        """② 빈 응답 → created 0, 예외 없음."""
        res = upsert_grade_changes([])
        assert res == {"created": 0, "updated": 0, "rows_in": 0, "rows_out": 0}
        assert AnalystGradeChange.objects.count() == 0

    def test_unique_constraint_matches_natural_key(self):
        """6필드 unique가 실제로 걸려 있어 상이 행은 공존한다."""
        upsert_grade_changes(DIVERGENT_PAIR)
        rows = AnalystGradeChange.objects.filter(symbol="TSLA", grading_company="Argus")
        assert rows.count() == 2
        assert rows.filter(action="downgrade").exists()
        assert rows.filter(action="upgrade").exists()

    def test_new_row_appearing_later_is_added_not_replaced(self):
        """재수집에서 신규 사건만 늘어난다(기존 무손상)."""
        upsert_grade_changes(DIVERGENT_PAIR)
        grown = DIVERGENT_PAIR + [
            _row("TSLA", "2020-09-23", "Deutsche Bank", "Hold", "Buy", "upgrade")
        ]
        res = upsert_grade_changes(grown)
        assert res["created"] == 1
        assert res["updated"] == 2
        assert AnalystGradeChange.objects.filter(symbol="TSLA").count() == 3
