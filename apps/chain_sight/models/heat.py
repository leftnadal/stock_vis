"""
Theme Heat 데이터 모델 (테마 온도계 + 수요 지지 축) — TH-1 독립 마이그레이션.

설계서: docs/chain_sight/theme_heat/theme_heat_design.md v1.2 FINAL §6.0~§6.6.
모든 필드는 설계서 §6 표를 그대로 따른다 (임의 필드 추가 금지). 산식·규칙은 설계서가
단일 진실이며, 충돌 시 설계서 우선.

7모델:
  §6.0 HeatEntity              — 측정 단위(추상 계층). Cycle 1 은 kind=sector 11행만.
  §6.1 ThemeHeatScore          — 과열 축(일간).
  §6.2 ThemeDemandScore        — 수요 축 DSS(주간, Cycle 2 선반영).
  §6.3 InsiderTransactionRecord— C2a 원장(전건 보존, 필터는 집계 계층).
  §6.4 ThemeEtfMap             — C4·C5 매핑.
  §6.5 ThemeFilingCount        — C2b(424B5 + IPO 이벤트).
  §6.6 EstimateSnapshot        — C8 원장(주간 스냅샷 → 60일 diff).

TH-3 추가:
  UniverseSnapshot             — 배치 일자별 유니버스 동결(모집단 drift 차단). 설계서 §6.0
                                 잠금장치 3("월 구성 동결")의 Cycle 1 sector 판(일간 동결).
"""

from django.db import models


class HeatEntity(models.Model):
    """
    온도의 단위를 가리키는 얇은 추상 계층 (설계서 §6.0, §12-1 C안).

    잠금장치:
      1. 도메인 필드는 kind/ref_id/constituent_policy 3개를 초과하지 않는다 (과설계 방지).
         → created_at 등 부가 컬럼 없음 (의도적).
      2. kind=theme 로직은 Cycle 1~2 에서 구현 금지 — 행 자체를 만들지 않는다.
      3. 테마 레인 개방 게이트 = 6개월 백테스트 + 월 1회 구성 동결 (§13).
    """

    KIND_SECTOR = "sector"
    KIND_THEME = "theme"
    KIND_CHOICES = [(KIND_SECTOR, "sector"), (KIND_THEME, "theme")]

    kind = models.CharField(
        max_length=16,
        choices=KIND_CHOICES,
        help_text="sector | theme — Cycle 1 은 sector 11행만 시드.",
    )
    ref_id = models.CharField(
        max_length=64,
        help_text="sector: GICS 섹터 키 / theme: (미래) 테마 노드 식별자.",
    )
    constituent_policy = models.CharField(
        max_length=16,
        help_text="sector: static / theme: (미래) monthly_frozen.",
    )

    class Meta:
        # (kind, ref_id) 유일 — 시드 멱등성 + FK 대상 안정성. (필드 아님 = 잠금장치 1 무위반)
        unique_together = [("kind", "ref_id")]
        indexes = [models.Index(fields=["kind"], name="heat_entity_kind_idx")]

    def __str__(self):
        return f"HeatEntity({self.kind}:{self.ref_id})"


class ThemeHeatScore(models.Model):
    """과열 축 (설계서 §6.1). 일간. 8성분 z-score 가중합 0~100."""

    STATUS_OVERHEATED = "overheated"
    STATUS_WARNING = "warning"
    STATUS_COOL = "cool"
    STATUS_CHOICES = [
        (STATUS_OVERHEATED, "overheated"),
        (STATUS_WARNING, "warning"),
        (STATUS_COOL, "cool"),
    ]

    theme = models.ForeignKey(
        HeatEntity,
        on_delete=models.PROTECT,
        db_column="theme_id",
        related_name="heat_scores",
        help_text="§6.0 HeatEntity.",
    )
    date = models.DateField(db_index=True)
    score = models.SmallIntegerField(help_text="0~100.")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES)
    components = models.JSONField(
        default=dict,
        help_text="성분별 {z, s, raw, missing_reason} 8건 — C2 는 C2a/C2b 분리, C8 은 z_mode 포함.",
    )
    evidence = models.JSONField(
        default=dict,
        help_text="근거 한 줄 생성용 상위 기여 성분 2건 (§10.3).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("theme", "date")]
        ordering = ["-date", "-score"]
        indexes = [models.Index(fields=["-date"], name="heat_score_date_desc_idx")]

    def __str__(self):
        return f"ThemeHeatScore({self.theme_id}, {self.date}, {self.score})"


class ThemeDemandScore(models.Model):
    """수요 축 DSS (설계서 §6.2). 주간(금요일 기준일). Cycle 2 선반영."""

    STATUS_SUPPORTED = "supported"
    STATUS_NEUTRAL = "neutral"
    STATUS_DETACHED = "detached"
    STATUS_NOT_COMPUTED = "not_computed"
    STATUS_CHOICES = [
        (STATUS_SUPPORTED, "supported"),
        (STATUS_NEUTRAL, "neutral"),
        (STATUS_DETACHED, "detached"),
        (STATUS_NOT_COMPUTED, "not_computed"),
    ]

    theme = models.ForeignKey(
        HeatEntity,
        on_delete=models.PROTECT,
        db_column="theme_id",
        related_name="demand_scores",
    )
    date = models.DateField(db_index=True, help_text="주간(금요일 기준일).")
    score = models.SmallIntegerField(null=True, blank=True, help_text="not_computed 시 NULL.")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES)
    components = models.JSONField(
        default=dict, help_text="테마별 오버라이드 구성 그대로 기록."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("theme", "date")]
        ordering = ["-date"]

    def __str__(self):
        return f"ThemeDemandScore({self.theme_id}, {self.date}, {self.status})"


