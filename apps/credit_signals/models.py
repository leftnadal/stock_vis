"""
credit_signals Phase 1 모델 (PR §3).

MacroSeriesHistory:
    FRED 관측치 영구 누적 원장. FRED ICE BofA 시리즈는 2026년 4월부터 최근 3년
    관측치만 제공하므로, 수집 즉시 여기에 영구 적재하는 것이 이 앱의 존재 이유
    절반이다. 데이터 삭제 로직을 절대 작성하지 않는다 (§10 영구 누적 원칙).

CreditSignalState:
    signal_key별 최신 파생 상태 1행. 소비처(Dashboard/Chain Sight/Thesis)는
    이 테이블만 읽는다.

EtfNavHistory:
    ETF NAV·시장가 영구 원장 (P2a-1). MacroSeriesHistory(FRED 전용)와 분리해
    앱 내 원장 의미 순수성을 유지한다. nav·price는 동일 (symbol, 거래일) 쌍이라
    2컬럼 1행이 write-time 거래일 정합을 강제한다.
"""
from django.db import models

from .constants import GRADE_CHOICES


class MacroSeriesHistory(models.Model):
    """FRED 관측치 영구 원장 (insert-only + revise-on-change)."""

    series_id = models.CharField(max_length=32, db_index=True)
    date = models.DateField()
    value = models.DecimalField(max_digits=12, decimal_places=4)
    # 최초 적재 시각 — revise가 일어나도 유지한다.
    ingested_at = models.DateTimeField(auto_now_add=True)
    # FRED가 과거값을 revise해 value가 갱신된 시각 (최초 적재 시 null).
    revised_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "macro_series_history"
        constraints = [
            models.UniqueConstraint(fields=["series_id", "date"], name="uniq_series_date"),
        ]
        indexes = [models.Index(fields=["series_id", "-date"])]

    def __str__(self) -> str:
        return f"{self.series_id}@{self.date}={self.value}"


class CreditSignalState(models.Model):
    """signal_key별 최신 파생 상태 (upsert, signal_key unique)."""

    signal_key = models.CharField(max_length=64, unique=True)  # 예: "HY_OAS"
    as_of = models.DateField()
    value = models.DecimalField(max_digits=12, decimal_places=4)
    z_score = models.DecimalField(max_digits=8, decimal_places=4, null=True)
    grade = models.CharField(max_length=8, choices=GRADE_CHOICES)
    # 창 크기, 구성 시리즈, 계산 파라미터 스냅샷
    detail = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "credit_signal_state"

    def __str__(self) -> str:
        return f"{self.signal_key}={self.grade}(z={self.z_score})"


class EtfNavHistory(models.Model):
    """
    ETF NAV·시장가 영구 원장 (P2a-1, insert-only + revise-on-change).

    정본 거래일(date) = quote timestamp의 ET 거래일. nav는 해당 거래일 행에
    함께 upsert하되, nav updatedAt이 정본 거래일과 1영업일 초과 괴리 시 수집을
    skip한다(자가 보정 금지 — 서비스 계층에서 처리). 삭제 로직 절대 금지(§10).

    파생 신호(*_NAV_DISCOUNT = (nav−price)/nav)는 여기 미적재 — compute-on-read
    (P2-0 파생 계약 복제, 원장 raw 순수성).
    """

    symbol = models.CharField(max_length=16, db_index=True)
    date = models.DateField()  # 정본 거래일 (quote timestamp ET 기준)
    nav = models.DecimalField(max_digits=12, decimal_places=4)
    price = models.DecimalField(max_digits=12, decimal_places=4)
    # 최초 적재 시각 — revise가 일어나도 유지한다.
    ingested_at = models.DateTimeField(auto_now_add=True)
    # nav/price가 갱신(revise)된 시각 (최초 적재 시 null).
    revised_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "etf_nav_history"
        constraints = [
            models.UniqueConstraint(fields=["symbol", "date"], name="uniq_etf_symbol_date"),
        ]
        indexes = [models.Index(fields=["symbol", "-date"])]

    def __str__(self) -> str:
        return f"{self.symbol}@{self.date} nav={self.nav} price={self.price}"
