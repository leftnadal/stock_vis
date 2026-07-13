"""backfill_broad_news — Slice C-N: 모집단 구간 과거 뉴스 소급 백필 (L3 그라운딩 재료).

소속: services/news/management/commands (backfill_spy_eod A-PREP 선례 재사용 — 뉴스판).
역할: analog 카드 L3(그날의 맥락)의 그라운딩 재료인 과거 시장 뉴스를, AV NEWS_SENTIMENT
  broad 소스로 모집단 미커버 구간(~2023-08 ~ 2025-12)에 소급 백필한다. 기존 라이브
  broad 수집(collect_av_broad_news)과 **동일 save 경로**(NewsAggregatorService: dedup +
  _save_articles url upsert)를 재사용하므로 저장 형태가 라이브와 동형이고 멱등이다.
의존: services.news.providers.alphavantage.AlphaVantageNewsProvider (shared 뉴스 provider,
  time_from/time_to 과거 창 조회), services.news.services.aggregator.NewsAggregatorService.

왜 AV인가 (STEP 0 GN 실측 2026-07-13):
  - FMP 뉴스: `from/to` 날짜 파라미터 = 402 프리미엄 + 페이지 캡(page~200 400) → 과거 도달 불가.
  - AV NEWS_SENTIMENT: time_from/time_to 과거 창 실측 2023-09까지 도달, 모집단 전 구간 커버.
  - 제약: AV 무료 티어 25 req/day, 1 req/s 스로틀 → 전량 백필은 병진 수일(--max-requests 배치).

규약:
  - **dry-run 기본**: 인자 없이 실행 = 무쓰기 산정(윈도우 수·예상 요청·소요일). 쓰기는 `--commit`.
  - 멱등: NewsArticle.url unique upsert(_save_articles) → 창 겹침·재실행 중복 0.
  - 재개 가능: `--skip-covered`(기본 on) — 이미 충분히 커버된 창은 AV 요청 없이 건너뜀.
  - 외부는 AV provider(shared 뉴스 경유)만. 기존 라이브 파이프라인 무변경(가산만).
  - NewsArticle은 나이 purge 없음(archive_old_articles = soft delete is_archived) → 백필분 영속.
    ※ C-L3 그라운딩 쿼리는 is_archived=True 포함해야 함(6개월+ 과거분은 아카이브 플래그).

사용:
    python manage.py backfill_broad_news                      # dry-run: 윈도우·요청 산정
    python manage.py backfill_broad_news --commit --max-requests 20   # 실쓰기(운영자 승인 후, 1일분)
    python manage.py backfill_broad_news --from 2023-08-07 --to 2025-12-05

⚠️ prod 쓰기 + AV 요청 소비 = 운영자 수동(--commit). 세션은 dry-run 산정 + 소량 검증만.
"""
from __future__ import annotations

import time
from datetime import date, datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

# 모집단 미커버 기본 구간(STEP 0 실측: 모집단 683 = 2023-08-07~2026-04-24,
#   NewsArticle 라이브 커버 시작 2025-12-08 → 미커버 587일 = 아래 범위).
DEFAULT_FROM = date(2023, 8, 7)
DEFAULT_TO = date(2025, 12, 5)
DEFAULT_WINDOW_DAYS = 7      # 창당 볼륨 ≤ AV limit(1000) 목표(실측 ~34~158/일; 7일 peak≈1100 saturat 경고)
DEFAULT_LIMIT = 1000         # AV 무료 상한
DEFAULT_MAX_REQUESTS = 20    # 실행당 AV 요청 예산(25/day 캡 아래, 병진 배치)
# 커버 판정 = 창 내 기사 수 ≥ window_days × 이 값. 플랫 임계는 인접 창 spillover(경계일
#   소수 기사)를 "커버됨"으로 오판해 실제 공백 창을 skip → 갭. 일당 비례로 spillover 격리.
COVERED_PER_DAY = 3


