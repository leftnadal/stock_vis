"""FMP 캘린더 응답 캡 감지 (EVT 트랙 하드 요건, 설계 앵커 §3).

FMP `/stable/*-calendar` 계열은 **하드캡 4,000행**에 도달하면 조용히 tail(최근일)만
반환하고 앞 구간을 무언 소실시킨다(earnings 90일 창 실측: 4,000행·뒤 16일만).
이 무오류 데이터 소실은 감지기 없이 가동 금지 — 소비 측은 반환마다 detect_truncation()
으로 검사하고 True면 창을 이분 재시도한다.
"""
from datetime import date
from typing import Any, Dict, List, Optional

# 실측 하드캡 (earnings 90일=4,000 정확 / 45일=2,302 안전).
FMP_CALENDAR_ROW_CAP = 4000


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
    """캡에 의한 조용한 절단 여부.

    True 조건 (OR):
      1. len(rows) >= FMP_CALENDAR_ROW_CAP (하드캡 도달)
      2. 반환 date-span이 요청 span의 앞을 덮지 못함 = 가장 이른 반환일 > 요청 from
         (tail-return 캡의 특징 — 앞 구간 무언 소실)

    설계 노트: 조건 2는 앞이 잘린 경우(front clip)만 잡는다. 요청 창 앞부분에 진짜로
    이벤트가 없어 min_date > from인 sparse-front는 False positive가 될 수 있으나,
    조건 1과 결합하지 않는 한 창 이분 재시도는 무해(멱등 upsert). 실측 캡은 두 조건을
    동시 충족했다(4,000행 + 앞 74일 소실).
    """
    if len(rows) >= FMP_CALENDAR_ROW_CAP:
        return True

    req_from = _parse_date(requested_from)
    if req_from is None or not rows:
        return False

    row_dates = [d for d in (_parse_date(r.get("date")) for r in rows) if d is not None]
    if not row_dates:
        return False

    earliest = min(row_dates)
    return earliest > req_from
