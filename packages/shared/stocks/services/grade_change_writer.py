"""SCB-CONTEXT-S2 — AnalystGradeChange writer (D-SCB-GRADES-KEY-1).

FMP `/stable/grades` 응답(개별 등급 변경 사건)을 **dedup 후 멱등 upsert** 한다.

★ 이 모듈은 **적재만** 한다 — 누가 언제 부르는지(배선)는 여기 없다.
  배선 후보(① `_fetch_signals` 5번째 콜 / ② 별도 task)는 디렉터 결정 대기 중이며,
  결정과 무관하게 이 계약은 동일하다.

왜 append가 아니라 upsert인가: 원천이 **과거 전체를 매번 반환**한다(실측 9심볼 6,137행·
2012~현재). append 전용이면 재수집마다 6,137행이 다시 쌓여 멱등이 구조적으로 깨진다.
`AnalystSignalSnapshot`의 append 규약(D-I1-2)과 **반대 방향**이라는 점을 분명히 둔다.
"""
import logging
from datetime import date as _date
from typing import Any, Iterable, Optional

from packages.shared.stocks.models import AnalystGradeChange

logger = logging.getLogger(__name__)

# 자연키 = 원천이 주는 전 필드. 이것으로도 완전동일 행이 남아(S2 §1-B: AAPL/2023-06-16/
# Jefferies/Buy→Buy/maintain) dedup이 필수다. 순서 = unique_together와 동일.
KEY_FIELDS = ("symbol", "date", "grading_company", "previous_grade", "new_grade", "action")


def _parse_date(value: Any) -> Optional[_date]:
    """원천 `YYYY-MM-DD` → date. 형식 이탈은 None(그 행은 버린다)."""
    if isinstance(value, _date):
        return value
    if not value:
        return None
    try:
        return _date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def normalize_row(raw: dict) -> Optional[dict]:
    """FMP 행 → 모델 필드 dict. 필수(symbol·date) 결손 시 None."""
    symbol = (raw.get("symbol") or "").strip().upper()
    d = _parse_date(raw.get("date"))
    if not symbol or d is None:
        return None
    return {
        "symbol": symbol,
        "date": d,
        "grading_company": (raw.get("gradingCompany") or "").strip(),
        "previous_grade": (raw.get("previousGrade") or "").strip(),
        "new_grade": (raw.get("newGrade") or "").strip(),
        "action": (raw.get("action") or "").strip(),
    }


def dedup_grade_rows(raw_rows: Iterable[dict]) -> list[dict]:
    """자연키로 접고 원본 행 수를 센다 (순수 함수 · DB 무접촉).

    반환 = [{**KEY_FIELDS, "source_row_count": n}, ...] — 입력 순서 보존.

    계약 2건(S2 §1-B 실측에서 유래):
      · 전 필드가 같은 N행 → **1행 + source_row_count=N** (정보 손실 0)
      · 같은 날·같은 기관이라도 등급/action이 다르면 → **각각 별 행** (이게 설계 목적)
    """
    out: dict[tuple, dict] = {}
    dropped = 0
    for raw in raw_rows or []:
        row = normalize_row(raw)
        if row is None:
            dropped += 1
            continue
        key = tuple(row[f] for f in KEY_FIELDS)
        if key in out:
            out[key]["source_row_count"] += 1
        else:
            out[key] = {**row, "source_row_count": 1}
    if dropped:
        logger.warning("dedup_grade_rows: 필수 필드 결손으로 %d행 제외", dropped)
    return list(out.values())


def upsert_grade_changes(raw_rows: Iterable[dict], source: str = "fmp") -> dict:
    """dedup 후 자연키 기준 멱등 upsert.

    반환 = {created, updated, rows_in, rows_out}.
    같은 응답을 두 번 적용해도 행 수·source_row_count가 불변이다(재실행 안전).
    빈 응답은 에러가 아니라 무작업(created=0)이다.
    """
    raw_list = list(raw_rows or [])  # 제너레이터 입력도 1회만 소비(rows_in 정확)
    rows = dedup_grade_rows(raw_list)
    created = updated = 0
    for row in rows:
        key = {f: row[f] for f in KEY_FIELDS}
        _, was_created = AnalystGradeChange.objects.update_or_create(
            **key,
            defaults={"source_row_count": row["source_row_count"], "source": source},
        )
        created += 1 if was_created else 0
        updated += 0 if was_created else 1
    return {
        "created": created,
        "updated": updated,
        "rows_in": len(raw_list),
        "rows_out": len(rows),
    }