class Command(BaseCommand):
    help = "Backfill 과거 broad 시장 뉴스 via AV NEWS_SENTIMENT (idempotent, dry-run 기본)."

    def add_arguments(self, parser):
        parser.add_argument("--from", dest="from_date", type=str, default=None,
                            help="YYYY-MM-DD (기본: 2023-08-07 = 모집단 미커버 시작)")
        parser.add_argument("--to", dest="to_date", type=str, default=None,
                            help="YYYY-MM-DD (기본: 2025-12-05 = 라이브 커버 직전)")
        parser.add_argument("--window-days", type=int, default=DEFAULT_WINDOW_DAYS,
                            help=f"창 길이(일). 기본 {DEFAULT_WINDOW_DAYS}. 볼륨 큰 구간은 줄여 saturation 회피")
        parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                            help=f"창당 AV 기사 상한(무료 1000). 기본 {DEFAULT_LIMIT}")
        parser.add_argument("--max-requests", type=int, default=DEFAULT_MAX_REQUESTS,
                            help=f"실행당 AV 요청 예산(25/day 캡 아래). 기본 {DEFAULT_MAX_REQUESTS}")
        parser.add_argument("--sort", type=str, default="EARLIEST",
                            choices=["EARLIEST", "LATEST", "RELEVANCE"])
        parser.add_argument("--no-skip-covered", action="store_true",
                            help="이미 커버된 창도 재조회(기본은 skip으로 재개·예산 절약)")
        parser.add_argument("--commit", action="store_true",
                            help="실제 DB 쓰기 + AV 요청 소비(미지정 시 dry-run 산정만)")

    def handle(self, *args, **options):
        from_date = self._parse(options["from_date"]) or DEFAULT_FROM
        to_date = self._parse(options["to_date"]) or DEFAULT_TO
        if from_date > to_date:
            raise CommandError(f"--from({from_date}) > --to({to_date})")

        window_days = options["window_days"]
        limit = options["limit"]
        max_requests = options["max_requests"]
        sort = options["sort"]
        skip_covered = not options["no_skip_covered"]
        commit = options["commit"]

        windows = self._windows(from_date, to_date, window_days)
        self.stdout.write(
            f"[backfill_broad_news] 구간 {from_date}~{to_date} · 창 {window_days}일 · "
            f"총 {len(windows)}창 · limit {limit} · sort {sort} · "
            f"{'COMMIT' if commit else 'DRY-RUN'}"
        )

        # skip-covered: 창별 기존 커버 산정(무쓰기, AV 요청 0). 임계 = 창일수 × 일당.
        covered_threshold = max(1, window_days * COVERED_PER_DAY)
        pending = []
        skipped_covered = 0
        for w_start, w_end in windows:
            if skip_covered and self._window_count(w_start, w_end) >= covered_threshold:
                skipped_covered += 1
                continue
            pending.append((w_start, w_end))

        est_requests = min(len(pending), max_requests)
        self.stdout.write(
            f"  커버됨 skip: {skipped_covered}창 · 백필 대상: {len(pending)}창 · "
            f"이번 실행 요청 예산: {est_requests} (max-requests {max_requests})"
        )
        remaining = max(0, len(pending) - max_requests)
        if remaining:
            days_needed = -(-len(pending) // 25)  # ceil, AV 25/day
            self.stdout.write(
                f"  ⚠️ 잔여 {remaining}창 = 이후 실행 필요(전량 ≈ {days_needed}일 @ 25 req/day)"
            )

        if not commit:
            self.stdout.write(self.style.WARNING(
                "  DRY-RUN: 쓰기·AV 요청 0. 실제 백필은 --commit(운영자 승인)."
            ))
            self._print_window_preview(pending[:est_requests])
            return

        # ── COMMIT: provider·aggregator 재사용(라이브와 동일 save 경로) ──
        key = getattr(settings, "ALPHA_VANTAGE_API_KEY", "")
        if not key:
            raise CommandError("ALPHA_VANTAGE_API_KEY 미설정 — 백필 불가")

        from services.news.providers.alphavantage import (
            AlphaVantageNewsProvider,
            RateLimitExceeded,
        )
        from services.news.services.aggregator import NewsAggregatorService

        provider = AlphaVantageNewsProvider(key)
        aggregator = NewsAggregatorService()

        totals = {"fetched": 0, "unique": 0, "saved": 0, "updated": 0, "skipped": 0}
        saturated = []
        done = 0
        for w_start, w_end in pending[:max_requests]:
            try:
                fetched, unique, saved, updated, skipped = self._fetch_save(
                    provider, aggregator, w_start, w_end, limit, sort,
                )
            except RateLimitExceeded as exc:
                self.stdout.write(self.style.WARNING(
                    f"  AV 한도/스로틀 도달({exc}) — {done}창 처리 후 중단. 재실행으로 재개."
                ))
                break
            totals["fetched"] += fetched
            totals["unique"] += unique
            totals["saved"] += saved
            totals["updated"] += updated
            totals["skipped"] += skipped
            if fetched >= limit:
                saturated.append((w_start, w_end))
            self.stdout.write(
                f"  {w_start}~{w_end}: fetched {fetched} / saved {saved} / updated {updated}"
                + ("  ⚠️SATURATED(창 축소 재패스 필요)" if fetched >= limit else "")
            )
            done += 1

        self.stdout.write(self.style.SUCCESS(
            f"[완료] {done}창 · fetched {totals['fetched']} · saved {totals['saved']} · "
            f"updated {totals['updated']} · skipped {totals['skipped']}"
        ))
        if saturated:
            self.stdout.write(self.style.WARNING(
                f"  SATURATED {len(saturated)}창(볼륨>limit, 후속일 갭 위험) → "
                f"--window-days 축소 재패스 권장: {saturated[:5]}{' …' if len(saturated) > 5 else ''}"
            ))

    # ── helpers ──────────────────────────────────────────────
    @staticmethod
    def _parse(s):
        if not s:
            return None
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except ValueError as exc:
            raise CommandError(f"날짜 형식 오류(YYYY-MM-DD): {s}") from exc

    @staticmethod
    def _windows(from_date, to_date, window_days):
        out = []
        cur = from_date
        step = timedelta(days=window_days)
        while cur <= to_date:
            w_end = min(cur + step, to_date + timedelta(days=1))
            out.append((cur, w_end))
            cur = w_end
        return out

    @staticmethod
    def _window_count(w_start, w_end):
        from services.news.models import NewsArticle
        return NewsArticle.objects.filter(
            published_at__date__gte=w_start, published_at__date__lt=w_end,
        ).count()

    @staticmethod
    def _fetch_save(provider, aggregator, w_start, w_end, limit, sort):
        """라이브 collect_av_broad_news와 동일 체인: fetch → dedup → _save_articles(멱등)."""
        tf = datetime(w_start.year, w_start.month, w_start.day)
        tt = datetime(w_end.year, w_end.month, w_end.day)
        arts = provider.fetch_broad_news(time_from=tf, time_to=tt, limit=limit, sort=sort)
        unique = aggregator.deduplicator.deduplicate(arts)
        saved, updated, skipped = aggregator._save_articles(unique)
        time.sleep(1.0)  # AV 1 req/s 스로틀 예의(provider 자체 스로틀 보강)
        return len(arts), len(unique), saved, updated, skipped

    def _print_window_preview(self, pending):
        if not pending:
            self.stdout.write("  (백필 대상 창 없음 — 이미 전부 커버)")
            return
        self.stdout.write("  이번 실행 대상 창(미리보기):")
        for w_start, w_end in pending:
            self.stdout.write(f"    {w_start} ~ {w_end}")