class InsiderTransactionRecord(models.Model):
    """
    C2a 내부자 원장 (설계서 §6.3).

    원본 레코드는 전건 보존(transaction_type 공란 포함) — 방어 필터는 적재가 아닌
    집계(조회) 계층에서 적용한다 (§5.1). dedup_key 로 upsert 멱등.
    """

    symbol = models.CharField(max_length=16, db_index=True)
    reporting_cik = models.CharField(max_length=16, blank=True)
    company_cik = models.CharField(max_length=16, blank=True)
    filing_date = models.DateField(db_index=True)
    transaction_date = models.DateField(db_index=True)
    transaction_type = models.CharField(
        max_length=32,
        blank=True,
        help_text="S-Sale, P-Purchase, A-Award, M-Exempt, F-InKind, G-Gift, 공란 — 전건 보존.",
    )
    securities_transacted = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True
    )
    price = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    type_of_owner = models.CharField(max_length=64, blank=True)
    direct_or_indirect = models.CharField(max_length=8, blank=True)
    acq_or_disp = models.CharField(max_length=8, blank=True)
    sec_url = models.TextField(blank=True, help_text="SEC 원문 — 교차검증 훅(§8)·감사 추적용.")
    raw = models.JSONField(default=dict, help_text="FMP 응답 원본.")
    dedup_key = models.CharField(
        max_length=64,
        unique=True,
        help_text="hash(symbol, reporting_cik, transaction_date, transaction_type, "
        "securities_transacted, price).",
    )

    class Meta:
        ordering = ["-filing_date"]
        indexes = [
            models.Index(fields=["symbol", "-filing_date"], name="insider_sym_date_idx"),
        ]

    def __str__(self):
        return f"InsiderTransactionRecord({self.symbol}, {self.transaction_date}, {self.transaction_type})"


class ThemeEtfMap(models.Model):
    """C4·C5 매핑 (설계서 §6.4). role=primary(플로우)/leveraged(투기)."""

    ROLE_PRIMARY = "primary"
    ROLE_LEVERAGED = "leveraged"
    ROLE_CHOICES = [(ROLE_PRIMARY, "primary"), (ROLE_LEVERAGED, "leveraged")]

    theme = models.ForeignKey(
        HeatEntity,
        on_delete=models.PROTECT,
        db_column="theme_id",
        related_name="etf_maps",
    )
    etf_symbol = models.CharField(max_length=16)
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    leverage_factor = models.SmallIntegerField(default=1, help_text="1, 2, 3.")
    active = models.BooleanField(default=True, help_text="상장폐지 대응.")

    class Meta:
        unique_together = [("theme", "etf_symbol", "role")]
        ordering = ["theme", "role"]

    def __str__(self):
        return f"ThemeEtfMap({self.theme_id}, {self.etf_symbol}, {self.role})"


class ThemeFilingCount(models.Model):
    """
    C2b 발행 신호 원장 (설계서 §6.5).

    정확 일치 필터 통과분만: 424B5(기상장사 2차발행) + IPO 이벤트.
    (S-1/424B4 는 §5.2 재정의로 폐기 — symbol 결측 60~62%.) dedup_key 로 upsert 멱등.
    """

    SOURCE_FMP = "fmp"

    symbol = models.CharField(max_length=16, blank=True, db_index=True)
    filing_date = models.DateField(db_index=True)
    form_type = models.CharField(
        max_length=16, help_text="424B5 또는 IPO 이벤트 마커."
    )
    exchange = models.CharField(
        max_length=16, blank=True, help_text="IPO 레코드용 — NYSE/NASDAQ 필터 (§5.2-3)."
    )
    source = models.CharField(
        max_length=8,
        default=SOURCE_FMP,
        help_text="fmp 고정 (EDGAR 폴백 불요 확정, 필드는 이음새로 유지).",
    )
    dedup_key = models.CharField(
        max_length=64,
        unique=True,
        help_text="hash(symbol, cik, accession) — accession 은 link 에서 추출.",
    )

    class Meta:
        ordering = ["-filing_date"]
        indexes = [
            models.Index(fields=["form_type", "-filing_date"], name="filing_type_date_idx"),
        ]

    def __str__(self):
        return f"ThemeFilingCount({self.symbol or '—'}, {self.form_type}, {self.filing_date})"


