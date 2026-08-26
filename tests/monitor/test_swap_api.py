"""교체 검토 API 검증 (RECON-SWAP-0813 PART 3-BE): evidence-status · swap-hold-logs ·
decision-journal-entries. D-FIXTURE-FIXED-BASE 준수(as_of=고정일)."""
from datetime import date, datetime

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.monitor.models import (
    Claim,
    ClaimEvidence,
    DecisionJournalEntry,
    Monitor,
    MonitorIndicator,
    SwapHoldLog,
)

User = get_user_model()

_AS_OF = date(2026, 8, 10)


@pytest.fixture
def alice(db):
    return User.objects.create_user(username="swap_alice", password="pw12345")


@pytest.fixture
def bob(db):
    return User.objects.create_user(username="swap_bob", password="pw12345")


@pytest.fixture
def client_alice(alice):
    c = APIClient()
    c.force_authenticate(user=alice)
    return c


@pytest.fixture
def client_bob(bob):
    c = APIClient()
    c.force_authenticate(user=bob)
    return c


@pytest.fixture
def alice_monitor(alice):
    return Monitor.objects.create(
        user=alice, scope=Monitor.Scope.STOCK, target_ref="AAPL", name="애플 감시"
    )


@pytest.fixture
def alice_claim(alice_monitor):
    return Claim.objects.create(monitor=alice_monitor, assertion="애플 강세 지속")


@pytest.fixture
def bob_monitor(bob):
    return Monitor.objects.create(
        user=bob, scope=Monitor.Scope.STOCK, target_ref="MSFT", name="MS 감시"
    )


@pytest.fixture
def bob_claim(bob_monitor):
    return Claim.objects.create(monitor=bob_monitor, assertion="MS 강세 지속")


# ── evidence-status ─────────────────────────────────────────────────────


@pytest.mark.django_db
class TestClaimEvidenceStatusAPI:
    def test_unauthenticated_rejected(self, alice_claim):
        resp = APIClient().get(f"/api/v1/monitor/claims/{alice_claim.id}/evidence-status/")
        assert resp.status_code in (401, 403)

    def test_manual_and_auto_enriched(self, client_alice, alice_claim, alice_monitor):
        ind = MonitorIndicator.objects.create(
            monitor=alice_monitor,
            name="12-1 모멘텀",
            indicator_type=MonitorIndicator.IndicatorType.TECHNICAL,
        )
        auto_ev = ClaimEvidence.objects.create(
            claim=alice_claim, kind=ClaimEvidence.Kind.AUTO,
            indicator=ind, operator=ClaimEvidence.Operator.GTE, threshold=0.3,
        )
        manual_ev = ClaimEvidence.objects.create(
            claim=alice_claim, kind=ClaimEvidence.Kind.MANUAL,
            description="AI 인프라 테마 열기 지속",
            last_confirmed_at=_AS_OF, recheck_period_days=90,
        )
        resp = client_alice.get(
            f"/api/v1/monitor/claims/{alice_claim.id}/evidence-status/?as_of={_AS_OF.isoformat()}"
        )
        assert resp.status_code == 200
        data = resp.data
        assert str(data["claim_id"]) == str(alice_claim.id)
        assert data["as_of"] == _AS_OF.isoformat()
        assert data["total"] == 2

        by_id = {r["evidence_id"]: r for r in data["results"]}
        # 자동형: readings 없어 unknown, 지표명 노출
        assert by_id[auto_ev.id]["status"] == "unknown"
        assert by_id[auto_ev.id]["indicator_name"] == "12-1 모멘텀"
        assert by_id[auto_ev.id]["description"] == ""
        # 수동형: 재확인 주기 내 → alive, 서술 노출
        assert by_id[manual_ev.id]["status"] == "alive"
        assert by_id[manual_ev.id]["description"] == "AI 인프라 테마 열기 지속"
        assert by_id[manual_ev.id]["indicator_name"] is None
        assert data["alive"] == 1

    def test_default_as_of_is_today(self, client_alice, alice_claim):
        ClaimEvidence.objects.create(
            claim=alice_claim, kind=ClaimEvidence.Kind.MANUAL,
            description="근거", last_confirmed_at=_AS_OF, recheck_period_days=90,
        )
        resp = client_alice.get(f"/api/v1/monitor/claims/{alice_claim.id}/evidence-status/")
        assert resp.status_code == 200
        assert resp.data["as_of"] is not None

    def test_invalid_as_of_format_400(self, client_alice, alice_claim):
        resp = client_alice.get(
            f"/api/v1/monitor/claims/{alice_claim.id}/evidence-status/?as_of=not-a-date"
        )
        assert resp.status_code == 400

    def test_no_evidences_returns_empty(self, client_alice, alice_claim):
        resp = client_alice.get(
            f"/api/v1/monitor/claims/{alice_claim.id}/evidence-status/?as_of={_AS_OF.isoformat()}"
        )
        assert resp.status_code == 200
        assert resp.data["total"] == 0
        assert resp.data["alive"] == 0
        assert resp.data["results"] == []

    def test_other_user_claim_404(self, client_alice, bob_claim):
        resp = client_alice.get(f"/api/v1/monitor/claims/{bob_claim.id}/evidence-status/")
        assert resp.status_code == 404  # user 스코프 격리(IDOR 방지)

    def test_read_only_no_db_write(self, client_alice, alice_claim):
        ClaimEvidence.objects.create(
            claim=alice_claim, kind=ClaimEvidence.Kind.MANUAL,
            description="근거", last_confirmed_at=_AS_OF, recheck_period_days=90,
        )
        before = ClaimEvidence.objects.count()
        client_alice.get(
            f"/api/v1/monitor/claims/{alice_claim.id}/evidence-status/?as_of={_AS_OF.isoformat()}"
        )
        assert ClaimEvidence.objects.count() == before


