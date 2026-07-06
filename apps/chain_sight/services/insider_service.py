"""
C2a 내부자 파이프라인 (TH-2) — FMP E1/E2 → InsiderTransactionRecord.

설계서 theme_heat_design.md v1.2.1 §5.1:
- E1/E2 거래 레벨로 90일 rolling 자체 집계, E3 는 분기 대조 sanity check(±10%).
- 원본 레코드 전건 보존 (transaction_type 공란 포함) — **방어 필터는 적재가 아닌
  집계(조회) 계층**에서 적용한다. (필터 튜닝 시 재수집 없이 재집계로 대응.)
- dedup_key = hash(symbol, reporting_cik, transaction_date, transaction_type,
  securities_transacted, price), upsert 멱등.

FMP 접근 검증: docs/audits/fmp_insider_access_report.md (E1/E2/E3 OPEN, PASS).
"""

import hashlib
import logging
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Optional

from apps.chain_sight.models import InsiderTransactionRecord

logger = logging.getLogger(__name__)

# ── 방어 필터 상수 (§5.1) — 집계 계층 전용 ──
SELL_TYPE = "S-Sale"       # 자발적 매도만
BUY_TYPE = "P-Purchase"    # 자발적 매수만
# A-Award·M-Exempt·F-InKind·G-Gift·공란은 집계에서 제외 (매수로 오인 금지).

# type_of_owner 가중 (§5.1)
WEIGHT_OFFICER_DIRECTOR = 1.0
WEIGHT_TEN_PCT = 0.7
WEIGHT_INDIRECT = 0.5


