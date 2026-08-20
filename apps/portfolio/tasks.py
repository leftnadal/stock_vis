"""Slice 19c — 포트폴리오 자산 스냅샷 nightly Celery 태스크.

엔진 실행 시 upsert(`snapshot.upsert_snapshot`)와 **이중 기록**. 태스크 본체는 서비스
함수를 얇게 호출 → 수동/엔진 경로와 로직 공유. 멱등(update_or_create(user, date)).

beat 등록은 DB PeriodicTask가 유일한 진실(공통버그 #28) — config dict 스케줄 금지.
등록 커맨드 = `sync_portfolio_snapshot_beat`(멱등). macOS fork 안전(버그 #25).
"""

import logging

from celery import shared_task

from packages.shared.api_request.providers.fmp.client import FMPClient
from packages.shared.stocks.services.analyst_signal_writer import capture_symbols

logger = logging.getLogger(__name__)


def _coach_universe() -> list[str]:
    """수집 대상 유니버스 = **UserGoal 보유 유저**의 WalletHolding ∪ WatchlistItem 실심볼.

    스코프 = nightly advisory·snapshot 태스크와 동일 좌표(`portfolio_goal__isnull=False`).
    글로벌 무필터(SFI-I1 원안)는 타 유저 데이터 유입 결함이었음(D-I1b-1 / common-bugs
    GLOBAL-SCOPE-TASK). 목표 유저 0명이면 빈 리스트(안전 종료).
    """
    from django.contrib.auth import get_user_model

    from apps.portfolio.models import WalletHolding
    from packages.shared.users.models import WatchlistItem

    User = get_user_model()
    goal_users = User.objects.filter(portfolio_goal__isnull=False)
    wh = WalletHolding.objects.filter(wallet__user__in=goal_users).values_list(
        "stock__symbol", flat=True
    )
    wl = WatchlistItem.objects.filter(watchlist__user__in=goal_users).values_list(
        "stock__symbol", flat=True
    )
    return sorted({s.upper() for s in list(wh) + list(wl) if s})


@shared_task(bind=True, max_retries=3, name="apps.portfolio.tasks.snapshot_all_users")
def snapshot_all_users(self):
    """목표를 가진 전 사용자의 오늘 자산 스냅샷 upsert(멱등·nightly).

    idempotent: PortfolioSnapshot.update_or_create(user, date=today) → 재실행 안전.
    한 사용자 실패가 배치 전체를 막지 않도록 개별 try(로그 후 계속).
    """
    from django.contrib.auth import get_user_model
    from django.db import connections

    connections.close_all()  # fork 후 DB 연결 정리 (macOS SIGSEGV, 버그 #25)

    from apps.portfolio.services.snapshot import upsert_snapshot

    User = get_user_model()
    users = User.objects.filter(portfolio_goal__isnull=False)  # UserGoal 있는 사용자만
    ok, fail = 0, 0
    for user in users:
        try:
            upsert_snapshot(user)
            ok += 1
        except Exception:  # noqa: BLE001 — 개별 실패 격리
            logger.exception("snapshot 실패 user=%s", getattr(user, "pk", "?"))
            fail += 1
    logger.info("snapshot_all_users: ok=%d fail=%d", ok, fail)
    return {"ok": ok, "fail": fail}


@shared_task(bind=True, max_retries=3, name="apps.portfolio.tasks.advisory_all_users")
def advisory_all_users(self):
    """목표를 가진 전 사용자의 일 1회 권유 자동 기록(`trigger=auto`·nightly, SLICE20A).

    run_advisory가 스냅샷 upsert(멱등)까지 담당 → snapshot nightly와 이중 안전.
    사후분석은 auto 표본만 쓰므로 nightly가 시계열 원장을 형성한다(D2).
    개별 사용자 실패 격리(로그 후 계속).
    """
    from django.contrib.auth import get_user_model
    from django.db import connections

    connections.close_all()  # fork 후 DB 연결 정리 (macOS SIGSEGV, 버그 #25)

    from apps.portfolio.services.advisory_engine import run_advisory

    User = get_user_model()
    users = User.objects.filter(portfolio_goal__isnull=False)  # UserGoal 있는 사용자만
    ok, fail = 0, 0
    for user in users:
        try:
            run_advisory(user, trigger="auto")
            ok += 1
        except Exception:  # noqa: BLE001 — 개별 실패 격리
            logger.exception("advisory 실패 user=%s", getattr(user, "pk", "?"))
            fail += 1
    logger.info("advisory_all_users: ok=%d fail=%d", ok, fail)
    return {"ok": ok, "fail": fail}


