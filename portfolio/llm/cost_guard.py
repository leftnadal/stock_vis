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

Slice 8 Part 1 #33 (이중 카운터):
    PER_INSTANCE_LIMIT=50: 단일 instance(= scripts/스크립트 1회 실행) 호출 한도.
    PER_SLICE_LIMIT=100: 전체 slice(= 다중 instance 합산) 호출 한도.
    record_llm_call(): 두 카운터 +1 + check (호출 전 차단용).
    start_instance(): instance 카운터만 reset (slice 카운터 보존).

Slice 9 Step 0 #43 (비용 임계 + 슬라이스 cap):
    threshold: 누적 광의 비용 임계 (default $4.00, env COST_THRESHOLD_USD).
    warning: 누적 80% 사전 경고 (default $3.20, env COST_WARNING_USD).
    cap_per_slice: 슬라이스 단독 cap ($1.00, env COST_CAP_PER_SLICE_USD).
    cap_warning: cap 80% 사전 경고 ($0.80, env COST_CAP_WARNING_USD).
    cumulative_usd: 전체 누적 (reset_slice/reset_for_slice 시도 보존).
    slice_usd: 현재 슬라이스 비용 (reset 시 0).
    record_cost(cost): cumulative+slice 합산 + cap/threshold check.
    check_warnings(): 경고 리스트 반환.
    CostCapExceeded / CostThresholdExceeded 신규 예외.

Slice 11 Step 0 (D-3 임계 상향):
    threshold $3.00 → $4.00 (비용 패턴 $1 → $1.5 → $2 → $3 → $4 일관).
    warning   $2.40 → $3.20 (= 80%).
    재상향 트리거 $3.40 (CostGuard 자체 변경 없음; COST_POLICY.md 정책 변수).