# ────────────────────────────── 적재 (전건 보존) ──────────────────────────────
def _to_decimal(value: Any) -> Optional[Decimal]:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def build_dedup_key(row: dict) -> str:
    """§5.1 dedup_key = sha256(symbol, reporting_cik, transaction_date, transaction_type,
    securities_transacted, price). 64-hex = varchar(64) 정합."""
    parts = [
        str(row.get("symbol", "")).upper(),
        str(row.get("reportingCik", "")),
        str(row.get("transactionDate", ""))[:10],
        str(row.get("transactionType", "")),
        str(row.get("securitiesTransacted", "")),
        str(row.get("price", "")),
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def map_fmp_row(row: dict) -> Optional[dict]:
    """FMP E1/E2 응답 행 → InsiderTransactionRecord 필드. 필수 날짜 결측이면 None."""
    filing = str(row.get("filingDate", ""))[:10]
    txn = str(row.get("transactionDate", ""))[:10]
    if not filing or not txn:
        return None
    return {
        "symbol": str(row.get("symbol", "")).upper(),
        "reporting_cik": str(row.get("reportingCik", "") or ""),
        "company_cik": str(row.get("companyCik", "") or ""),
        "filing_date": filing,
        "transaction_date": txn,
        "transaction_type": str(row.get("transactionType", "") or ""),
        "securities_transacted": _to_decimal(row.get("securitiesTransacted")),
        "price": _to_decimal(row.get("price")),
        "type_of_owner": str(row.get("typeOfOwner", "") or "")[:64],
        "direct_or_indirect": str(row.get("directOrIndirect", "") or "")[:8],
        "acq_or_disp": str(row.get("acquisitionOrDisposition", "") or "")[:8],
        "sec_url": str(row.get("url") or row.get("link") or ""),
        "raw": row,
        "dedup_key": build_dedup_key(row),
    }


def upsert_insider_records(rows: Iterable[dict]) -> dict:
    """FMP 행 리스트를 dedup_key 로 멱등 upsert. 전건 보존(필터 없음). {created, updated, skipped}."""
    created = updated = skipped = 0
    for row in rows:
        fields = map_fmp_row(row)
        if fields is None:
            skipped += 1
            continue
        dedup_key = fields.pop("dedup_key")
        _, was_created = InsiderTransactionRecord.objects.update_or_create(
            dedup_key=dedup_key, defaults=fields
        )
        created += was_created
        updated += not was_created
    return {"created": created, "updated": updated, "skipped": skipped}


# ────────────────────────────── 수집 (E1 백필 / E2 증분) ──────────────────────────────
def backfill_symbol(client, symbol: str, cutoff: date, max_pages: int = 50) -> dict:
    """E1 페이지네이션 순회 — transaction_date 가 cutoff 이전이 될 때까지. 멱등 upsert."""
    agg = {"created": 0, "updated": 0, "skipped": 0, "pages": 0}
    for page in range(max_pages):
        rows = client.get_insider_trading_search(symbol, page=page, limit=100)
        if not rows:
            break
        agg["pages"] += 1
        res = upsert_insider_records(rows)
        for k in ("created", "updated", "skipped"):
            agg[k] += res[k]
        # 마지막 행의 거래일이 cutoff 이전이면 순회 종료 (desc 정렬 가정)
        oldest = min((str(r.get("transactionDate", ""))[:10] for r in rows if r.get("transactionDate")), default="")
        if oldest and oldest < cutoff.isoformat():
            break
        if len(rows) < 100:
            break
    return agg


def collect_latest(client, max_pages: int = 3) -> dict:
    """E2 최신 스트림 기반 증분 수집 (일간). beat 등록은 TH-3."""
    agg = {"created": 0, "updated": 0, "skipped": 0}
    for page in range(max_pages):
        rows = client.get_insider_trading_latest(page=page, limit=100)
        if not rows:
            break
        res = upsert_insider_records(rows)
        for k in agg:
            agg[k] += res[k]
    return agg


# ────────────────────────────── C2a 집계 (방어 필터 — §5.1) ──────────────────────────────
def owner_weight(record: InsiderTransactionRecord) -> float:
    """type_of_owner/direct_or_indirect 가중 (§5.1). 간접 0.5 > 10%주주 0.7 > 임원·이사 1.0."""
    if (record.direct_or_indirect or "").upper().startswith("I"):
        return WEIGHT_INDIRECT
    owner = (record.type_of_owner or "").lower()
    if "10%" in owner or "ten percent" in owner:
        return WEIGHT_TEN_PCT
    return WEIGHT_OFFICER_DIRECTOR


def compute_c2a_net_sell_ratio(
    records: Iterable[InsiderTransactionRecord],
) -> Optional[float]:
    """
    net_sell_ratio = Σ(매도금액×가중) / Σ((매도+매수)금액×가중). (§5.1)

    방어 필터 (집계 계층):
      1. transaction_type 공란 제외
      2. S-Sale(매도)·P-Purchase(매수)만 — A-Award 등은 제외 (매수 오인 금지)
      3. 금액 = price×securities_transacted, price=0/None 이면 금액가중 제외
      4. type_of_owner 가중 적용
    유효 매도·매수 금액 합이 0 이면 None (결측 → §3-5 재분배).
    """
    weighted_sell = 0.0
    weighted_buy = 0.0
    for r in records:
        ttype = r.transaction_type
        if ttype not in (SELL_TYPE, BUY_TYPE):
            continue  # 공란·A-Award·M-Exempt·F-InKind·G-Gift 제외
        if r.price is None or r.price == 0 or r.securities_transacted is None:
            continue  # 금액가중 불가
        amount = float(r.price) * float(r.securities_transacted) * owner_weight(r)
        if ttype == SELL_TYPE:
            weighted_sell += amount
        else:
            weighted_buy += amount
    denom = weighted_sell + weighted_buy
    if denom <= 0:
        return None
    return weighted_sell / denom


def net_sell_ratio_for_symbols(
    symbols: Iterable[str], as_of: date, window_days: int = 90
) -> Optional[float]:
    """테마 합산 net_sell_ratio_90d — 구성종목 전체 거래를 한 풀로 집계 (§5.1)."""
    start = as_of - timedelta(days=window_days)
    qs = InsiderTransactionRecord.objects.filter(
        symbol__in=[s.upper() for s in symbols],
        transaction_date__gte=start,
        transaction_date__lte=as_of,
    )
    return compute_c2a_net_sell_ratio(qs)


# ────────────────────────────── E3 sanity check (경고만) ──────────────────────────────
def e3_sanity_check(client, symbol: str, self_disposed: int, self_acquired: int) -> dict:
    """
    자체 분기 집계(disposed/acquired 건수) vs FMP E3 statistics ±10% 대조.
    불일치는 경고 로그만 — 차단 없음 (§5.1). {ok, delta_disposed, delta_acquired}.
    """
    stats = client.get_insider_statistics(symbol)
    if not stats:
        return {"ok": None, "reason": "no_e3_data"}
    latest = stats[0]
    e3_disposed = latest.get("disposedTransactions", 0) or 0
    e3_acquired = latest.get("acquiredTransactions", 0) or 0

    def _within(a, b, tol=0.10):
        if b == 0:
            return a == 0
        return abs(a - b) / b <= tol

    ok = _within(self_disposed, e3_disposed) and _within(self_acquired, e3_acquired)
    if not ok:
        logger.warning(
            "E3 sanity mismatch %s: self(d=%s,a=%s) vs E3(d=%s,a=%s)",
            symbol, self_disposed, self_acquired, e3_disposed, e3_acquired,
        )
    return {
        "ok": ok,
        "self_disposed": self_disposed, "e3_disposed": e3_disposed,
        "self_acquired": self_acquired, "e3_acquired": e3_acquired,
    }