class EstimateSnapshot(models.Model):
    """
    C8 추정치 리비전 원장 (설계서 §6.6). 주간(금요일) 스냅샷 → 60일 diff.

    정합성 메모: 설계서 표는 unique_together 를 (symbol, snapshot_date) 로 표기하나,
    fiscal_year 가 "당기·차기 연도별 행"(스냅샷당 복수 행)이므로 유일 제약의 정합 해석은
    (symbol, snapshot_date, fiscal_year) 이다. 설계서 owner 확인 대상 (보고서 명시).
    """

    symbol = models.CharField(max_length=16, db_index=True)
    snapshot_date = models.DateField(db_index=True, help_text="주간(금요일). diff 의 시간축.")
    fiscal_year = models.SmallIntegerField(help_text="당기·차기 연도별 행.")
    eps_avg = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    eps_high = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    eps_low = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    num_analysts_eps = models.IntegerField(
        null=True, blank=True, help_text="C8 신뢰 가중."
    )
    revenue_avg = models.DecimalField(
        max_digits=22, decimal_places=2, null=True, blank=True, help_text="보조."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("symbol", "snapshot_date", "fiscal_year")]
        ordering = ["symbol", "-snapshot_date", "fiscal_year"]

    def __str__(self):
        return f"EstimateSnapshot({self.symbol}, {self.snapshot_date}, FY{self.fiscal_year})"


class UniverseSnapshot(models.Model):
    """
    배치 일자별 유니버스 동결 (TH-3).

    문제: 성분 z(특히 C2a 내부자 테마 합산)의 모집단 = "그날의 S&P 500 구성종목"인데,
    SP500Constituent 는 월 1회 동기화되며 is_active 가 변한다. 모집단이 소리 없이
    바뀌면 z 히스토리가 오염된다 (설계서 §6.0 잠금장치 3 "구성 동결"과 동일 문제 —
    z 시계열 보호). 해결: 매 배치가 그날 조회한 유니버스를 스냅샷으로 박고, 이후 모든
    크로스섹셔널/시계열 z 의 모집단은 배치 일자 스냅샷을 참조한다.

    설계서 §6.0 은 테마 레인의 "월 1회 구성 동결"을 명시한다. Cycle 1 은 sector 단위라
    구성 = S&P 500 유니버스이며, 본 테이블이 그 일간 동결 원장이다.

    필드는 (batch_date, symbols) 만 — 지시서 스펙 "batch_date, symbol 배열" 정합.
    """

    batch_date = models.DateField(
        unique=True, db_index=True, help_text="배치 실행 일자 (유니버스 동결 시점)."
    )
    symbols = models.JSONField(
        default=list,
        help_text="그날 조회한 유니버스 심볼 배열 (SP500 active − '.' 심볼). 모집단 참조원.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-batch_date"]

    def __str__(self):
        return f"UniverseSnapshot({self.batch_date}, n={len(self.symbols or [])})"


class EtfSnapshot(models.Model):
    """
    C4 ETF 플로우 **원료 시계** (TH-7c, 결정11=A).

    C4 산식 = Σ(Δshares_out × NAV) 20일 이동합의 3년 z (설계 앵커 §2). FMP Starter 는
    shares_outstanding 의 **이력을 제공하지 않아**(TH-7 프로브: historical/shares_float 404,
    etf/holdings 402, v3 legacy 403 — 현재 스냅샷만 가용), EstimateSnapshot(§6.6) 전례처럼
    **일간 스냅샷을 직접 축적**해 diff 시계열을 자체 구성한다. 이 모델은 원료만 적립하며,
    산식·z·콜드스타트(3년 σ 부재 대응)는 TH-C4-COLDSTART 비준 후 별도 배선한다.
    """

    symbol = models.CharField(max_length=16, db_index=True)
    snapshot_date = models.DateField(db_index=True, help_text="수집 기준일. diff 의 시간축.")
    shares_outstanding = models.DecimalField(
        max_digits=24, decimal_places=2, null=True, blank=True,
        help_text="FMP /stable/shares-float outstandingShares.",
    )
    nav = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True,
        help_text="FMP /stable/etf/info nav.",
    )
    aum = models.DecimalField(
        max_digits=24, decimal_places=2, null=True, blank=True,
        help_text="FMP /stable/etf/info assetsUnderManagement (보조).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("symbol", "snapshot_date")]
        ordering = ["symbol", "-snapshot_date"]

    def __str__(self):
        return f"EtfSnapshot({self.symbol}, {self.snapshot_date})"
