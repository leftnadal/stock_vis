"""
C2a 내부자 파이프라인 테스트 (TH-2, 설계서 §5.1).

검증:
- 방어 필터 4규칙 (집계 계층): 공란 제외 / S-Sale·P-Purchase만 (A-Award 매수 오인 금지)
  / price=0 금액가중 제외 / type_of_owner 가중 1.0·0.7·0.5
- net_sell_ratio 산식 정확성
- dedup_key 안정성 + upsert 멱등 (재실행 안전)
- 전건 보존 (공란 적재)
- E3 sanity check 경고만 (예외 없음)
"""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import pytest

from apps.chain_sight.models import InsiderTransactionRecord
from apps.chain_sight.services import insider_service as svc


def _rec(ttype, price, shares, owner="officer", di="D"):
    """미저장 인스턴스 (필터 로직 순수 테스트용)."""
    return InsiderTransactionRecord(
        symbol="NVDA",
        filing_date=date(2026, 6, 29),
        transaction_date=date(2026, 6, 25),
        transaction_type=ttype,
        price=None if price is None else Decimal(str(price)),
        securities_transacted=None if shares is None else Decimal(str(shares)),
        type_of_owner=owner,
        direct_or_indirect=di,
        dedup_key=f"{ttype}-{price}-{shares}-{owner}-{di}",
    )


# ─────────────────────── 방어 필터 4규칙 ───────────────────────
class TestDefensiveFilters:
    def test_a_award_not_counted_as_buy(self):
        """핵심: A-Award 는 매수로 오인되지 않는다 (제외). S-Sale 단독 → ratio=1.0."""
        records = [
            _rec("S-Sale", 100, 10, "officer"),        # weighted_sell = 1000
            _rec("A-Award", 50, 1000, "director"),     # 무시 (매수 오인 시 ratio 급락)
        ]
        assert svc.compute_c2a_net_sell_ratio(records) == 1.0

    def test_blank_type_excluded(self):
        records = [_rec("S-Sale", 100, 10), _rec("", 100, 10)]
        assert svc.compute_c2a_net_sell_ratio(records) == 1.0

    def test_other_types_excluded(self):
        for t in ("M-Exempt", "F-InKind", "G-Gift"):
            records = [_rec("S-Sale", 100, 10), _rec(t, 100, 1000)]
            assert svc.compute_c2a_net_sell_ratio(records) == 1.0, t

    def test_price_zero_excluded_from_amount(self):
        """price=0 은 금액가중 불가 → 제외. 매수 price=0 이면 매수측 0 → ratio=1.0."""
        records = [_rec("S-Sale", 100, 10), _rec("P-Purchase", 0, 10)]
        assert svc.compute_c2a_net_sell_ratio(records) == 1.0

    def test_sell_buy_ratio(self):
        """S-Sale 1000 vs P-Purchase 1000 → 0.5."""
        records = [_rec("S-Sale", 100, 10), _rec("P-Purchase", 100, 10)]
        assert svc.compute_c2a_net_sell_ratio(records) == 0.5

    def test_none_when_no_valid(self):
        records = [_rec("A-Award", 50, 1000), _rec("", 100, 10)]
        assert svc.compute_c2a_net_sell_ratio(records) is None


class TestOwnerWeight:
    def test_officer_director_1_0(self):
        assert svc.owner_weight(_rec("S-Sale", 1, 1, "officer: CEO", "D")) == 1.0

    def test_ten_percent_0_7(self):
        assert svc.owner_weight(_rec("S-Sale", 1, 1, "10% owner", "D")) == 0.7

    def test_indirect_0_5(self):
        assert svc.owner_weight(_rec("S-Sale", 1, 1, "officer", "I")) == 0.5

    def test_weight_applied_in_ratio(self):
        """간접 매도(0.5) vs 직접 매수(1.0): sell=100*10*0.5=500, buy=100*10*1.0=1000 → 500/1500."""
        records = [
            _rec("S-Sale", 100, 10, "officer", "I"),
            _rec("P-Purchase", 100, 10, "officer", "D"),
        ]
        assert svc.compute_c2a_net_sell_ratio(records) == pytest.approx(500 / 1500)


