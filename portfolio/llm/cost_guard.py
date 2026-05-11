"""LLM 비용 가드. Slice 단위 호출 카운트 + 비용 추적 (D3.C).

Slice 진입 시 reset_slice()로 카운터 0으로 초기화.
record_call()로 매 호출 누적.
exceeded() 또는 LLMClient 통합으로 한도 초과 시 LLMBudgetExceededError 발생.

사용 예:
    from portfolio.llm.cost_guard import CostGuard

    guard = CostGuard.get_instance()
    guard.reset_slice("slice3", max_calls=50)
    guard.record_call(cost_usd=0.005, model="claude-haiku-4-5")
    print(guard.status())
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import ClassVar, Optional

from portfolio.llm.exceptions import LLMBudgetExceededError

logger = logging.getLogger(__name__)


@dataclass
class CallRecord:
    """단일 LLM 호출 기록."""

    cost_usd: float
    model: str
    timestamp: str  # ISO format


@dataclass
class CostGuard:
    """싱글톤 패턴. 슬라이스 단위 비용 가드."""

    slice_id: str = "default"
    max_calls: int = 50
    call_count: int = 0
    total_cost_usd: float = 0.0
    records: list[CallRecord] = field(default_factory=list)
    started_at: Optional[str] = None

    _instance: ClassVar[Optional["CostGuard"]] = None
    _lock: ClassVar[Lock] = Lock()

    @classmethod
    def get_instance(cls) -> "CostGuard":
        """싱글톤 인스턴스 반환."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def reset_slice(self, slice_id: str, max_calls: int = 50) -> None:
        """슬라이스 진입 시 카운터 reset.

        Args:
            slice_id: 슬라이스 식별자 (예: "slice3", "slice4")
            max_calls: 본 슬라이스의 최대 호출 한도 (default 50)
        """
        self.slice_id = slice_id
        self.max_calls = max_calls
        self.call_count = 0
        self.total_cost_usd = 0.0
        self.records = []
        self.started_at = datetime.now(timezone.utc).isoformat()
        logger.info(
            "CostGuard reset for slice=%s, max_calls=%d", slice_id, max_calls
        )

    def record_call(self, cost_usd: float, model: str) -> None:
        """매 LLM 호출 후 누적 기록.

        Raises:
            LLMBudgetExceededError: 한도 초과 시 (호출 후 검증 — 다음 호출 차단)
        """
        if self.call_count >= self.max_calls:
            raise LLMBudgetExceededError(
                f"Slice {self.slice_id} budget exceeded: "
                f"{self.call_count}/{self.max_calls} calls"
            )
        self.call_count += 1
        self.total_cost_usd += cost_usd
        self.records.append(
            CallRecord(
                cost_usd=cost_usd,
                model=model,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )

    def exceeded(self) -> bool:
        """한도 초과 여부 (호출 전 검증용)."""
        return self.call_count >= self.max_calls

    def status(self) -> dict:
        """현재 상태 dict 반환."""
        return {
            "slice_id": self.slice_id,
            "call_count": self.call_count,
            "max_calls": self.max_calls,
            "remaining": max(0, self.max_calls - self.call_count),
            "total_cost_usd": round(self.total_cost_usd, 4),
            "started_at": self.started_at,
            "records_count": len(self.records),
        }