# ── swap-hold-logs ───────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSwapHoldLogAPI:
    def test_unauthenticated_rejected(self):
        resp = APIClient().get("/api/v1/monitor/swap-hold-logs/")
        assert resp.status_code in (401, 403)

    def test_create_uppercases_candidate_ref(self, client_alice, alice_claim):
        resp = client_alice.post(
            "/api/v1/monitor/swap-hold-logs/",
            {"claim": str(alice_claim.id), "candidate_ref": "msft", "note": "관망"},
        )
        assert resp.status_code == 201, resp.data
        assert resp.data["candidate_ref"] == "MSFT"
        assert resp.data["note"] == "관망"
        assert SwapHoldLog.objects.filter(claim=alice_claim).count() == 1

    def test_list_filtered_by_claim(self, client_alice, alice_claim, alice_monitor):
        other_claim = Claim.objects.create(monitor=alice_monitor, assertion="다른 주장")
        SwapHoldLog.objects.create(claim=alice_claim, candidate_ref="MSFT")
        SwapHoldLog.objects.create(claim=other_claim, candidate_ref="NVDA")
        resp = client_alice.get(f"/api/v1/monitor/swap-hold-logs/?claim={alice_claim.id}")
        assert resp.status_code == 200
        data = resp.data["results"] if isinstance(resp.data, dict) and "results" in resp.data else resp.data
        assert len(data) == 1
        assert data[0]["candidate_ref"] == "MSFT"

    def test_create_for_other_user_claim_forbidden(self, client_bob, alice_claim):
        resp = client_bob.post(
            "/api/v1/monitor/swap-hold-logs/",
            {"claim": str(alice_claim.id), "candidate_ref": "MSFT"},
        )
        assert resp.status_code == 403  # _assert_owner PermissionDenied

    def test_list_user_scoped(self, client_alice, client_bob, alice_claim, bob_claim):
        SwapHoldLog.objects.create(claim=alice_claim, candidate_ref="MSFT")
        SwapHoldLog.objects.create(claim=bob_claim, candidate_ref="NVDA")
        resp = client_alice.get("/api/v1/monitor/swap-hold-logs/")
        data = resp.data["results"] if isinstance(resp.data, dict) and "results" in resp.data else resp.data
        assert len(data) == 1
        assert data[0]["candidate_ref"] == "MSFT"


# ── swap-hold-logs 성과(C-BE) ──────────────────────────────────────────


