"""TimeSeriesContext + metric 시계열 컨텍스트 (Slice 8 Part 1 Step 1 #27).

LLM input에 4분기·12분기 시계열을 부착하여 Slice 7 75% "구체성 부족" 시스템 결함 해소.
모든 metric 모델 (MetricResult 등)에 Optional[TimeSeriesContext] 필드 부착하여
시계열 데이터 보유 시 LLM이 변화율·추세까지 함께 해석 가능.

backward-compat: 기존 fixture (time_series 없음)는 default None으로 로딩 무영향.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TimeSeriesContext(BaseModel):
    """Metric 1개의 4분기·12분기 시계열 컨텍스트.

    설계 (지시서 §Step 1 #1, B2 raw + 시계열):
      - current: 현재 분기 값 (필수)
      - window_1q / 4q / 12q: 과거 분기 값 (Optional, FMP 데이터 가용성 흡수)
      - delta_4q_pct property: LLM/UI 표시용 4분기 변화율

    Examples:
        >>> ts = TimeSeriesContext(current=Decimal("100"), window_4q=Decimal("80"))
        >>> ts.delta_4q_pct
        Decimal('25')
        >>> ts_none = TimeSeriesContext(current=Decimal("100"))
        >>> ts_none.delta_4q_pct is None
        True
    """

    model_config = ConfigDict(extra="forbid")

    current: Decimal = Field(..., description="현재 분기 값 (필수).")
    window_1q: Optional[Decimal] = Field(
        None, description="1분기 전 값 (FMP 미가용 시 None)."
    )
    window_4q: Optional[Decimal] = Field(
        None, description="4분기 전 값 (FMP 미가용 시 None)."
    )
    window_12q: Optional[Decimal] = Field(
        None, description="12분기 전 값 (3년치 데이터, FMP 미가용 시 None)."
    )

    @property
    def delta_4q_pct(self) -> Optional[Decimal]:
        """4분기 변화율 (%). window_4q가 None 또는 0이면 None.

        공식: (current - window_4q) / abs(window_4q) * 100
        abs(window_4q)를 분모로 사용해 음수 base에서도 부호 보존.
        """
        if self.window_4q is None or self.window_4q == 0:
            return None
        return (self.current - self.window_4q) / abs(self.window_4q) * Decimal("100")
