"""
RelationPairSnapshot 백필 관리 명령 (해자 궤적 적립 — 옵션3).

현재 RelationConfidence 전수를 정규화 쌍 단위로 집계해 period=today 스냅샷 1세트를 생성한다.

★ 이것은 "오늘 단면 1점"이다. 과거 궤적은 복원되지 않는다(원천도 현재 단면만 보관).
  궤적은 forward-only로 다음 배치(매일 11:30 EST aggregate_relation_pairs_task)부터 적립된다.

사용:
    python manage.py backfill_pair_relevance            # 오늘 단면 적립
    python manage.py backfill_pair_relevance --dry-run  # 미적용, 쌍 수 + opp/risk 분포만 출력
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.chain_sight.services.pair_aggregation import aggregate_relation_pairs


def _histogram(values, bins=10):
    """[0,1] 값 리스트 → 10구간 히스토그램 라인."""
    counts = [0] * bins
    for v in values:
        idx = min(int(v * bins), bins - 1)
        counts[idx] += 1
    lines = []
    for i, c in enumerate(counts):
        lo, hi = i / bins, (i + 1) / bins
        bar = "█" * c if c <= 60 else "█" * 60 + f"…({c})"
        lines.append(f"  [{lo:.1f}–{hi:.1f}) {c:>6} {bar}")
    return "\n".join(lines)


class Command(BaseCommand):
    help = "RelationConfidence를 쌍 단위로 집계해 오늘(period=today) RelationPairSnapshot 적립."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="쓰지 않고 생성될 쌍 수 + opp/risk 분포만 출력.",
        )

    def handle(self, *args, **options):
        period = timezone.now().date()
        dry_run = options["dry_run"]

        self.stdout.write(
            self.style.WARNING(
                "⚠ 이것은 오늘 단면 1점이다. 과거 궤적은 복원되지 않는다. "
                "궤적은 forward-only로 다음 배치부터 적립된다."
            )
        )

        result = aggregate_relation_pairs(period=period, dry_run=dry_run)

        if dry_run:
            opp = result["opp_values"]
            risk = result["risk_values"]
            opp_pos = [v for v in opp if v > 0]
            risk_pos = [v for v in risk if v > 0]
            self.stdout.write(f"[DRY-RUN] period={period} 쌍 수: {result['pairs']}")
            self.stdout.write(f"  relevance_opp > 0: {len(opp_pos)}개")
            self.stdout.write(_histogram(opp))
            self.stdout.write(f"  relevance_risk > 0: {len(risk_pos)}개")
            self.stdout.write(_histogram(risk))
            self.stdout.write(self.style.SUCCESS("[DRY-RUN] 쓰기 없음."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"period={period} 적립 완료: "
                    f"pairs={result['pairs']} created={result['created']} "
                    f"updated={result['updated']}"
                )
            )