"""

from __future__ import annotations

import logging
import os
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
    """싱글톤 패턴. 슬라이스 단위 비용 가드.

    Slice 8 Part 1 #33: 이중 카운터(per-instance + per-slice).
    Slice 9 Step 0 #43: 누적 임계 + 슬라이스 cap (비용 차원).
    """

    slice_id: str = "default"
    max_calls: int = 100  # backward-compat: slice 한도 (= PER_SLICE_LIMIT default)
    call_count: int = 0  # slice 카운터 (alias로 _per_slice_count 의미)
    instance_call_count: int = 0  # instance 카운터 (Slice 8 #33 신규)
    total_cost_usd: float = 0.0  # 슬라이스 단독 비용 합계 (reset_slice 시 0)
    records: list[CallRecord] = field(default_factory=list)
    started_at: Optional[str] = None

    # Slice 9 #43 신규: 비용 차원 임계 + cap (env 기반 default)
    # Slice 11 D-3: $3.00 → $4.00, $2.40 → $3.20 (80%) 상향.
    threshold: float = field(
        default_factory=lambda: float(os.getenv("COST_THRESHOLD_USD", "4.00"))
    )
    warning: float = field(
        default_factory=lambda: float(os.getenv("COST_WARNING_USD", "3.20"))
    )
    cap_per_slice: float = field(
        default_factory=lambda: float(os.getenv("COST_CAP_PER_SLICE_USD", "1.00"))
    )
    cap_warning: float = field(
        default_factory=lambda: float(os.getenv("COST_CAP_WARNING_USD", "0.80"))
    )
    per_call_haiku: float = field(
        default_factory=lambda: float(os.getenv("PER_CALL_THRESHOLD_HAIKU_USD", "0.03"))
    )
    per_call_sonnet: float = field(
        default_factory=lambda: float(
            os.getenv("PER_CALL_THRESHOLD_SONNET_USD", "0.10")
        )
    )
    cumulative_usd: float = 0.0  # 전체 누적 (reset_slice/reset_for_slice 시도 보존)
    slice_usd: float = 0.0  # 현재 슬라이스 비용 (reset 시 0)

    # Slice 8 Part 1 #33: 클래스 상수
    PER_INSTANCE_LIMIT: ClassVar[int] = 50
    PER_SLICE_LIMIT: ClassVar[int] = 100

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

    def reset_slice(self, slice_id: str, max_calls: Optional[int] = None) -> None:
        """슬라이스 진입 시 두 카운터 모두 reset (멱등).

        Args:
            slice_id: 슬라이스 식별자 (예: "slice3", "slice4")
            max_calls: slice 한도. None이면 PER_SLICE_LIMIT (100) 사용.
                       backward-compat: 기존 호출이 max_calls=50 명시했으면 그대로 50 사용.

        Slice 9 #43: slice_usd도 0으로 reset, cumulative_usd는 보존.
        """
        self.slice_id = slice_id
        self.max_calls = max_calls if max_calls is not None else self.PER_SLICE_LIMIT
        self.call_count = 0
        self.instance_call_count = 0
        self.total_cost_usd = 0.0
        self.records = []
        self.slice_usd = 0.0  # Slice 9 #43: 슬라이스 cap 카운터 reset
        self.started_at = datetime.now(timezone.utc).isoformat()
        logger.info(
            "CostGuard reset for slice=%s, max_calls=%d", slice_id, self.max_calls
        )

    # Slice 8 #33 alias — 지시서 §Step 0-1 명시.
    # Slice 9 #43: reset_for_slice는 reset_slice의 alias로 유지하되,
    # reset_slice가 slice_usd도 0으로 리셋 + cumulative_usd 보존을 수행한다.
    reset_for_slice = reset_slice

    def start_instance(self) -> None:
        """instance 카운터만 reset (slice 카운터·비용·records 모두 보존).

        Slice 8 Part 1 #33: 단일 스크립트/instance 진입 시 호출.
        예: 야간 자동화에서 매 batch 시작마다 호출 → instance 한도 50 재시작.
        """
        self.instance_call_count = 0

    def check_per_instance(self) -> None:
        """instance 카운터가 PER_INSTANCE_LIMIT 초과 시 raise.

        Raises:
            LLMBudgetExceededError(scope="instance", ...)
        """
        if self.instance_call_count > self.PER_INSTANCE_LIMIT:
            raise LLMBudgetExceededError(
                scope="instance",
                count=self.instance_call_count,
                limit=self.PER_INSTANCE_LIMIT,
            )

    def check_per_slice(self) -> None:
        """slice 카운터가 max_calls 초과 시 raise.

        Raises:
            LLMBudgetExceededError(scope="slice", ...)
        """
        if self.call_count > self.max_calls:
            raise LLMBudgetExceededError(
                scope="slice",
                count=self.call_count,
                limit=self.max_calls,
            )

    def record_llm_call(self) -> None:
        """LLMClient.call 직전 1회 호출 (Slice 8 #33).

        두 카운터 모두 +1 후 두 check 호출. 한도 도달 시 LLMBudgetExceededError raise.
        비용/모델 기록은 별도 record_call()에서 처리.
        """
        self.instance_call_count += 1
        self.call_count += 1
        self.check_per_instance()
        self.check_per_slice()

    def record_call(self, cost_usd: float, model: str) -> None:
        """매 LLM 호출 후 누적 기록 (backward-compat).

        내부에서 record_llm_call() 호출 → 두 카운터 +1 + check.
        이후 비용/모델 기록 추가.

        Raises:
            LLMBudgetExceededError: 한도 초과 시 (호출 후 검증).
        """
        self.record_llm_call()
        self._record_response_internal(cost_usd, model)

    def record_response(self, cost_usd: float, model: str) -> None:
        """LLM 응답 후 비용/모델만 누적 (Slice 8 #33).

        record_llm_call()이 호출 전 카운트했음을 전제. 카운트 안 함 → 중복 방지.
        지시서 §Step 0-1 "record_llm_call은 LLMClient.call 직전 1회만 호출" 충족.
        """
        self._record_response_internal(cost_usd, model)

    def _record_response_internal(self, cost_usd: float, model: str) -> None:
        """비용/모델 기록 내부 헬퍼 (카운트 X)."""
        self.total_cost_usd += cost_usd
        self.records.append(
            CallRecord(
                cost_usd=cost_usd,
                model=model,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )

    # ──────────────────────────────────────────────────────────────────
    # Slice 9 Step 0 #43: 비용 차원 임계 + 슬라이스 cap
    # ──────────────────────────────────────────────────────────────────

    def record_cost(self, cost_usd: float) -> None:
        """비용만 기록 (호출 카운트 X). 누적 + 슬라이스 cap 검증.

        Slice 9 #43 신규. record_call/record_response와 별개.
        - cumulative_usd: 전체 누적
        - slice_usd: 현재 슬라이스 비용

        Raises:
            CostCapExceeded: 슬라이스 cap 위반 시 (cap_per_slice 기본 $1.00)
            CostThresholdExceeded: 누적 임계 위반 시 (threshold 기본 $3.00)
        """
        with self._lock:
            self.cumulative_usd += cost_usd
            self.slice_usd += cost_usd

            # 슬라이스 cap 검증 (선행 지표)
            if self.slice_usd > self.cap_per_slice:
                raise CostCapExceeded(
                    f"슬라이스 cap 위반: ${self.slice_usd:.4f} > ${self.cap_per_slice} (cap)"
                )

            # 누적 임계 검증 (후행 지표)
            if self.cumulative_usd > self.threshold:
                raise CostThresholdExceeded(
                    f"누적 임계 위반: ${self.cumulative_usd:.4f} > ${self.threshold} (threshold)"
                )

    def check_warnings(self) -> list[str]:
        """경고 신호 확인 (Slice 9 #43).

        Returns:
            cap 80% 도달 + 누적 80% 도달 경고 메시지 리스트.
        """
        warnings: list[str] = []
        if self.slice_usd >= self.cap_warning:
            warnings.append(
                f"⚠ 슬라이스 cap 80% 도달: ${self.slice_usd:.4f} (cap ${self.cap_per_slice})"
            )
        if self.cumulative_usd >= self.warning:
            warnings.append(
                f"⚠ 누적 임계 80% 도달: ${self.cumulative_usd:.4f} (threshold ${self.threshold})"
            )
        return warnings

    # ──────────────────────────────────────────────────────────────────

    def exceeded(self) -> bool:
        """한도 초과 여부 (호출 전 검증용, backward-compat).

        Slice 8 #33: 두 카운터 중 하나라도 도달 시 True.
        """
        return (
            self.instance_call_count >= self.PER_INSTANCE_LIMIT
            or self.call_count >= self.max_calls
        )

    def status(self) -> dict:
        """현재 상태 dict 반환."""
        return {
            "slice_id": self.slice_id,
            "call_count": self.call_count,
            "max_calls": self.max_calls,
            "remaining": max(0, self.max_calls - self.call_count),
            "instance_call_count": self.instance_call_count,
            "per_instance_limit": self.PER_INSTANCE_LIMIT,
            "instance_remaining": max(0, self.PER_INSTANCE_LIMIT - self.instance_call_count),
            "total_cost_usd": round(self.total_cost_usd, 4),
            "started_at": self.started_at,
            "records_count": len(self.records),
            # Slice 9 #43: 비용 차원 상태
            "cumulative_usd": round(self.cumulative_usd, 4),
            "slice_usd": round(self.slice_usd, 4),
            "threshold": self.threshold,
            "cap_per_slice": self.cap_per_slice,
        }


class CostCapExceeded(Exception):
    """슬라이스 cap 위반 (Slice 9 #43).

    record_cost()에서 slice_usd > cap_per_slice 시 raise.
    """


class CostThresholdExceeded(Exception):
    """누적 임계 위반 (Slice 9 #43).

    record_cost()에서 cumulative_usd > threshold 시 raise.
    """