@pytest.mark.django_db
class TestSwapHoldLogPerformance:
    """C-BE — hold_performance_pct/candidate_performance_pct 서버 계산(스냅샷 시점 대비
    DailyPrice 종가 변화). latest_close(scenario.py) 재사용, 새 가격 API 없음."""

    def _seed_prices(self, symbol, rows):
        from packages.shared.stocks.models import DailyPrice, Stock

        stock, _ = Stock.objects.get_or_create(symbol=symbol)
        DailyPrice.objects.bulk_create([
            DailyPrice(
                stock=stock, date=d,
                open_price=close, high_price=close, low_price=close,
                close_price=close, volume=1,
            )
            for d, close in rows
        ])
        return stock

    def test_hold_and_candidate_performance_computed(self, client_alice, alice_claim):
        self._seed_prices("AAPL", [(date(2026, 8, 1), 100), (date(2026, 8, 20), 110)])
        self._seed_prices("MSFT", [(date(2026, 8, 1), 200), (date(2026, 8, 20), 190)])

        log = SwapHoldLog.objects.create(claim=alice_claim, candidate_ref="MSFT")
        SwapHoldLog.objects.filter(pk=log.pk).update(
            held_at=timezone.make_aware(datetime(2026, 8, 1, 12, 0))
        )

        resp = client_alice.get("/api/v1/monitor/swap-hold-logs/")
        data = resp.data["results"] if isinstance(resp.data, dict) and "results" in resp.data else resp.data
        assert resp.status_code == 200
        row = data[0]
        assert row["hold_performance_pct"] == pytest.approx(10.0)  # (110-100)/100*100
        assert row["candidate_performance_pct"] == pytest.approx(-5.0)  # (190-200)/200*100

    def test_null_when_no_candidate_ref(self, client_alice, alice_claim):
        self._seed_prices("AAPL", [(date(2026, 8, 1), 100), (date(2026, 8, 20), 110)])
        log = SwapHoldLog.objects.create(claim=alice_claim)
        SwapHoldLog.objects.filter(pk=log.pk).update(
            held_at=timezone.make_aware(datetime(2026, 8, 1, 12, 0))
        )

        resp = client_alice.get("/api/v1/monitor/swap-hold-logs/")
        data = resp.data["results"] if isinstance(resp.data, dict) and "results" in resp.data else resp.data
        row = data[0]
        assert row["hold_performance_pct"] == pytest.approx(10.0)
        assert row["candidate_performance_pct"] is None

    def test_null_when_no_price_data(self, client_alice, alice_claim):
        # AAPL·MSFT 모두 DailyPrice 없음 — anchor/current 조회 실패 → null-safe
        log = SwapHoldLog.objects.create(claim=alice_claim, candidate_ref="MSFT")
        resp = client_alice.get("/api/v1/monitor/swap-hold-logs/")
        data = resp.data["results"] if isinstance(resp.data, dict) and "results" in resp.data else resp.data
        row = data[0]
        assert row["hold_performance_pct"] is None
        assert row["candidate_performance_pct"] is None


# ── decision-journal-entries ─────────────────────────────────────────────


@pytest.mark.django_db
class TestDecisionJournalEntryAPI:
    def test_unauthenticated_rejected(self):
        resp = APIClient().get("/api/v1/monitor/decision-journal-entries/")
        assert resp.status_code in (401, 403)

    def test_create_close_entry(self, client_alice, alice_claim):
        resp = client_alice.post(
            "/api/v1/monitor/decision-journal-entries/",
            {"claim": str(alice_claim.id), "kind": "close", "sentence": "목표 도달로 익절 마감."},
        )
        assert resp.status_code == 201, resp.data
        assert resp.data["kind"] == "close"
        assert DecisionJournalEntry.objects.filter(claim=alice_claim).count() == 1

    def test_create_recommit_entry_no_min_length(self, client_alice, alice_claim):
        # ADR §6: 최소 글자수 등 검증 없음 — 한 글자도 통과.
        resp = client_alice.post(
            "/api/v1/monitor/decision-journal-entries/",
            {"claim": str(alice_claim.id), "kind": "recommit", "sentence": "ㅇ"},
        )
        assert resp.status_code == 201, resp.data

    def test_invalid_kind_rejected(self, client_alice, alice_claim):
        resp = client_alice.post(
            "/api/v1/monitor/decision-journal-entries/",
            {"claim": str(alice_claim.id), "kind": "bogus", "sentence": "x"},
        )
        assert resp.status_code == 400

    def test_create_for_other_user_claim_forbidden(self, client_bob, alice_claim):
        resp = client_bob.post(
            "/api/v1/monitor/decision-journal-entries/",
            {"claim": str(alice_claim.id), "kind": "hold", "sentence": "보류"},
        )
        assert resp.status_code == 403

    def test_list_filtered_by_claim(self, client_alice, alice_claim, alice_monitor):
        other_claim = Claim.objects.create(monitor=alice_monitor, assertion="다른 주장")
        DecisionJournalEntry.objects.create(claim=alice_claim, kind="hold", sentence="a")
        DecisionJournalEntry.objects.create(claim=other_claim, kind="hold", sentence="b")
        resp = client_alice.get(
            f"/api/v1/monitor/decision-journal-entries/?claim={alice_claim.id}"
        )
        data = resp.data["results"] if isinstance(resp.data, dict) and "results" in resp.data else resp.data
        assert len(data) == 1
        assert data[0]["sentence"] == "a"