@shared_task(
    bind=True,
    max_retries=3,
    name="apps.portfolio.tasks.ingest_analyst_signals",
)
def ingest_analyst_signals(self):
    """coach 유니버스 forward 신호 nightly 수집 (SFI-I1 Part 3).

    유니버스(보유∪관심) 순회 → AnalystSignalSnapshot append + Stock.analyst_* 미러.
    심볼별 격리(1종목 실패 계속) + 카운터 소진 시 중단(capture_symbols). self-throttle는
    FMPClient._make_request가 담당(단일 client 인스턴스 재사용). estimates 무접촉(D-I1-4).

    ★ append 전용(D-I1-2)이라 재실행 = 신규 행 — 멱등 아님(의도된 시계열). beat 미등록(병진).
    """
    from django.conf import settings
    from django.db import connections

    connections.close_all()  # fork 후 DB 연결 정리 (macOS SIGSEGV, 버그 #25)

    symbols = _coach_universe()
    if not symbols:
        logger.info("ingest_analyst_signals: 유니버스 비어있음 — skip")
        return {"captured": 0, "failed": 0, "skipped": 0, "universe": 0}

    client = FMPClient(api_key=settings.FMP_API_KEY)
    summary = capture_symbols(client, symbols)
    summary["universe"] = len(symbols)
    logger.info("ingest_analyst_signals: %s", summary)
    return summary


@shared_task(
    bind=True,
    max_retries=3,
    name="apps.portfolio.tasks.ingest_stock_splits",
)
def ingest_stock_splits(self):
    """coach 유니버스 액면분할 이력 nightly 수집 (I3-SPLIT-GUARD, D-SPLIT-1).

    유니버스(보유∪관심, `_coach_universe` 재사용) 순회 → FMP /stable/splits →
    StockSplit **append/skip**(unique (stock,date) 기준 get_or_create, 기존 행 무수정).
    채점(analyst_scoring)이 예측~만기 구간 분할을 unscoreable:corporate_action 처리하는 원료.
    심볼별 격리(1종목 실패 계속). beat 미등록(병진 수동, sync_stock_splits_beat).
    """
    from datetime import date as _date

    from django.conf import settings
    from django.db import connections

    connections.close_all()  # fork 후 DB 연결 정리 (macOS SIGSEGV, 버그 #25)

    from packages.shared.stocks.models import Stock, StockSplit

    symbols = _coach_universe()
    if not symbols:
        logger.info("ingest_stock_splits: 유니버스 비어있음 — skip")
        return {"symbols": 0, "fetched": 0, "created": 0, "skipped": 0, "errors": {}}

    client = FMPClient(api_key=settings.FMP_API_KEY)
    fetched = created = skipped = 0
    errors: dict = {}
    for sym in symbols:
        try:
            rows = client.get_stock_splits(sym)
            stock = Stock.objects.filter(symbol=sym.upper()).first()
            if stock is None:
                skipped += len(rows)
                continue
            for r in rows:
                fetched += 1
                try:
                    d = _date.fromisoformat(str(r["date"])[:10])
                except (KeyError, ValueError, TypeError):
                    skipped += 1
                    continue
                _, was_created = StockSplit.objects.get_or_create(
                    stock=stock,
                    date=d,
                    defaults={
                        "numerator": r.get("numerator"),
                        "denominator": r.get("denominator"),
                        "split_type": r.get("splitType") or "",
                        "source": "fmp",
                    },
                )
                if was_created:
                    created += 1
                else:
                    skipped += 1  # 기존 행 무수정(append-only)
        except Exception as e:  # noqa: BLE001 — 심볼별 격리
            logger.exception("ingest_stock_splits 실패 %s", sym)
            errors[sym] = str(e)

    summary = {
        "symbols": len(symbols),
        "fetched": fetched,
        "created": created,
        "skipped": skipped,
        "errors": errors,
    }
    logger.info("ingest_stock_splits: %s", summary)
    return summary