# ─────────────────────── dedup_key + 멱등 + 적재 ───────────────────────
class TestDedupAndUpsert:
    def test_dedup_key_stable(self):
        row = {
            "symbol": "nvda", "reportingCik": "123", "transactionDate": "2026-06-25",
            "transactionType": "S-Sale", "securitiesTransacted": 1211, "price": 308.63,
        }
        assert svc.build_dedup_key(row) == svc.build_dedup_key(dict(row))
        assert len(svc.build_dedup_key(row)) == 64  # varchar(64) 정합

    def test_map_preserves_blank_type(self):
        row = {"symbol": "AAPL", "filingDate": "2026-06-17", "transactionDate": "2026-06-15",
               "transactionType": "", "price": 0}
        mapped = svc.map_fmp_row(row)
        assert mapped["transaction_type"] == ""  # 전건 보존

    def test_map_skips_missing_dates(self):
        assert svc.map_fmp_row({"symbol": "X", "transactionType": "S-Sale"}) is None

    @pytest.mark.django_db
    def test_upsert_idempotent(self):
        row = {
            "symbol": "NVDA", "reportingCik": "123", "companyCik": "456",
            "filingDate": "2026-06-29", "transactionDate": "2026-06-25",
            "transactionType": "S-Sale", "securitiesTransacted": 1211, "price": 308.63,
            "typeOfOwner": "director", "directOrIndirect": "D",
            "acquisitionOrDisposition": "D", "url": "https://sec.gov/x",
        }
        r1 = svc.upsert_insider_records([row])
        assert r1["created"] == 1
        r2 = svc.upsert_insider_records([row])  # 재실행
        assert r2["created"] == 0 and r2["updated"] == 1
        assert InsiderTransactionRecord.objects.count() == 1  # 중복 미생성

    @pytest.mark.django_db
    def test_future_transaction_date_skipped(self):
        """적재 단 상한 위생: transaction_date > max 는 제외 (미래일 이상치)."""
        base = {"symbol": "NVDA", "filingDate": "2026-06-29", "reportingCik": "1",
                "transactionType": "S-Sale", "securitiesTransacted": 10, "price": 100}
        res = svc.upsert_insider_records(
            [
                {**base, "transactionDate": "2026-06-25"},               # 과거 = OK
                {**base, "transactionDate": "2035-02-05", "reportingCik": "2"},  # 미래 = 제외
            ],
            max_transaction_date=date(2026, 7, 7),
        )
        assert res["created"] == 1 and res["future_skipped"] == 1
        assert InsiderTransactionRecord.objects.count() == 1

    @pytest.mark.django_db
    def test_net_sell_ratio_for_symbols_window(self):
        base = {"symbol": "NVDA", "filingDate": "2026-06-29", "reportingCik": "1",
                "typeOfOwner": "officer", "directOrIndirect": "D"}
        svc.upsert_insider_records([
            {**base, "transactionDate": "2026-06-25", "transactionType": "S-Sale",
             "securitiesTransacted": 10, "price": 100},
            {**base, "transactionDate": "2020-01-01", "transactionType": "P-Purchase",
             "securitiesTransacted": 10, "price": 100, "reportingCik": "2"},  # 창 밖
        ])
        # 90일 창 = S-Sale 만 → 1.0 (창 밖 매수 미포함)
        ratio = svc.net_sell_ratio_for_symbols(["NVDA"], as_of=date(2026, 6, 29))
        assert ratio == 1.0


# ─────────────────────── E3 sanity check ───────────────────────
class TestE3Sanity:
    def test_e3_match_ok(self):
        client = Mock()
        client.get_insider_statistics.return_value = [
            {"disposedTransactions": 10, "acquiredTransactions": 5}
        ]
        res = svc.e3_sanity_check(client, "NVDA", self_disposed=10, self_acquired=5)
        assert res["ok"] is True

    def test_e3_mismatch_warns_no_raise(self):
        client = Mock()
        client.get_insider_statistics.return_value = [
            {"disposedTransactions": 100, "acquiredTransactions": 5}
        ]
        res = svc.e3_sanity_check(client, "NVDA", self_disposed=10, self_acquired=5)
        assert res["ok"] is False  # 경고만, 예외 없음

    def test_e3_no_data(self):
        client = Mock()
        client.get_insider_statistics.return_value = []
        assert svc.e3_sanity_check(client, "NVDA", 0, 0)["ok"] is None
