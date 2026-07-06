"""MP2-DELTA 슬라이스 2 — anomaly 신규/소멸/해소 델타 (조회-시 무상태 파생).

D-DELTA-CALC(후보 A): 요청마다 AnomalySignalLog 발동 날짜만 읽어 fired-set 비교.
  저장·캐시·마이그레이션 0 (prod 쓰기 0). 선례 = services/sector_delta.py.
D-DELTA-YDAY(anomaly 변형): 비교 기준 = 직전 '발동일'(calendar −1 아님, 직전 거래일도 아님).
  발동은 sparse(무발동일 다수)라 직전 발동일 기준만이 유의미한 델타를 준다.
D-DELTA-QUIET(옵션 2, 해소 명시 지향): 무발동일에 "해소" 표시를 지향하되, 거짓 해소를
  막기 위해 engine 실행 흔적을 게이트로 둔다. R3 실측 결과 판별 불가 →
  5c-ii 폴백 적용(_engine_ran_since 항상 False): 무발동일 항상 quiet.
  resolving/resolved_rules는 계약에 미래 확장 자리로 보존(ANOMALY-RUN-EVIDENCE 도입 시 활성).
"""
from __future__ import annotations

from datetime import date as date_cls
from typing import Any

from apps.market_pulse.models.anomaly import AnomalySignalLog

# 무발동일 해소 표시 lookback(일). 근거: 실측 발동 사이클(3주 내 발동 ~6일, 최장 무발동 13일).
# 조회-시 파생 경로라 celery worker 재시작 무관(common-bugs #41 비해당).
# 모듈 상수 고정 — 설정·환경변수 노출 금지(D-DELTA-QUIET 안전핀).
ANOMALY_RESOLVE_LOOKBACK_DAYS = 7


def _fired_rule_ids(d: date_cls | None) -> list[str]:
    """해당 발동일의 distinct rule_id (정렬 안정). d=None → 빈 리스트."""
    if d is None:
        return []
    return sorted(
        set(
            AnomalySignalLog.objects.filter(triggered_at__date=d).values_list(
                "rule_id", flat=True
            )
        )
    )


def _engine_ran_since(last: date_cls, today: date_cls) -> bool:
    """R3 5c-ii 폴백: anomaly engine은 무발동일에 실행 흔적을 남기지 않는다.

    AnomalySignalLog는 발동 행만 적재하고(tasks/anomaly.py — fired 루프 내부에서만
    create), 전용 run-marker 모델도 없다. 따라서 'engine이 돌았으나 무발동'을
    'engine 미실행'과 구분할 수 없다 → 항상 False 반환하여 무발동일을 항상 quiet로
    수렴시킨다(거짓 해소 방지). 미래(ANOMALY-RUN-EVIDENCE): run-marker 도입 시
    여기서 실제 판별하여 resolving을 활성화한다.
    """
    return False


def compute_anomaly_delta(today: date_cls) -> dict[str, Any]:
    """오늘 기준 anomaly 발동 상태 변화(조회-시 파생).

    상태:
      fired      — 오늘 발동. 직전 발동일 대비 new_rules / gone_rules.
      resolving  — 최근 발동분 해소(5c-ii 폴백에서는 미발생 — 미래 확장 자리).
      quiet      — 오늘 무발동. 마지막 발동일만 노출.
      no_history — 발동 이력 0.
    날짜는 전부 서버 ISO 문자열. FE 날짜 연산 금지.
    """
    fired_dates = list(
        AnomalySignalLog.objects.filter(triggered_at__date__lte=today).dates(
            "triggered_at", "day", order="DESC"
        )
    )
    base: dict[str, Any] = {
        "state": "quiet",
        "as_of": today.isoformat(),
        "last_fired_date": None,
        "vs_fired_date": None,
        "new_rules": [],
        "gone_rules": [],
        "resolved_rules": [],
    }
    if not fired_dates:
        return {**base, "state": "no_history"}

    last = fired_dates[0]
    if last == today:
        prev = fired_dates[1] if len(fired_dates) > 1 else None
        cur_set = set(_fired_rule_ids(last))
        prev_set = set(_fired_rule_ids(prev))
        return {
            **base,
            "state": "fired",
            "last_fired_date": last.isoformat(),
            "vs_fired_date": prev.isoformat() if prev else None,
            "new_rules": sorted(cur_set - prev_set),
            "gone_rules": sorted(prev_set - cur_set),
        }

    # 오늘 무발동 — 해소 표시는 engine 실행 흔적 게이트를 통과해야만(5c-i). 폴백에서는 항상 quiet.
    gap = (today - last).days
    if gap <= ANOMALY_RESOLVE_LOOKBACK_DAYS and _engine_ran_since(last, today):
        return {
            **base,
            "state": "resolving",
            "last_fired_date": last.isoformat(),
            "resolved_rules": _fired_rule_ids(last),
        }
    return {**base, "state": "quiet", "last_fired_date": last.isoformat()}
