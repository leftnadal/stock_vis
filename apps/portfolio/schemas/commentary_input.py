"""TimeSeriesContext + metric 시계열 컨텍스트 (Slice 8 Part 1 Step 1 #27).

LLM input에 4분기·12분기 시계열을 부착하여 Slice 7 75% "구체성 부족" 시스템 결함 해소.
모든 metric 모델 (MetricResult 등)에 Optional[TimeSeriesContext] 필드 부착하여
시계열 데이터 보유 시 LLM이 변화율·추세까지 함께 해석 가능.

backward-compat: 기존 fixture (time_series 없음)는 default None으로 로딩 무영향.

Slice 11 Part 1 (#41 자연 close 대비):
  - CommentaryInputBase + 6 sub class (E1~E6) 추가.
  - 6 진입점 통합 A2 시연용 input schema — A2 = 1 portfolio × E1~E6 통합 commentary.
  - 기존 service Request 모델(E2Request, E5Request 등)은 그대로 유지. 본 schema는
    Slice 11 Part 1+ trio 진입점 통합 호출용 신규 인터페이스.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Optional

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


# ============================================================
# Slice 11 Part 1 — 6 진입점 통합 input schema (A2 시연용)
# ============================================================
#
# D-1 (단일 모듈 base + 6 sub class), D-2 (fixture → schema validate 직접 매핑).
# scope: E1~E6만. e3_portfolio / e4_conversation 변형 진입점은 Slice 12+ 자연 추가.


PresetType = Literal["garp", "focused", "income", "growth", "factor"]
"""투자 스타일 preset enum. Slice 11에서 `income` 추가 (portfolio_a2 fixture 정합)."""


class Holding(BaseModel):
    """포트폴리오 보유 종목 (6 진입점 공통 type).

    Slice 8 H2 ActionItem 패턴 응용 — 같은 자산 클래스를 1회 정의 + 6 sub class 재사용.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    ticker: str = Field(
        ..., min_length=1, max_length=10, description="종목 ticker (대문자)."
    )
    weight: float = Field(
        ..., ge=0.0, le=1.0, description="포트폴리오 비중 (0.0 ~ 1.0)."
    )
    sector: Optional[str] = Field(None, description="섹터 라벨 (선택).")
    asset_class: Optional[Literal["stock", "etf", "bond", "cash"]] = Field(
        None, description="자산 클래스 (선택)."
    )
    name: Optional[str] = Field(None, description="종목 명 (선택, UI 표시용).")


class CommentaryInputBase(BaseModel):
    """6 진입점 공통 input base.

    모든 진입점 input은 이 base를 상속하고, 진입점별 특화 필드를 추가한다.
    discriminator: `entry_point` Literal value.

    설계 원칙:
        - frozen=True: input은 immutable (코칭 호출 후 변경 불가)
        - extra="forbid": 정의되지 않은 필드 거부 (schema drift 즉시 검출)
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    portfolio_id: str = Field(..., min_length=1, description="포트폴리오 식별자.")
    fetched_at: datetime = Field(..., description="데이터 수집 시점 (snapshot).")
    preset: PresetType = Field(..., description="투자 스타일 preset.")
    entry_point: str = Field(..., description="진입점 식별 (e1~e6) — discriminator.")
    holdings: list[Holding] = Field(
        ..., min_length=1, description="포트폴리오 보유 종목."
    )


class CommentaryInputE1(CommentaryInputBase):
    """E1 GARP 스코어링 input."""

    entry_point: Literal["e1"] = "e1"
    garp_metrics: dict[str, dict[str, Any]] = Field(
        ..., description="종목별 GARP 지표 dict — {ticker: {per, peg, roe, ...}}."
    )


class CommentaryInputE2(CommentaryInputBase):
    """E2 포트폴리오 종합 진단 input."""

    entry_point: Literal["e2"] = "e2"
    portfolio_return_1y: float = Field(..., description="포트폴리오 1년 수익률 (%).")
    sector_allocation: dict[str, float] = Field(
        ..., description="섹터 비중 dict — {sector: weight}."
    )


class CommentaryInputE3(CommentaryInputBase):
    """E3 집중도 분석 input."""

    entry_point: Literal["e3"] = "e3"
    concentration_metrics: dict[str, Any] = Field(
        ..., description="집중도 지표 — {hhi, top3_weight, sector_concentration, ...}."
    )


class CommentaryInputE4(CommentaryInputBase):
    """E4 대화 Q&A input.

    A2 통합 시연 시 사용자 질문 + 짧은 대화 이력을 함께 전달.
    """

    entry_point: Literal["e4"] = "e4"
    user_question: str = Field(
        ..., min_length=1, max_length=2000, description="현재 사용자 질문."
    )
    conversation_history: list[dict[str, Any]] = Field(
        default_factory=list, description="이전 대화 turn list (role/content)."
    )


class CommentaryInputE5(CommentaryInputBase):
    """E5 추출 진입점 input.

    extraction_targets에 명시된 항목 추출. TimeSeriesContext가 있으면 시계열 흐름까지 활용.
    """

    entry_point: Literal["e5"] = "e5"
    extraction_targets: list[str] = Field(
        ..., min_length=1, description="추출 대상 키 list."
    )
    time_series_context: Optional[TimeSeriesContext] = Field(
        None, description="Slice 8 #27 시계열 컨텍스트 (선택)."
    )


class CommentaryInputE6(CommentaryInputBase):
    """E6 분석엔진 input — 종목별 분석 결과를 종합."""

    entry_point: Literal["e6"] = "e6"
    analysis_results: dict[str, dict[str, Any]] = Field(
        ...,
        description="종목별 분석 결과 dict — {ticker: {score, signals, notes, ...}}.",
    )


# 외부 노출용 매핑 (loader / discriminator 활용).
COMMENTARY_INPUT_CLASSES: dict[str, type[CommentaryInputBase]] = {
    "e1": CommentaryInputE1,
    "e2": CommentaryInputE2,
    "e3": CommentaryInputE3,
    "e4": CommentaryInputE4,
    "e5": CommentaryInputE5,
    "e6": CommentaryInputE6,
}
