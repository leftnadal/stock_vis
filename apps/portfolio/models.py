"""
Stock-Vis Portfolio Coach — Django Models
==========================================

D-0a 리팩토링 (2026-04-24):
  - Wallet / Portfolio 개념 분리 (결정 I2-a-refined)
  - WalletSnapshot 도입 (결정 A1)
  - Coach 대화/의사결정 모델 추가 (ChatSession / Message / Decision)
  - Holding / CandidateHolding 제거

최종 모델 구성 (13개):
  1. Wallet                — 자산 지갑 (실제 보유 집합)
  2. WalletHolding         — 보유 종목 (기존 Holding 이관)
  3. WalletSnapshot        — 시점별 Wallet 스냅샷
  4. Portfolio             — 분석 대상 슬라이스 (의미 재정의)
  5. AnalysisRun           — 분석 실행 단위 (+ wallet_snapshot_at_execution)
  6. MetricResult          — 지표별 결과
  7. DiagnosticCard        — 진단 카드 (4요소)
  8. LLMComment            — 지표별 LLM 코멘트
  9. StoredAnalysis        — Saved/Temp 통합 (+ 저장시점 return_breakdown 2개)
 10. PercentileCache       — 퍼센타일 배치 캐시
 11. ChatSession           — Coach 대화 세션
 12. Message               — 대화 raw (결정 D3)
 13. Decision              — 구조화된 의사결정 (결정 D3)

참조:
  - docs/portfolio/design/wallet-portfolio-architecture-v1.md
  - docs/portfolio/design/coach-llm-design-v1.md
  - docs/portfolio/design/return-tracking-design-v1.md
  - docs/portfolio/intructions/d-0a-instructions.md
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

# ============================================================
# 1. Wallet — 자산 지갑 (실제 보유 집합)
# ============================================================


class Wallet(models.Model):
    """
    사용자의 실제 보유 종목 전체를 담는 자산 지갑.

    - MVP는 사용자당 Wallet 1개 (unique constraint 없이 1:N 열어둠)
    - Phase 2에서 다중 Wallet 지원 가능
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallets",
    )
    name = models.CharField(
        max_length=100,
        default="My Wallet",
        help_text="자산 지갑 이름. MVP는 사용자당 1개.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["user"])]

    def __str__(self):
        return f"{self.name} ({self.user})"


# ============================================================
# 2. WalletHolding — 보유 종목
# ============================================================


class WalletHolding(models.Model):
    """
    Wallet 내 실제 보유 종목.
    RV2-b 정책: sector/industry 필드는 stocks.Stock에 위치하므로
    여기서는 캐시하지 않는다. 접근은 `wallet_holding.stock.sector`.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="holdings",
    )
    stock = models.ForeignKey(
        "stocks.Stock",
        on_delete=models.PROTECT,
        related_name="wallet_holdings",
    )

    # ---- 매수 정보 ----
    shares = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        help_text="보유 수량 (소수점: 분할 매수)",
    )
    avg_cost = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        help_text="평균 매수 단가 (USD). Phase 2 Trade 모델 도입 시 자동 계산.",
    )
    first_bought_at = models.DateField(
        help_text="최초 매수일",
    )
    acquisition_fx_rate = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text=(
            "매수 시점 USD/KRW 환율, 사용자 정정 가능 (SLICE19B). "
            "null이면 매수일(first_bought_at) 환율로 근사."
        ),
    )

    # ---- 투자 근거 (Thesis Y1) ----
    investment_thesis = models.TextField(
        blank=True,
        help_text="매수 시 투자 근거. Coach가 대화 맥락으로 활용.",
    )

    # ---- 시뮬레이션 스냅샷 ----
    buy_snapshot = models.JSONField(
        null=True,
        blank=True,
        help_text="매수 확정 시점의 Wallet 구성 스냅샷 (thesis 집중도, 섹터 비중 등).",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["wallet"]),
            models.Index(fields=["wallet", "stock"]),
        ]
        unique_together = [("wallet", "stock")]

    def __str__(self):
        return f"{self.stock} × {self.shares} in {self.wallet.name}"


# ============================================================
# 3. WalletSnapshot — 시점별 Wallet 스냅샷 (결정 A1)
# ============================================================


class WalletSnapshot(models.Model):
    """
    Wallet의 특정 시점 상태 기록.

    트리거:
      - "initial_setup":   Wallet 첫 설정 시 자동 생성
      - "saved_analysis":  Saved Analysis 저장 시 자동 생성
      - "periodic_batch":  Phase 2 주기 배치 (MVP 미사용)
      - "manual":          사용자 수동 트리거

    용도:
      - Coach 시계열 변화 분석 (W2.5 시나리오 A)
      - Phase 2 사후 비교의 시계열 데이터
    """

    TRIGGER_CHOICES = [
        ("initial_setup", "Initial Setup"),
        ("saved_analysis", "Saved Analysis"),
        ("periodic_batch", "Periodic Batch (Phase 2)"),
        ("manual", "Manual"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="snapshots",
    )
    triggered_by = models.CharField(
        max_length=30,
        choices=TRIGGER_CHOICES,
        help_text="스냅샷 생성 트리거.",
    )
    triggered_by_ref = models.UUIDField(
        null=True,
        blank=True,
        help_text="트리거한 StoredAnalysis 등의 ID (선택).",
    )
    holdings_json = models.JSONField(
        help_text=(
            "스냅샷 시점의 WalletHolding 구조화 복사. "
            "[{stock_id, shares, avg_cost, sector, industry, market_value}, ...]"
        ),
    )
    aggregate_metrics = models.JSONField(
        help_text=(
            "집계 지표. "
            "{total_value, sector_distribution, industry_distribution, holding_count}"
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["wallet", "-created_at"]),
            models.Index(fields=["triggered_by"]),
        ]

    def __str__(self):
        return (
            f"Snapshot {self.id!s:.8} | {self.wallet.name} | {self.created_at:%Y-%m-%d}"
        )


# ============================================================
# 4. Portfolio — 분석 대상 슬라이스 (의미 재정의)
# ============================================================


class Portfolio(models.Model):
    """
    분석을 위해 선택된 WalletHolding의 부분집합.

    - Wallet의 "뷰" 성격 (컨설턴트 비유 참조)
    - 이름을 붙여 저장 (named) 또는 일회성 (temporary)
    - AnalysisRun은 Portfolio 기준으로 실행
    - H3 정책: wallet_holding_ids는 참조 링크, 실행 시점에 자동 필터링
    """

    SAVE_TYPE_CHOICES = [
        ("named", "Named"),
        ("temporary", "Temporary"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="portfolios",
    )
    name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="분석 그룹 이름. null이면 임시 그룹 (일회성).",
    )
    description = models.TextField(
        blank=True,
        help_text="이 분석 묶음의 목적/근거.",
    )
    wallet_holding_ids = models.JSONField(
        help_text=(
            "선택된 WalletHolding UUID 리스트. "
            "매도된 종목은 effective_holdings()에서 자동 필터링 (H3 정책)."
        ),
    )
    save_type = models.CharField(
        max_length=20,
        choices=SAVE_TYPE_CHOICES,
        default="temporary",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["wallet", "save_type"]),
            models.Index(fields=["wallet", "name"]),
        ]

    def __str__(self):
        label = self.name or f"(temporary {self.id!s:.8})"
        return f"{label} in {self.wallet.name}"

    def effective_holdings(self):
        """
        실행 시점에 유효한 WalletHolding만 필터링 (결정 H3).
        wallet_holding_ids에 있지만 Wallet에서 삭제된 종목은 자동 제외.
        """
        return WalletHolding.objects.filter(
            id__in=self.wallet_holding_ids,
            wallet=self.wallet,
        )


# ============================================================
# 5. AnalysisRun — 분석 실행 단위
# ============================================================


class AnalysisRun(models.Model):
    """
    분석 실행 단위.
    Portfolio + Preset 조합으로 1회 실행 → N개 MetricResult 생성.
    is_finalized=True 이후 수정 불가 (불변성 보장).
    """

    class StatusBadge(models.TextChoices):
        """5단계 상태 뱃지 — 내부 용어 (UI 언어는 프론트에서 매핑)"""

        EXCELLENT = "excellent", "Excellent"
        GOOD = "good", "Good"
        MODERATE = "moderate", "Moderate"
        WEAK = "weak", "Weak"
        CRITICAL = "critical", "Critical"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name="analysis_runs",
    )
    # preset_id는 코드 상수의 키값. FK가 아닌 CharField.
    preset_id = models.CharField(
        max_length=50,
        help_text="프리셋 식별자 (코드 상수 키, 예: buffett_quality_value)",
    )

    # ---- 버전 번들 (결정 M-4) ----
    preset_version = models.CharField(max_length=20, default="1.0")
    metric_version = models.CharField(max_length=20, default="1.0")
    scoring_version = models.CharField(max_length=20, default="1.0")
    prompt_version = models.CharField(max_length=20, default="1.0")
    universe_version = models.CharField(max_length=20, default="1.0")

    # ---- 분석 메타 ----
    portfolio_hash = models.CharField(
        max_length=64,
        help_text="포트폴리오 구성 해시 (종목+비중 기반, 중복 분석 방지용)",
    )
    status_badge = models.CharField(
        max_length=10,
        choices=StatusBadge.choices,
        blank=True,
        help_text="5단계 종합 상태 (LLM 또는 스코어링 엔진이 부여)",
    )
    one_line_summary = models.TextField(
        blank=True,
        help_text="한 줄 진단 요약 (LLM 생성)",
    )

    # ---- Wallet 스냅샷 연결 (RV4-b) ----
    wallet_snapshot_at_execution = models.ForeignKey(
        WalletSnapshot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analyses_at_time",
        help_text="실행 시점 Wallet 스냅샷 (Saved로 승격 시 자동 생성).",
    )

    # ---- 불변성 플래그 ----
    is_finalized = models.BooleanField(
        default=False,
        help_text="True 이후 수정 불가",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["portfolio", "preset_id", "-created_at"]),
            models.Index(fields=["preset_id", "prompt_version"]),
        ]

    def __str__(self):
        return f"Run {self.id!s:.8} | {self.preset_id} | {self.created_at:%Y-%m-%d}"

    def save(self, *args, **kwargs):
        # 불변성 보장: finalized된 run의 수정 차단
        if self.pk:
            try:
                existing = AnalysisRun.objects.get(pk=self.pk)
                if existing.is_finalized and not kwargs.pop("_force_save", False):
                    raise ValidationError(
                        "Cannot modify a finalized AnalysisRun. "
                        "Create a new run instead."
                    )
            except AnalysisRun.DoesNotExist:
                pass
        super().save(*args, **kwargs)


# ============================================================
# 6. MetricResult — 지표별 결과
# ============================================================


class MetricResult(models.Model):
    """
    지표별 분석 결과.
    AnalysisRun 1 : N MetricResult (종목 수 × 지표 수).
    """

    class DataStatus(models.TextChoices):
        """결측치 5가지 상태 분류"""

        OK = "ok", "정상"
        MISSING = "missing", "데이터 없음"
        NOT_APPLICABLE = "not_applicable", "해당 없음"
        DELAYED = "delayed", "갱신 대기"
        INSUFFICIENT = "insufficient", "제한적 데이터"
        UNSTABLE = "unstable", "일시적 왜곡 가능"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis_run = models.ForeignKey(
        AnalysisRun,
        on_delete=models.CASCADE,
        related_name="metric_results",
    )
    stock = models.ForeignKey(
        "stocks.Stock",
        on_delete=models.PROTECT,
        related_name="metric_results",
    )
    metric_id = models.CharField(
        max_length=50,
        help_text="지표 식별자 (코드 상수 키, 예: roic, pe_ratio)",
    )

    # ---- 결과 값 ----
    raw_value = models.FloatField(
        null=True,
        blank=True,
        help_text="원시 값 (예: ROIC 28.3%)",
    )
    percentile = models.FloatField(
        null=True,
        blank=True,
        help_text="산업 대비 퍼센타일 (0~100)",
    )
    level_tag = models.IntegerField(
        null=True,
        blank=True,
        help_text="5단계 레벨 (1=최하 ~ 5=최상)",
    )

    # ---- 비교군 맥락 (JSONField) ----
    comparison_meta = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "퍼센타일 산출 맥락. 예: "
            '{"comparison_group": "industry", "group_code": "Technology Hardware", '
            '"sample_size": 47, "used_fallback": false, '
            '"fallback_from": null, "percentile_date": "2026-04-15"}'
        ),
    )

    # ---- 데이터 상태 ----
    data_status = models.CharField(
        max_length=20,
        choices=DataStatus.choices,
        default=DataStatus.OK,
    )

    class Meta:
        indexes = [
            models.Index(fields=["analysis_run", "metric_id"]),
            models.Index(fields=["stock", "metric_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["analysis_run", "stock", "metric_id"],
                name="unique_metric_result_per_run_stock",
            ),
        ]

    def __str__(self):
        return f"{self.metric_id} | {self.stock} | {self.raw_value}"

    def save(self, *args, **kwargs):
        # 소속 run이 finalized면 저장 차단
        if self.analysis_run_id:
            try:
                run = AnalysisRun.objects.get(pk=self.analysis_run_id)
                if run.is_finalized:
                    raise ValidationError(
                        "Cannot add/modify MetricResult on a finalized AnalysisRun."
                    )
            except AnalysisRun.DoesNotExist:
                pass

        # metric_id 유효성 검증 (코드 상수와 대조)
        from apps.portfolio.metrics.definitions.metrics import (
            METRICS,  # lazy import to avoid circular
        )

        if self.metric_id not in METRICS:
            raise ValidationError(
                f"Unknown metric_id: '{self.metric_id}'. "
                f"Must be one of: {list(METRICS.keys())}"
            )

        super().save(*args, **kwargs)


# ============================================================
# 7. DiagnosticCard — 진단 카드 (4요소)
# ============================================================


class DiagnosticCard(models.Model):
    """
    진단 카드 — 4요소 구조.
    AnalysisRun 당 최대 3개, priority 1~3.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis_run = models.ForeignKey(
        AnalysisRun,
        on_delete=models.CASCADE,
        related_name="diagnostic_cards",
    )
    priority = models.IntegerField(
        help_text="카드 우선순위 (1=가장 중요, 최대 3)",
    )
    target_metric_id = models.CharField(
        max_length=50,
        help_text="진단 대상 지표 (또는 복합 이슈의 경우 대표 지표)",
    )
    target_stock = models.ForeignKey(
        "stocks.Stock",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="diagnostic_cards",
        help_text="진단 대상 종목 (포트폴리오 레벨 진단이면 null)",
    )

    # ---- 4요소 ----
    problem_statement = models.TextField(
        help_text="무엇이 문제인가 (LLM 생성)",
    )
    comparison_basis = models.TextField(
        help_text="어떤 기준 대비인가 (LLM 생성)",
    )
    preset_relevance = models.TextField(
        help_text="이 프리셋에서 왜 중요한가 (LLM 생성)",
    )
    exception_tradeoff = models.TextField(
        blank=True,
        help_text="예외/트레이드오프가 있는가 (LLM 생성)",
    )

    # ---- 생성 메타 ----
    generated_by = models.CharField(
        max_length=20,
        help_text="생성에 사용된 prompt_version",
    )

    class Meta:
        ordering = ["priority"]
        constraints = [
            models.UniqueConstraint(
                fields=["analysis_run", "priority"],
                name="unique_card_priority_per_run",
            ),
        ]

    def __str__(self):
        return f"Card #{self.priority} | {self.target_metric_id} | Run {self.analysis_run_id!s:.8}"

    def save(self, *args, **kwargs):
        if self.priority not in (1, 2, 3):
            raise ValidationError("DiagnosticCard priority must be 1, 2, or 3.")
        if self.analysis_run_id:
            try:
                run = AnalysisRun.objects.get(pk=self.analysis_run_id)
                if run.is_finalized:
                    raise ValidationError(
                        "Cannot add/modify DiagnosticCard on a finalized AnalysisRun."
                    )
            except AnalysisRun.DoesNotExist:
                pass
        super().save(*args, **kwargs)


# ============================================================
# 8. LLMComment — 지표별 LLM 코멘트
# ============================================================


class LLMComment(models.Model):
    """
    지표별 LLM 코멘트.
    AnalysisRun × metric_id × stock 단위로 생성.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis_run = models.ForeignKey(
        AnalysisRun,
        on_delete=models.CASCADE,
        related_name="llm_comments",
    )
    stock = models.ForeignKey(
        "stocks.Stock",
        on_delete=models.PROTECT,
        related_name="llm_comments",
    )
    metric_id = models.CharField(
        max_length=50,
        help_text="코멘트 대상 지표",
    )
    comment_text = models.TextField(
        help_text="LLM 생성 코멘트",
    )
    generated_by = models.CharField(
        max_length=20,
        help_text="생성에 사용된 prompt_version",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["analysis_run", "stock", "metric_id"],
                name="unique_comment_per_run_stock_metric",
            ),
        ]

    def __str__(self):
        return f"Comment | {self.metric_id} | {self.stock} | Run {self.analysis_run_id!s:.8}"

    def save(self, *args, **kwargs):
        if self.analysis_run_id:
            try:
                run = AnalysisRun.objects.get(pk=self.analysis_run_id)
                if run.is_finalized:
                    raise ValidationError(
                        "Cannot add/modify LLMComment on a finalized AnalysisRun."
                    )
            except AnalysisRun.DoesNotExist:
                pass
        super().save(*args, **kwargs)


# ============================================================
# 9. StoredAnalysis — Saved/Temp 통합 (+ RV4-b 저장시점 수익률)
# ============================================================


class StoredAnalysis(models.Model):
    """
    저장된 분석 — Saved(영구) + Temp(임시 FIFO) 통합.
    save_type 전환으로 임시→영구 승격.
    """

    class SaveType(models.TextChoices):
        SAVED = "saved", "영구 저장"
        TEMP = "temp", "임시 저장"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis_run = models.OneToOneField(
        AnalysisRun,
        on_delete=models.CASCADE,
        related_name="stored_analysis",
    )
    save_type = models.CharField(
        max_length=5,
        choices=SaveType.choices,
        default=SaveType.TEMP,
    )
    user_memo = models.TextField(
        blank=True,
        help_text="사용자 메모 (saved 타입에서만 의미 있음)",
    )
    dedup_key = models.CharField(
        max_length=120,
        blank=True,
        help_text="portfolio_hash:preset_id 복합 키 (temp 중복 방지)",
    )

    # ---- RV4-b: 저장 시점 수익률 breakdown (불변) ----
    portfolio_return_breakdown = models.JSONField(
        null=True,
        blank=True,
        help_text="저장 시점 Portfolio 수익률 breakdown. 불변.",
    )
    wallet_return_breakdown = models.JSONField(
        null=True,
        blank=True,
        help_text="저장 시점 Wallet 수익률 breakdown. 불변.",
    )

    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-saved_at"]
        indexes = [
            models.Index(fields=["save_type", "-saved_at"]),
            models.Index(fields=["dedup_key"]),
        ]

    def __str__(self):
        return f"[{self.save_type}] Run {self.analysis_run_id!s:.8} | {self.saved_at:%Y-%m-%d}"

    def promote_to_saved(self, memo: str = ""):
        """임시 저장 → 영구 저장 전환."""
        self.save_type = self.SaveType.SAVED
        self.user_memo = memo
        self.save()
        # 연결된 AnalysisRun도 finalize
        run = self.analysis_run
        run.is_finalized = True
        run.save(_force_save=True)


# ============================================================
# 10. PercentileCache — 퍼센타일 배치 캐시
# ============================================================


class PercentileCache(models.Model):
    """
    퍼센타일 배치 캐시.
    업종 × 지표 × 날짜 단위로 분포 저장.
    values는 {ticker: raw_value} dict 형태.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    metric_id = models.CharField(max_length=50)
    industry_code = models.CharField(
        max_length=100,
        help_text="산업 분류 코드 (FMP industry 기준)",
    )
    date = models.DateField(
        help_text="배치 기준일",
    )
    values = models.JSONField(
        help_text='업종 내 종목별 원시 값. 예: {"AAPL": 28.3, "MSFT": 24.1}',
    )
    sample_size = models.IntegerField(
        help_text="표본 수 (= len(values), 검증용)",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["metric_id", "industry_code", "date"],
                name="unique_percentile_cache",
            ),
        ]
        indexes = [
            models.Index(fields=["metric_id", "industry_code", "-date"]),
        ]

    def __str__(self):
        return f"Cache | {self.metric_id} | {self.industry_code} | {self.date}"


