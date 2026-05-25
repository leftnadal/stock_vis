"""UnmatchedCompanyQueue 1차 청소 + 재매칭 (2026-05-26 C 옵션).

1) 블록리스트(BLOCKED_NAMES)에 매칭되는 pending → 'not_public' or 'skipped'
2) 신규 CompanyAlias 적용해서 pending 항목 재매칭 시도 → 매칭되면 'matched'
3) 통계 출력

Usage:
    python manage.py reprocess_unmatched_queue
    python manage.py reprocess_unmatched_queue --dry-run
    python manage.py reprocess_unmatched_queue --limit 200
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from sec_pipeline.models import UnmatchedCompanyQueue
from sec_pipeline.ticker_matcher import BLOCKED_NAMES, TickerMatcher


class Command(BaseCommand):
    help = "UnmatchedCompanyQueue 일괄 청소 + 재매칭 (블록리스트 + alias 갱신 반영)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--limit", type=int, default=0, help="최대 처리 건수 (0=전체)")

    def handle(self, *args, **opts):
        dry_run = opts["dry_run"]
        limit = opts["limit"] or 0

        qs = UnmatchedCompanyQueue.objects.filter(status="pending").order_by("-occurrence_count")
        total_pending = qs.count()
        if limit > 0:
            qs = qs[:limit]
        self.stdout.write(f"pending 큐 항목 {total_pending}건 중 {qs.count() if limit else total_pending}건 처리")

        matcher = TickerMatcher()
        stats = {
            "blocked": 0,
            "matched": 0,
            "still_unmatched": 0,
        }

        for entry in qs:
            raw = entry.raw_company_name.strip()

            # 1) 블록리스트
            if raw.lower() in BLOCKED_NAMES:
                stats["blocked"] += 1
                if not dry_run:
                    entry.status = "not_public"
                    entry.save(update_fields=["status", "updated_at"])
                self.stdout.write(f"  [BLOCK] {raw} → not_public (occ={entry.occurrence_count})")
                continue

            # 2) 재매칭 시도 (alias + exact + fuzzy)
            sector_hint = (entry.source_sectors or [""])[0] if entry.source_sectors else ""
            ticker, method = matcher.match(raw, sector_hint)

            if ticker:
                stats["matched"] += 1
                if not dry_run:
                    entry.status = "matched"
                    entry.resolved_ticker = ticker
                    entry.save(update_fields=["status", "resolved_ticker", "updated_at"])
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  [MATCH] {raw} → {ticker} ({method}, occ={entry.occurrence_count})"
                    )
                )
            else:
                stats["still_unmatched"] += 1

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"완료 — blocked={stats['blocked']} matched={stats['matched']} "
            f"still_unmatched={stats['still_unmatched']}"
        ))
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN: DB 변경 없음"))
