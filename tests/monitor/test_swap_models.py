"""SwapHoldLog / DecisionJournalEntry 모델 검증 (RECON-SWAP-0813 PART 3-BE)."""
from datetime import datetime, timedelta

import pytest
from django.utils import timezone

from apps.monitor.models import Claim, DecisionJournalEntry, SwapHoldLog

# D-FIXTURE-FIXED-BASE 준수 — 고정 base(now 앵커 금지).
_BASE = timezone.make_aware(datetime(2026, 8, 10, 12, 0))


@pytest.fixture
def claim(monitor):
    return Claim.objects.create(monitor=monitor, assertion="애플 강세 지속")


@pytest.mark.django_db
class TestSwapHoldLogModel:
    def test_create_minimal(self, claim):
        log = SwapHoldLog.objects.create(claim=claim, candidate_ref="MSFT")
        assert log.candidate_ref == "MSFT"
        assert log.note == ""
        assert log.held_at is not None
        assert claim.hold_logs.count() == 1

    def test_candidate_ref_and_note_optional(self, claim):
        log = SwapHoldLog.objects.create(claim=claim)
        assert log.candidate_ref is None
        assert log.note == ""

    def test_count_and_span_reconstructed_from_log(self, claim):
        # 별도 카운터 필드 없음 — 횟수/누적일수는 로그 집계로 재구성.
        t1 = _BASE - timedelta(days=10)
        t2 = _BASE - timedelta(days=3)
        t3 = _BASE
        for t in (t1, t2, t3):
            log = SwapHoldLog.objects.create(claim=claim, candidate_ref="MSFT")
            SwapHoldLog.objects.filter(pk=log.pk).update(held_at=t)

        logs = list(claim.hold_logs.order_by("held_at"))
        assert len(logs) == 3  # 횟수
        span_days = (logs[-1].held_at - logs[0].held_at).days
        assert span_days == 10  # 누적 일수(최초~최근)

    def test_ordering_desc_by_held_at(self, claim):
        older = SwapHoldLog.objects.create(claim=claim, candidate_ref="A")
        SwapHoldLog.objects.filter(pk=older.pk).update(held_at=_BASE - timedelta(days=5))
        newer = SwapHoldLog.objects.create(claim=claim, candidate_ref="B")
        SwapHoldLog.objects.filter(pk=newer.pk).update(held_at=_BASE)
        ids = list(claim.hold_logs.values_list("id", flat=True))
        assert ids == [newer.id, older.id]

    def test_claim_delete_cascades_hold_logs(self, claim):
        SwapHoldLog.objects.create(claim=claim, candidate_ref="MSFT")
        claim.delete()
        assert SwapHoldLog.objects.count() == 0


@pytest.mark.django_db
class TestDecisionJournalEntryModel:
    @pytest.mark.parametrize("kind", ["close", "recommit", "hold"])
    def test_create_each_kind(self, claim, kind):
        entry = DecisionJournalEntry.objects.create(
            claim=claim, kind=kind, sentence="목표 도달로 익절 마감."
        )
        entry.full_clean()  # 통과해야 함(sentence 품질 검증 없음)
        assert entry.kind == kind
        assert claim.journal_entries.count() == 1

    def test_no_min_length_validator_on_sentence(self, claim):
        # ADR §6: 입력 품질 검증(최소 글자수 등) 금지 — 한 글자도 통과해야 함.
        entry = DecisionJournalEntry(claim=claim, kind="hold", sentence="ㅇ")
        entry.full_clean()  # 예외 없이 통과

    def test_claim_delete_cascades_journal_entries(self, claim):
        DecisionJournalEntry.objects.create(claim=claim, kind="close", sentence="마감")
        claim.delete()
        assert DecisionJournalEntry.objects.count() == 0

    def test_ordering_desc_by_created_at(self, claim):
        e1 = DecisionJournalEntry.objects.create(claim=claim, kind="hold", sentence="첫 보류")
        DecisionJournalEntry.objects.filter(pk=e1.pk).update(
            created_at=_BASE - timedelta(days=1)
        )
        e2 = DecisionJournalEntry.objects.create(claim=claim, kind="hold", sentence="둘째 보류")
        DecisionJournalEntry.objects.filter(pk=e2.pk).update(created_at=_BASE)
        ids = list(claim.journal_entries.values_list("id", flat=True))
        assert ids == [e2.id, e1.id]
