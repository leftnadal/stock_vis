"""Slice 19c — 포트폴리오 자산 스냅샷 nightly Celery 태스크.

엔진 실행 시 upsert(`snapshot.upsert_snapshot`)와 **이중 기록**. 태스크 본체는 서비스
함수를 얇게 호출 → 수동/엔진 경로와 로직 공유. 멱등(update_or_create(user, date)).

beat 등록은 DB PeriodicTask가 유일한 진실(공통버그 #28) — config dict 스케줄 금지.
등록 커맨드 = `sync_portfolio_snapshot_beat`(멱등). macOS fork 안전(버그 #25).
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


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