# ============================================================
# 11. ChatSession — Coach 대화 세션
# ============================================================


class ChatSession(models.Model):
    """
    Coach와의 대화 세션.
    하나의 AnalysisRun에 연결된 대화 = 하나의 ChatSession.
    AnalysisRun 삭제에는 느슨한 연결 (SET_NULL).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_sessions",
    )
    analysis_run = models.ForeignKey(
        AnalysisRun,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_sessions",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    session_summary = models.TextField(
        blank=True,
        help_text="Tier 2 요약. 세션 종료 시 생성.",
    )

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["user", "-started_at"]),
            models.Index(fields=["analysis_run"]),
        ]

    def __str__(self):
        return f"Session {self.id!s:.8} | {self.user} | {self.started_at:%Y-%m-%d}"


# ============================================================
# 12. Message — 대화 원본 (결정 D3 raw)
# ============================================================


class Message(models.Model):
    """
    ChatSession 하위의 개별 메시지.
    사용자 메시지 + Coach 응답 모두 raw로 저장.
    """

    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
    )
    content = models.TextField()
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="예: 조정 요청 시 overrides_json, 진단 카드 생성 시 cards_json.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["session", "created_at"]),
        ]

    def __str__(self):
        preview = self.content[:40].replace("\n", " ")
        return f"[{self.role}] {preview}..."


# ============================================================
# 13. Decision — 구조화된 의사결정 (결정 D3)
# ============================================================


class Decision(models.Model):
    """
    사용자의 의사결정 이벤트.
    Chat 대화 또는 명시적 액션에서 LLM이 추출.
    raw(Message)와 extracted(Decision)의 하이브리드 구조.
    """

    DECISION_TYPE_CHOICES = [
        ("preset_adjustment", "Preset Adjustment (Level 1)"),
        ("preset_switch", "Preset Switch"),
        ("holding_change_intent", "Holding Change Intent"),
        ("thesis_note", "Thesis Note (Wallet Holding)"),
        ("portfolio_creation", "Portfolio (Analysis Group) Creation"),
        ("preference_signal", "Preference Signal (Subjective)"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="decisions",
    )
    decision_type = models.CharField(
        max_length=40,
        choices=DECISION_TYPE_CHOICES,
    )
    decision_at = models.DateTimeField()
    context_analysis_run = models.ForeignKey(
        AnalysisRun,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decisions",
    )
    rationale_text = models.TextField(
        help_text="사용자가 남긴 자연어 근거 또는 LLM이 대화에서 추출한 요약.",
    )
    structured_payload = models.JSONField(
        help_text=(
            "의사결정 유형별 구조화 데이터. "
            "예: preset_adjustment 이면 {metric_id, old_threshold, new_threshold}"
        ),
    )
    source_messages = models.JSONField(
        default=list,
        blank=True,
        help_text="추출 출처 Message UUID 리스트.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-decision_at"]
        indexes = [
            models.Index(fields=["user", "-decision_at"]),
            models.Index(fields=["decision_type"]),
        ]

    def __str__(self):
        return f"Decision[{self.decision_type}] | {self.user} | {self.decision_at:%Y-%m-%d}"


# ============================================================
# Slice 18-R — 사용자 상태 그릇 신규 모델 (ADDITIVE, models_my.py)
# Django 앱 모델 발견용 재노출. 정의는 models_my.py 참조 (DECISIONS SLICE18R).
# SLICE19C: PortfolioSnapshot·AdvisoryRun 원장 2종 재노출.
# ============================================================
from apps.portfolio.models_my import (  # noqa: E402,F401
    AdvisoryRun,
    CashBalance,
    PortfolioSnapshot,
    ScopedManager,
    UserGoal,
)
