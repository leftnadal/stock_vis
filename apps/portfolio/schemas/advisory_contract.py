"""Slice 20a — 권유 REST 계약 (Pydantic = 진실 소스).

계약 v3(`advisory_engine.recommend`/OUTPUT_CONTRACT_V3)를 REST 응답 형태로 미러.
★ 값 규약: Decimal은 `_jsonable`로 **문자열 직렬화**되므로 금액/비율 필드는 `str`
  (프론트에서 float 정밀도 손실 방지 — KRW·비율 전부 문자열). 계약 가산 전용(D0):
  이후 SIGNAL-FORWARD-INFRA의 예상수익률도 필드 추가로만 들어온다.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class RecommendationContract(BaseModel):
    action: str  # BUY | HOLD | TRIM
    symbol: str
    currency: str
    score: Optional[str] = None  # BUY=배치 우선순위 점수(str), HOLD/TRIM=null
    lane: str  # core | exploration
    rationale: str


class DialByCurrencyContract(BaseModel):
    cash_krw: str
    buffer_share_krw: str
    deployable_krw: str
    headroom_ratio: str


class DialContract(BaseModel):
    dd: str
    a: str
    buffer: str
    is_new_high: bool
    headroom_frac: str
    deployable_krw_total: str
    frozen: bool
    window_days: int
    by_currency: dict[str, DialByCurrencyContract]


class KnobsContract(BaseModel):
    A: int
    G: int
    w: str
    L: int
    E: int


class MaxConcentrationContract(BaseModel):
    symbol: str
    currency: str
    weight: str


class SummaryContract(BaseModel):
    # 통계 세부(진행/배치 갭·fx_context)는 화면 표기 키만 소비 → dict 유연 유지(가산 안전).
    model_config = ConfigDict(extra="allow")

    goal_target_return_pct: Optional[str] = None
    numeraire: str
    cost_basis_note: str
    dial: DialContract
    knobs: KnobsContract
    max_concentration: Optional[MaxConcentrationContract] = None
    notes: list[str]
    progress_gap: dict[str, Any]
    allocation_gap: dict[str, Any]
    fx_context: dict[str, Any]


class AdvisoryOutputContract(BaseModel):
    mode: str  # BUY | DEFEND
    summary: SummaryContract
    recommendations: list[RecommendationContract]
    disclaimer: str


# ---- REST 봉투 3종 + 손잡이 읽기 ----


class LatestAdvisoryContract(BaseModel):
    """GET 최신 권유 — 최근 AdvisoryRun 산출 전문 + trigger + 실행 시각."""

    available: bool
    trigger: Optional[str] = None  # auto | manual
    run_at: Optional[str] = None  # ISO datetime
    output: Optional[AdvisoryOutputContract] = None


class AssetSummaryContract(BaseModel):
    """GET 자산 요약 — 최근 PortfolioSnapshot + 진행/배치 갭 + 모드."""

    available: bool
    date: Optional[str] = None  # 스냅샷 기준일
    total_krw: Optional[str] = None
    by_currency: dict[str, Any] = {}
    price_as_of: Optional[str] = None
    progress_gap: Optional[dict[str, Any]] = None
    allocation_gap: Optional[dict[str, Any]] = None
    mode: Optional[str] = None


class KnobsReadContract(BaseModel):
    """GET 손잡이 현재값 — UserGoal 5종 (읽기 전용, 쓰기는 20b)."""

    available: bool
    aggressiveness_offset: Optional[int] = None
    growth_boost: Optional[int] = None
    diversification_weight: Optional[str] = None
    concentration_limit: Optional[int] = None
    exploration_ratio: Optional[int] = None
