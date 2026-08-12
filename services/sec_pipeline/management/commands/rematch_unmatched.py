"""
기존 미매칭 SupplyChainEvidence를 재매칭.

1. 제네릭 용어 evidence는 삭제
2. 나머지 target_company=NULL에 TickerMatcher 재실행
3. 결과 리포트 출력

Usage:
    python manage.py rematch_unmatched
    python manage.py rematch_unmatched --dry-run
"""

import logging

from django.core.management.base import BaseCommand

from services.sec_pipeline.models import SupplyChainEvidence, UnmatchedCompanyQueue
from services.sec_pipeline.ticker_matcher import TickerMatcher
from services.sec_pipeline.validator_track_a import _is_generic_term

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "미매칭 SupplyChainEvidence 재매칭 (제네릭 제거 + TickerMatcher 재실행)"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        prefix = "[DRY RUN] " if dry_run else ""

        # v2 필터: rematch delete가 v1 원장을 건드리지 않도록 스코프(D-SECB-V2-COEXIST=B, v1 보존)
        unmatched = SupplyChainEvidence.objects.current().filter(target_company__isnull=True)
        total = unmatched.count()
        self.stdout.write(f"{prefix}미매칭 evidence: {total}개")

        # 1. 제네릭 용어 evidence 삭제
        generic_qs = [e for e in unmatched if _is_generic_term(e.target_company_name)]
        generic_count = len(generic_qs)
        if generic_qs and not dry_run:
            generic_pks = [e.pk for e in generic_qs]
            SupplyChainEvidence.objects.filter(pk__in=generic_pks).delete()
            # UnmatchedCompanyQueue에서도 정리
            generic_names = set(e.target_company_name for e in generic_qs)
            UnmatchedCompanyQueue.objects.filter(
                raw_company_name__in=generic_names
            ).update(status="not_company")
        self.stdout.write(f"{prefix}제네릭 용어 삭제: {generic_count}개")

        # 2. 나머지 미매칭에 TickerMatcher 재실행
        remaining = SupplyChainEvidence.objects.filter(target_company__isnull=True)
        remaining_count = remaining.count()
        self.stdout.write(f"{prefix}재매칭 대상: {remaining_count}개")

        if dry_run:
            # dry-run: 매칭 시뮬레이션
            matcher = TickerMatcher()
            would_match = 0
            for ev in remaining:
                ticker, method = matcher.match(
                    ev.target_company_name,
                    ev.source_company.sector if ev.source_company else "",
                )
                if ticker:
                    would_match += 1
                    self.stdout.write(
                        f'  WOULD MATCH: "{ev.target_company_name}" → {ticker} ({method})'
                    )
                else:
                    self.stdout.write(f'  STILL UNMATCHED: "{ev.target_company_name}"')
            self.stdout.write(
                self.style.SUCCESS(
                    f"{prefix}매칭 예상: {would_match}/{remaining_count}"
                )
            )
            return

        # 실제 매칭
        matcher = TickerMatcher()
        matched = 0
        for ev in remaining:
            doc = ev.source_document
            symbol = ev.source_company_id
            ticker, method = matcher.match_with_queue(
                ev.target_company_name, ev, doc, symbol
            )
            if ticker:
                matched += 1
                self.stdout.write(
                    f'  MATCHED: "{ev.target_company_name}" → {ticker} ({method})'
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"완료: 제네릭 제거 {generic_count}개, "
                f"재매칭 {matched}/{remaining_count}개, "
                f"총 처리 {generic_count + matched}/{total}개"
            )
        )
