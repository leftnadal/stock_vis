"""
sync_non_sp500_held_news_category — 비SP500 보유종목 뉴스 카테고리 멱등 동기화 (NEWS-P0-FIX T1/S3).

배경(RECON-NEWS-P0):
    News 유니버스는 3경로로 구성된다 — orchestrator(SP500 503전량) /
    collect_daily_news(MarketMover 상위 20) / category(custom CSV, 관리자 수기 등록).
    보유 종목 중 TLN·IONQ·IREN은 SP500 미편입이라 orchestrator에서 빠지고,
    MarketMover 상위 20에도 항상 들지 않아 뉴스 수집 사각지대(NewsEntity 0)에 놓인다.
    GEV·GOOGL·PLTR은 SP500 편입 종목이라 orchestrator가 이미 커버 — 이 커맨드의
    등재 대상에서 제외한다.

동작:
    NewsCollectionCategory(category_type="custom", name=CATEGORY_NAME) 1건을
    get_or_create 하고, value(CSV)에 TARGET_SYMBOLS 를 합집합(union)으로 보장한다.
    기존에 관리자가 수기로 추가한 다른 심볼은 보존한다(제거하지 않음) — 순수 추가(additive).
    재실행해도 동일 결과(멱등).

사용:
    python manage.py sync_non_sp500_held_news_category            # dry-run(기본, 쓰기 없음)
    python manage.py sync_non_sp500_held_news_category --apply    # 실제 반영
"""

from django.core.management.base import BaseCommand

CATEGORY_NAME = "비SP500 보유종목"
CATEGORY_TYPE = "custom"
# GEV·GOOGL·PLTR 제외 — SP500 편입 종목이라 collect_sp500_news_fmp_orchestrator가 이미 커버.
TARGET_SYMBOLS = ["IONQ", "IREN", "TLN"]


class Command(BaseCommand):
    help = (
        "NewsCollectionCategory(custom)에 비SP500 보유종목(IONQ·IREN·TLN)을 멱등 등재한다. "
        "기본은 dry-run — --apply 로 실제 반영."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="실제 반영 수행. 기본은 dry-run(계획만 출력, 쓰기 없음).",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]

        # import는 handle 안에서(관례 — register_news_av_beat.py와 동일 패턴)
        from services.news.models import NewsCollectionCategory

        existing = NewsCollectionCategory.objects.filter(
            category_type=CATEGORY_TYPE, name=CATEGORY_NAME
        ).first()

        if existing is None:
            current_symbols: list[str] = []
        else:
            current_symbols = [
                s.strip().upper() for s in existing.value.split(",") if s.strip()
            ]

        missing = [s for s in TARGET_SYMBOLS if s not in current_symbols]
        merged_symbols = current_symbols + missing  # additive, 기존 순서·항목 보존
        merged_value = ",".join(merged_symbols)

        if not apply_changes:
            if existing is None:
                self.stdout.write(
                    f"[dry-run] would create category '{CATEGORY_NAME}' "
                    f"(type={CATEGORY_TYPE}) value='{merged_value}'"
                )
            elif missing:
                self.stdout.write(
                    f"[dry-run] would update category '{CATEGORY_NAME}' "
                    f"(id={existing.id}) value: '{existing.value}' -> '{merged_value}' "
                    f"(추가: {missing})"
                )
            else:
                self.stdout.write(
                    f"[dry-run] category '{CATEGORY_NAME}' (id={existing.id}) already "
                    f"contains {TARGET_SYMBOLS} — no-op"
                )
            self.stdout.write(self.style.WARNING("dry-run: 아무것도 반영하지 않음."))
            return

        if existing is None:
            obj = NewsCollectionCategory.objects.create(
                name=CATEGORY_NAME,
                category_type=CATEGORY_TYPE,
                value=merged_value,
                is_active=True,
                priority="medium",
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"created: '{obj.name}' (id={obj.id}) value='{obj.value}'"
                )
            )
        elif missing:
            existing.value = merged_value
            existing.save(update_fields=["value", "updated_at"])
            self.stdout.write(
                self.style.SUCCESS(
                    f"updated: '{existing.name}' (id={existing.id}) "
                    f"value='{existing.value}' (추가: {missing})"
                )
            )
        else:
            self.stdout.write(
                f"no-op: '{existing.name}' (id={existing.id}) already contains "
                f"{TARGET_SYMBOLS}"
            )
