"""교체 검토 최소 영속 모델 (RECON-SWAP-0813 PART 3-BE, v0).

SwapHoldLog = 사용자가 대결 화면에서 "보류"를 누른 이력. 보류 횟수·누적 일수는 이 로그를
집계해서 재구성한다 — 별도 카운터 필드는 만들지 않는다(단일 소스=로그, ADR §6).

DecisionJournalEntry = 마감/재커밋 실행 시 강제되는 1문장 일지(P-4 회고 재인용 대비).
sentence는 품질 검증(최소 글자수 등) 없음 — ADR §6 결정.

둘 다 additive 신규 테이블 — 기존 Claim 모델·데이터 무접촉. Claim 상태 전이(마감·재커밋)
자체는 여기서 다루지 않는다(기존 closure 경로 재사용, FE가 조립).
"""
import uuid

from django.db import models

from apps.monitor.models.monitor import Claim


class SwapHoldLog(models.Model):
    """교체 검토 "보류" 클릭 이력. 횟수/누적일수는 조회 시 이 로그에서 집계."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name="hold_logs")
    held_at = models.DateTimeField(auto_now_add=True, help_text="보류 클릭 시각")
    candidate_ref = models.CharField(
        max_length=20, null=True, blank=True, help_text="검토 대상 후보 종목 심볼(대문자)"
    )
    # 보류 시점 가격 스냅샷 — P-1 계기판 "양측 기간 성과·격차"를 진실하게 산출하기 위한 앵커.
    # null 허용(FE 미제공·가격 부재 시). 저장 시점 종가/현재가는 FE가 보유·후보 각각 전달.
    hold_price = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True,
        help_text="보류 시점 보유 종목 가격(성과 앵커)",
    )
    candidate_price = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True,
        help_text="보류 시점 후보 종목 가격(성과 앵커)",
    )
    note = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-held_at"]

    def __str__(self):
        return f"hold_log({self.candidate_ref}) @ {self.claim_id}"


class DecisionJournalEntry(models.Model):
    """마감/재커밋 시 강제되는 1문장 결정 일지. sentence 품질 검증 없음(ADR §6)."""

    class Kind(models.TextChoices):
        CLOSE = "close", "마감"
        RECOMMIT = "recommit", "재커밋"
        HOLD = "hold", "보류"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name="journal_entries")
    kind = models.CharField(max_length=8, choices=Kind.choices)
    sentence = models.TextField(help_text="결정 한 줄(검증 없음 — ADR §6)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"journal({self.kind}) @ {self.claim_id}"
