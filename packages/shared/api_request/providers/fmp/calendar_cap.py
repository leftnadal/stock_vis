"""FMP 캘린더 응답 캡 감지 (EVT 트랙 하드 요건, 설계 앵커 §3).

FMP `/stable/*-calendar` 계열은 **하드캡 4,000행**에 도달하면 조용히 tail(최근일)만
반환하고 앞 구간을 무언 소실시킨다(earnings 90일 창 실측: 4,000행·뒤 16일만).
이 무오류 데이터 소실은 감지기 없이 가동 금지 — 소비 측은 반환마다 detect_truncation()
으로 검사하고 True면 창을 이분 재시도한다.

재설계(EVT-IMPL-2 §2, 관찰① 처방): 절단 판정 = **count ≥ 4000 단독**. 45일 청킹에서
캡이 유일한 절단 기전이므로 count가 신뢰 시그니처. 앞 지연(min_date > from + grace)은
주말·휴일 시작 창의 정상 지연을 오탐할 수 있어 절단이 아니라 **span_anomaly 경고 로그**로
강등한다(재시도·실패 마킹 없음, 관찰만).
"""
import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 실측 하드캡 (earnings 90일=4,000 정확 / 45일=2,302 안전).
FMP_CALENDAR_ROW_CAP = 4000

# 앞 지연이 이보다 크면 span_anomaly 경고(절단 아님). 주말·연휴 시작 창의 정상 지연 흡수.
SPAN_ANOMALY_GRACE_DAYS = 5


def _parse_date(value: Any) -> Optional[date]:
    """행의 'date' 필드(YYYY-MM-DD 또는 그 접두)를 date로. 파싱 불가 시 None."""
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def detect_truncation(
    requested_from: str, requested_to: str, rows: List[Dict[str, Any]]
) -> bool:
    """캡에 의한 조용한 절단 여부 = **count >= FMP_CALENDAR_ROW_CAP 단독 조건**.

    45일 청킹 하에서 캡 도달이 유일한 절단 기전(실측 시그니처)이라 count만으로 판정한다.
    앞 지연(min_date > from + SPAN_ANOMALY_GRACE_DAYS)은 절단이 아니라 span_anomaly
    경고 로그로 강등 — 주말·휴일 시작 창의 정상 지연을 오탐(재시도·실패 마킹)하지 않기 위함.
    부작용: span_anomaly 시 logger.warning 1회(반환값 불변).
    """
    if len(rows) >= FMP_CALENDAR_ROW_CAP:
        return True

    # span_anomaly 관찰(절단 아님) — 경고만.
    req_from = _parse_date(requested_from)
    if req_from is not None and rows:
        row_dates = [
            d for d in (_parse_date(r.get("date")) for r in rows) if d is not None
        ]
        if row_dates:
            earliest = min(row_dates)
            lag_days = (earliest - req_from).days
            if lag_days > SPAN_ANOMALY_GRACE_DAYS:
                logger.warning(
                    "FMP 캘린더 span_anomaly: 요청 from=%s 이나 최이른 반환일=%s "
                    "(%d일 지연, grace=%d) — 절단 아님(캡 미도달), 관찰만.",
                    requested_from, earliest.isoformat(), lag_days,
                    SPAN_ANOMALY_GRACE_DAYS,
                )

    return False
