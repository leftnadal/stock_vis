"""
유니버스 스냅샷 서비스 (TH-3) — 배치 일자별 모집단 동결.

설계서 theme_heat_design.md §6.0 잠금장치 3("월 1회 구성 동결 — z 히스토리 보호")의
Cycle 1 구현. Cycle 1 은 sector 단위라 구성 = S&P 500 유니버스이며, 이 서비스가
그 일간 동결 원장(UniverseSnapshot)을 관리한다.

핵심 규약:
- 유니버스 = SP500Constituent(is_active) − '.' 포함 심볼 (FMP 프리미엄 402 회피, Bug #23).
  이는 backfill_insider_transactions 커맨드의 유니버스 정의와 **동일 소스**여야 한다.
- 매 배치는 그날 유니버스를 스냅샷으로 박는다 (멱등 — 같은 batch_date 재호출 시 저장분 반환).
- 이후 모든 성분 z 의 모집단은 배치 일자 스냅샷을 참조한다 (라이브 재조회 금지 = drift 차단).
- 저장 시 전일(직전) 스냅샷 대비 심볼 추가/제거 diff 를 1줄 로그로 남긴다.
"""

import logging
from typing import Callable, Optional

from django.utils import timezone

from apps.chain_sight.models import UniverseSnapshot
from packages.shared.stocks.models import SP500Constituent

logger = logging.getLogger(__name__)


def live_universe_symbols() -> list[str]:
    """
    현재 시점의 유니버스를 라이브 조회 (SP500 active − '.' 심볼), 정렬.

    backfill_insider_transactions 와 동일 정의 — 단일 소스 유지. 스냅샷 저장 순간에만
    호출하고, 이후 소비는 스냅샷을 읽는다.
    """
    symbols = (
        SP500Constituent.objects.filter(is_active=True)
        .order_by("symbol")
        .values_list("symbol", flat=True)
    )
    return sorted(s for s in symbols if "." not in s)


def _diff(prev: list[str], curr: list[str]) -> tuple[list[str], list[str]]:
    """전일 대비 (추가, 제거) 심볼."""
    prev_set, curr_set = set(prev or []), set(curr or [])
    added = sorted(curr_set - prev_set)
    removed = sorted(prev_set - curr_set)
    return added, removed


def get_or_create_universe_snapshot(
    batch_date=None, log_fn: Optional[Callable[[str], None]] = None
) -> tuple[list[str], UniverseSnapshot, dict]:
    """
    배치 일자 유니버스 스냅샷을 반환 (없으면 라이브 조회로 생성).

    반환 = (symbols, snapshot, diff) — diff = {"added": [...], "removed": [...], "reused": bool}.
      - 같은 batch_date 스냅샷이 있으면 저장분을 그대로 반환 (멱등, reused=True, diff 미산출).
      - 없으면 라이브 유니버스를 저장하고 직전 스냅샷 대비 diff 를 1줄 로그.

    log_fn 은 커맨드의 self.stdout.write 등 주입용 (없으면 module logger).
    """
    if batch_date is None:
        batch_date = timezone.now().date()

    existing = UniverseSnapshot.objects.filter(batch_date=batch_date).first()
    if existing is not None:
        return list(existing.symbols or []), existing, {"added": [], "removed": [], "reused": True}

    symbols = live_universe_symbols()
    prev = (
        UniverseSnapshot.objects.filter(batch_date__lt=batch_date)
        .order_by("-batch_date")
        .first()
    )
    prev_symbols = list(prev.symbols) if prev else []
    added, removed = _diff(prev_symbols, symbols)

    snapshot = UniverseSnapshot.objects.create(batch_date=batch_date, symbols=symbols)

    prev_label = prev.batch_date.isoformat() if prev else "없음"
    line = (
        f"[universe_snapshot] {batch_date} n={len(symbols)} "
        f"(전일 {prev_label} 대비 +{len(added)}/-{len(removed)}"
        + (f" 추가={added}" if added else "")
        + (f" 제거={removed}" if removed else "")
        + ")"
    )
    (log_fn or logger.info)(line)

    return symbols, snapshot, {"added": added, "removed": removed, "reused": False}


def sector_constituents(sector: str, snapshot_symbols: list[str]) -> list[str]:
    """
    스냅샷 모집단 안에서 특정 GICS 섹터 구성종목만 추린다 (Cycle 1 sector 엔티티용).

    모집단(symbol 집합)은 스냅샷이 고정하고, 섹터 귀속은 SP500Constituent.sector 로 매핑한다
    (섹터는 거의 불변 — 심볼 집합 동결이 drift 방어의 핵심). 반환은 스냅샷 ∩ 섹터.
    """
    snap = set(snapshot_symbols or [])
    rows = (
        SP500Constituent.objects.filter(is_active=True, sector=sector)
        .values_list("symbol", flat=True)
    )
    return sorted(s for s in rows if s in snap)
