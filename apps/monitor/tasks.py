"""Monitor 평가 주기 Celery 태스크 (MON-P2-BEAT).

EOD 창(18:00~18:35 ET) 종료 후 refresh(ingest→evaluate)를 실행한다. beat 등록은
`sync_monitor_beat` 커맨드가 DB PeriodicTask에 멱등 등록(공통버그 #28) — config dict
스케줄 금지. 태스크 본체는 서비스 함수 `pipeline.refresh_monitors`를 얇게 호출(§3)
→ 수동 커맨드 `refresh_monitors`와 로직을 공유한다.
"""
import logging
from zoneinfo import ZoneInfo

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.db.models import Max
from django.utils import timezone

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")

# 신선도 가드 재시도: EOD 미도착 시 20분 후 재시도, 최대 2회(총 대기 ~40분 → EOD 지연 흡수).
RETRY_COUNTDOWN = 1200
MAX_RETRIES = 2


def et_today():
    """실행 시점의 미국 동부(ET) 달력일 = EODSignal.date 거래일 기준.

    프로젝트 TIME_ZONE=Asia/Seoul이라 timezone.localdate()는 Seoul 날짜를 준다
    (18:45 ET 시점엔 이미 +1일) → 거래일과 어긋남. ET 날짜를 명시 계산해 신선도 가드와
    as_of(ingest 범위·스냅샷 asof_date)를 EOD 거래일에 정합시킨다.
    """
    return timezone.now().astimezone(ET).date()


def latest_eod_date():
    """가장 최근 EODSignal.date (없으면 None). 신선도 가드 입력."""
    from packages.shared.stocks.models import EODSignal

    return EODSignal.objects.aggregate(m=Max("date"))["m"]


def is_eod_fresh(as_of, latest=None):
    """가장 최근 EODSignal이 as_of(ET 오늘)와 같은가 = 오늘 EOD 도착 여부 (순수 판정).

    latest 미지정 시 DB에서 조회. 오늘 데이터 없음 = 미도착(데이터 지연) 또는 휴장.
    """
    if latest is None:
        latest = latest_eod_date()
    return latest == as_of


@shared_task(bind=True, max_retries=MAX_RETRIES)
def refresh_monitors_task(self):
    """stock scope Monitor 전체 refresh(ingest→evaluate). 신선도 가드 + 재시도.

    본문 순서(§3): 신선도 가드(§4) → 서비스 함수 호출 → 결과 요약 로그.
    가드: 오늘(ET) EODSignal 미도착이면 20분 후 재시도(최대 2회). 최종 미도착 시
    경고 로그 후 skip — stale 데이터로 평가하지 않는다(휴장·데이터 지연 모두 이 경로 종결,
    휴장 캘린더 로직은 스코프 밖).
    """
    from apps.monitor.services.pipeline import refresh_monitors

    as_of = et_today()

    if not is_eod_fresh(as_of):
        try:
            # non-exhausted → Retry 예외 전파(워커가 재스케줄), exhausted → 아래 catch로 skip.
            self.retry(countdown=RETRY_COUNTDOWN)
        except MaxRetriesExceededError:
            logger.warning(
                "monitor refresh skip: 오늘(ET %s) EODSignal 미도착 — %d회 재시도 후 종결"
                " (휴장/데이터 지연)",
                as_of,
                MAX_RETRIES,
            )
            return {"status": "skipped_stale_eod", "as_of": as_of.isoformat()}

    results = refresh_monitors(as_of_date=as_of)
    ingested = sum(r.get("ingested", 0) for r in results)
    changed = sum(1 for r in results if r.get("state_changed"))
    alerts_created = sum(1 for r in results if r.get("alert_created"))
    new_close_ids = [r["monitor_id"] for r in results if r.get("newly_close_suggested")]

    # 다이제스트 이메일: 당일 전이 ≥1건 또는 마감 제안 신규 시에만(전이일 한정, best-effort).
    from apps.monitor.services.alerts import send_digest

    digest_res = send_digest(as_of, new_close_monitor_ids=new_close_ids)

    logger.info(
        "monitor refresh 완료: as_of=%s monitors=%d readings+=%d state_changed=%d "
        "alerts=%d close_suggest_new=%d digest_sent=%s",
        as_of,
        len(results),
        ingested,
        changed,
        alerts_created,
        len(new_close_ids),
        digest_res["sent"],
    )
    return {
        "status": "ok",
        "as_of": as_of.isoformat(),
        "monitors": len(results),
        "readings_ingested": ingested,
        "state_changed": changed,
        "alerts_created": alerts_created,
        "close_suggest_new": len(new_close_ids),
        "digest_sent": digest_res["sent"],
    }
