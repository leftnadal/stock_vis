"""R2-S2 선행: co-mention 파트너 활동 일일 물질화 태스크(MIG-BUNDLE-1 C-2).

story_activity._compute_story_threads_live 를 소스로 재사용(중복 구현 금지 —
서비스가 라이브/캐시 양쪽 소스). 종목별로 후보 파트너 활동을 계산해
SymbolStoryActivity 로 upsert 한다. 카드 API 는 캐시를 우선 소비(C-3).

멱등: 심볼 단위 delete-then-insert(트랜잭션) → 재실행 안전. 관계·엣지 무변경(읽기+캐시 쓰기).
beat 등록은 코드 아닌 DB(PeriodicTask, Bug #28) — 병진 수동(랜딩 관문 ②).
"""

import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def materialize_story_activity(now=None):
    """전 종목 co-mention 파트너 활동을 물질화(태스크·커맨드 공용 코어).

    Returns: {"symbols": 물질화된 종목 수, "rows": 적재 행 수, "candidates": 대상 종목 수}
    """
    import datetime

    from apps.chain_sight.models import CoMentionEdge, SymbolStoryActivity
    from apps.chain_sight.services.story_activity import (
        CANDIDATE_N,
        _compute_story_threads_live,
    )

    now = now or timezone.now()

    # 대상 심볼 = CoMentionEdge 에 등장한 전 종목(양방향).
    symbols = set()
    for a, b in CoMentionEdge.objects.values_list("symbol_a", "symbol_b").iterator():
        symbols.add(a)
        symbols.add(b)

    materialized_symbols = 0
    total_rows = 0
    for sym in symbols:
        # top_n=candidate_n → 슬라이스 손실 없이 후보 전량의 지표를 캐시에 적재.
        result = _compute_story_threads_live(
            sym, top_n=CANDIDATE_N, candidate_n=CANDIDATE_N, now=now
        )
        threads = result["threads"]
        thread_total = result["thread_total"]
        objs = []
        for t in threads:
            last = t["last_co_mention_date"]
            objs.append(
                SymbolStoryActivity(
                    symbol=sym,
                    partner=t["partner"],
                    count_7d=t["count_7d"],
                    count_90d=t["count_90d"],
                    weekly_avg_90d=t["weekly_avg_90d"],
                    activity_ratio=t["activity_ratio"],
                    last_co_mention_date=(
                        datetime.date.fromisoformat(last) if last else None
                    ),
                    thread_total=thread_total,
                    materialized_at=now,
                )
            )
        # 심볼 단위 멱등 upsert(delete-then-insert).
        with transaction.atomic():
            SymbolStoryActivity.objects.filter(symbol=sym).delete()
            if objs:
                SymbolStoryActivity.objects.bulk_create(objs)
        if objs:
            materialized_symbols += 1
        total_rows += len(objs)

    logger.info(
        "materialize_story_activity: candidates=%s symbols=%s rows=%s",
        len(symbols),
        materialized_symbols,
        total_rows,
    )
    return {
        "candidates": len(symbols),
        "symbols": materialized_symbols,
        "rows": total_rows,
    }


@shared_task(
    name="chainsight-materialize-story-activity",
    bind=True,
    max_retries=0,  # 무재시도(단순 우선·멱등 재실행은 다음 beat 가 담당)
    soft_time_limit=1800,
    time_limit=1980,
)
def materialize_story_activity_task(self):
    """일일 co-mention 활동 캐시 물질화(beat 진입점)."""
    from django import db

    db.connections.close_all()  # macOS fork 안전 (Bug #25)
    return materialize_story_activity()
