# PR-A3 위임 프롬프트 — 카드 스냅샷 3개 (marketpulse 앱 확장)

> **메타 정보**
>
> - PR ID: PR-A3
> - 영역: marketpulse 앱에 카드 스냅샷 모델 3개 추가
> - 의존 PR: A1 (FK: `SectorFlowSnapshot.market_index → MarketIndex`), A2 (DB 순서)
> - 후속 의존: PR-F(Breadth), PR-G(SectorFlow), PR-H(Concentration)
> - 견적: 4.8h ± 0.6h (PERT P50, 3분리 반영)
> - 결정 패키지: **A3-A.Ⅱ(Migration 3분리, A1과 동일) + A3-B.Ⅰ(빈 테이블만)**
> - **백필 command 불필요** (A1과 결정적 차이 — 데이터 적재는 PR-F/G/H 책임)
> - 동결 결정 인용: D2(long-format) · D6(universe SPY only) · D8(PROTECT) · is_finalized

---

## §1. 컨텍스트

### 1.1 프로젝트 배경

- 프로젝트: **Market Pulse v2 Phase 1**
- 위치: `backend/marketpulse/` (PR-A2가 scaffold한 앱에 추가)
- 의존: PR-A1(MarketIndex 20 row + sector_group), PR-A2(marketpulse 앱 0001_initial)
- 본 PR-A3는 **스키마만** 추가, 데이터 적재는 후속 PR(F/G/H)이 책임.

### 1.2 본 PR의 목표

PR-A2가 scaffold한 marketpulse 앱에 카드 스냅샷 3개 모델을 **3개의 독립 migration 파일**로 추가:

| Migration | 모델                    | 책임                                            | 후속 PR | 의존                    |
| --------- | ----------------------- | ----------------------------------------------- | ------- | ----------------------- |
| **0002**  | `BreadthSnapshot`       | Card B 일별 참여도, universe 필드, is_finalized | PR-F    | A2의 0001               |
| **0003**  | `SectorFlowSnapshot`    | Card C·D long-format, FK PROTECT, is_finalized  | PR-G    | A1의 MarketIndex + 0002 |
| **0004**  | `ConcentrationSnapshot` | Card B 펼침·R02 입력, is_finalized              | PR-H    | 0003                    |

**A1과의 결정적 차이**: PR-A1은 EconomicIndicator 11 + MarketIndex 20을 자체 시드해야 했으나, PR-A3는 **빈 테이블만**. 데이터 적재는 PR-F/G/H가 책임 → **백필 command 자체가 불필요**.

### 1.3 의존성

#### 1.3.1 상위 PR 의존

- **PR-A1**: `MarketIndex` 모델 + `sector_group` 컬럼 + 11 섹터 ETF row (`XLF`, `XLK`, ..., `XLC`) — `SectorFlowSnapshot.market_index` FK가 의존
- **PR-A2**: marketpulse 앱 scaffold (`0001_initial`) — 본 PR의 마이그레이션이 dependency로 명시

#### 1.3.2 의존성 체인 (3분리)

```
A1: market.0004_seed_market_indices  ← MarketIndex.sector_group + row
A2: marketpulse.0001_initial          ← marketpulse 앱 scaffold
A3:
  marketpulse.0002_add_breadth         deps: marketpulse.0001
  marketpulse.0003_add_sector_flow     deps: marketpulse.0002 + market.0004
  marketpulse.0004_add_concentration   deps: marketpulse.0003
```

**SectorFlowSnapshot의 cross-app 의존**: `market.0004` (PR-A1)와 `marketpulse.0002` 두 곳에 의존. Django의 `dependencies` 리스트에 둘 다 명시.

### 1.4 결정 패키지의 의미

#### 1.4.1 A3-A.Ⅱ Migration 3분리 (A1과 동일 패턴)

PR-A1의 A-Ⅲ 결정과 완전 일관:

- **부분 롤백 가능**: `migrate marketpulse 0003`으로 ConcentrationSnapshot만 reverse, 나머지 2개 유지
- **단계별 헬스체크**: `migrate 0002` → check Breadth → `migrate 0003` → check SectorFlow → `migrate 0004` → check Concentration
- **git bisect 친화**: 회귀 발생 시 파일명만으로 영역 즉시 식별
- **A1과 같은 명명 규약 동결**: `000X_<verb>_<object>.py`

#### 1.4.2 A3-B.Ⅰ 빈 테이블만 (PR-F/G/H가 시드)

A2의 패턴(스키마만, 데이터는 후속 PR)을 그대로 계승.

- PR-F: BreadthSnapshot.universe='SPY' 첫 row 생성
- PR-G: 일별 11 섹터 row 생성 (long-format)
- PR-H: ConcentrationSnapshot.universe='SPY' 첫 row 생성

PR-A3 시점에는 **`Model.objects.count() == 0`이 정상 상태**.

#### 1.4.3 동결 결정 인용

- **D2 long-format**: SectorFlowSnapshot은 (date × market_index) row. Phase 2에서 IG/Thematic 추가 시 row만 늘어남.
- **D6 universe SPY only**: BreadthSnapshot/ConcentrationSnapshot의 `universe` 필드는 choices에 SPY/QQQ/DIA 모두 정의하되, Phase 1 데이터는 SPY만 (PR-F/H 책임)
- **D8 PROTECT**: SectorFlowSnapshot.market_index FK가 MarketIndex 무결성 보호
- **is_finalized**: 3개 모델 모두 `is_finalized` BooleanField + `finalized_at` DateTimeField (KST 05:30 finalize task가 마킹)

---

## §2. 변경 파일

### 2.1 신규 파일 (8개)

```
backend/marketpulse/models/snapshot/__init__.py       # 또는 단일 snapshot.py — §3.1 참고
backend/marketpulse/models/snapshot/breadth.py
backend/marketpulse/models/snapshot/sector_flow.py
backend/marketpulse/models/snapshot/concentration.py

backend/marketpulse/migrations/0002_add_breadth.py
backend/marketpulse/migrations/0003_add_sector_flow.py
backend/marketpulse/migrations/0004_add_concentration.py

backend/tests/marketpulse/test_models_snapshot.py
```

### 2.2 수정 파일 (2개)

```
backend/marketpulse/models/__init__.py       # 3개 모델 re-export 추가
backend/marketpulse/admin/__init__.py        # 3개 admin 등록 추가 (PR-A2가 만든 admin 파일)
```

### 2.3 변경 금지 파일

- PR-A2가 만든 `models/news.py`, `models/anomaly.py`, `models/regime.py`, `models/briefing.py` (도메인 분리 원칙)
- PR-A1이 만든 `apps/market/` 하위
- 기존 migration 파일 (`0001_initial.py` 등)
- `settings.py`, `urls.py`
- Pydantic schemas (본 PR 모델 3개는 typed 비율 87%~100%로 JSONField 거의 없음 — `top_contributors`만 JSONField)

---

## §3. 수도코드

### 3.1 모델 파일 구조 결정

A2의 도메인별 분리 패턴을 계승하되, 카드 스냅샷 3개는 모두 `snapshot` 도메인에 속하므로:

```
models/
├── __init__.py              # 기존 + 3개 re-export 추가
├── news.py                  # PR-A2
├── anomaly.py               # PR-A2
├── regime.py                # PR-A2
├── briefing.py              # PR-A2
└── snapshot/                # ⭐ NEW (sub-package)
    ├── __init__.py
    ├── breadth.py           # BreadthSnapshot
    ├── sector_flow.py       # SectorFlowSnapshot
    └── concentration.py     # ConcentrationSnapshot
```

> **대안**: 단일 `models/snapshot.py`도 가능하지만 PR-A2의 도메인 분리 정신 일관 + PR-F/G/H가 각자의 도메인 파일만 수정하도록 sub-package로 분리 권장. 위임 프롬프트는 sub-package 형태로 작성.

### 3.2 `models/snapshot/breadth.py`

```python
"""Card B 참여도 스냅샷. PR-F(breadth calculator)가 사용."""
from django.db import models


class BreadthSnapshot(models.Model):
    """
    Card B 일별 참여도. universe별 long-format (D6).

    Phase 1: SPY only 활성 (데이터 row는 PR-F가 생성).
    Phase 2: QQQ, DIA universe 활성화 → row 추가만, 마이그레이션 불필요.

    is_finalized 정책 (동결 §2.5):
    - 장중 임시 row는 is_finalized=False
    - KST 05:30 finalize task가 finalized=True + finalized_at 마킹
    """

    UNIVERSE_CHOICES = [
        ("SPY", "S&P 500"),       # Phase 1 활성
        ("QQQ", "Nasdaq 100"),    # Phase 2
        ("DIA", "Dow 30"),        # Phase 2
    ]

    # 식별
    date = models.DateField(db_index=True)
    universe = models.CharField(max_length=8, choices=UNIVERSE_CHOICES, default="SPY")

    # % above MA (M06 — typed)
    above_ma_20 = models.FloatField()    # 0~100
    above_ma_50 = models.FloatField()
    above_ma_100 = models.FloatField()
    above_ma_200 = models.FloatField()

    # 52주 신고/신저 (M07 — typed)
    new_highs_52w = models.IntegerField()
    new_lows_52w = models.IntegerField()
    net_highs_lows = models.IntegerField()              # highs - lows
    net_highs_lows_ma10 = models.FloatField()           # 10일 이동평균

    # A-D Line (M08, M09 — typed)
    advances = models.IntegerField()
    declines = models.IntegerField()
    unchanged = models.IntegerField()
    ad_line_cumulative = models.BigIntegerField()       # 누적 A-D
    ad_line_slope_20d = models.FloatField()             # 20일 기울기
    mcclellan_oscillator = models.FloatField()

    # 데이터 품질
    coverage_ratio = models.FloatField(default=1.0)     # 종목 커버리지 (DQS)

    # is_finalized (동결 §2.5)
    is_finalized = models.BooleanField(default=False, db_index=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    calculated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["date", "universe"],
                name="uniq_breadth_date_universe",
            ),
        ]
        indexes = [
            models.Index(fields=["universe", "-date"]),
            models.Index(fields=["is_finalized", "-date"]),
        ]
        ordering = ["-date", "universe"]

    def __str__(self):
        finalized = "✓" if self.is_finalized else "△"
        return f"{self.date} [{self.universe}] AD={self.advances}/{self.declines} {finalized}"
```

### 3.3 `models/snapshot/sector_flow.py`

```python
"""Card C·D 섹터 자금 흐름 long-format. PR-G(sector flow calculator)가 사용."""
from django.db import models

from apps.market.models import MarketIndex


class SectorFlowSnapshot(models.Model):
    """
    Card C·D Long-format (D2). 일별 11 row(11 섹터, Phase 1).
    Phase 2: Industry Group 24개 또는 Thematic 추가 시 row만 늘어남.

    D8 PROTECT: MarketIndex 삭제 시 IntegrityError로 차단.

    Phase 1 활성 11 섹터:
    XLF, XLK, XLV, XLY, XLP, XLE, XLI, XLB, XLU, XLRE, XLC
    """

    # 식별
    date = models.DateField(db_index=True)
    market_index = models.ForeignKey(
        MarketIndex,
        on_delete=models.PROTECT,        # D8
        related_name="flow_snapshots",
        # Phase 2에서 IG/Thematic 추가 시 limit_choices_to 확장
    )

    # 가격·수익률 (S02)
    close_price = models.DecimalField(max_digits=12, decimal_places=4)
    return_1d = models.FloatField()
    return_1w = models.FloatField()
    return_1m = models.FloatField()
    return_3m = models.FloatField()
    return_ytd = models.FloatField()
    return_12m = models.FloatField()

    # 자금 흐름 (S05)
    volume = models.BigIntegerField()
    volume_ma_20 = models.BigIntegerField()
    flow_proxy = models.FloatField()                    # volume * return_1d (방향성 자금)

    # Capital Flow Ratio (S04)
    capital_flow_ratio_1w = models.FloatField()         # 섹터 자금 비중 1주 누적
    capital_flow_ratio_1m = models.FloatField()         # 1개월 누적

    # Z-Score (S03 — Dual Z-Score Matrix)
    z_score_temporal = models.FloatField()              # 자기 시계열 대비
    z_score_cross = models.FloatField()                 # 같은 날 섹터 간 cross-sectional

    # RS (S06)
    rs_vs_spy_4w = models.FloatField()                  # 4주 상대 강도
    rs_vs_spy_12w = models.FloatField()                 # 12주 상대 강도
    rs_trend_slope_4w = models.FloatField()             # RS 추세 기울기 (가속 판정)

    # RVOL (S11)
    rvol = models.FloatField()                          # 거래량 / 20일 평균

    # is_finalized (동결 §2.5)
    is_finalized = models.BooleanField(default=False, db_index=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    calculated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["date", "market_index"],
                name="uniq_sectorflow_date_index",
            ),
        ]
        indexes = [
            models.Index(fields=["market_index", "-date"]),
            models.Index(fields=["-date", "market_index"]),  # cross-sectional 쿼리용
            models.Index(fields=["is_finalized", "-date"]),
        ]
        ordering = ["-date", "market_index"]

    def __str__(self):
        finalized = "✓" if self.is_finalized else "△"
        return f"{self.date} {self.market_index.symbol} ret={self.return_1d:.2%} {finalized}"
```

### 3.4 `models/snapshot/concentration.py`

```python
"""Card B 펼침·이상 신호 R02 입력. PR-H(concentration calculator)가 사용."""
from django.db import models

from .breadth import BreadthSnapshot   # UNIVERSE_CHOICES 재사용


class ConcentrationSnapshot(models.Model):
    """
    지수 집중도. R02(concentration_extreme) 트리거 입력. universe × top_n 매트릭스.

    Phase 1: SPY only 활성 (PR-H가 row 생성).
    """

    UNIVERSE_CHOICES = BreadthSnapshot.UNIVERSE_CHOICES

    # 식별
    date = models.DateField(db_index=True)
    universe = models.CharField(max_length=8, choices=UNIVERSE_CHOICES, default="SPY")

    # 집중도 (typed)
    top5_contribution = models.FloatField()              # 0~1, 상위 5개 일일 기여도
    top10_contribution = models.FloatField()
    top20_contribution = models.FloatField()

    # 백분위 (1년 기준 — R02 트리거)
    top5_pct_1y = models.FloatField()                    # 0~1
    top10_pct_1y = models.FloatField()

    # 상위 종목 (가변 — JSON, list of dict)
    top_contributors = models.JSONField(default=list)
    # 예: [{"ticker": "AAPL", "contribution": 0.18, "weight": 0.07}, ...]

    # Herfindahl 지수 (시총 가중치 집중도)
    herfindahl_index = models.FloatField()               # 0~1

    # is_finalized (동결 §2.5)
    is_finalized = models.BooleanField(default=False, db_index=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    calculated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["date", "universe"],
                name="uniq_concentration_date_universe",
            ),
        ]
        indexes = [
            models.Index(fields=["universe", "-date"]),
            models.Index(fields=["is_finalized", "-date"]),
        ]
        ordering = ["-date", "universe"]

    def __str__(self):
        finalized = "✓" if self.is_finalized else "△"
        return f"{self.date} [{self.universe}] top5={self.top5_contribution:.1%} {finalized}"
```

### 3.5 `models/snapshot/__init__.py`

```python
"""Card snapshot models. Sub-package of marketpulse.models."""
from .breadth import BreadthSnapshot
from .sector_flow import SectorFlowSnapshot
from .concentration import ConcentrationSnapshot

__all__ = [
    "BreadthSnapshot",
    "SectorFlowSnapshot",
    "ConcentrationSnapshot",
]
```

### 3.6 `models/__init__.py` 수정

```python
"""All marketpulse models."""
# 기존 (PR-A2)
from .news import MarketPulseNews, NewsViewLog
from .anomaly import AnomalySignalLog
from .regime import RegimeSnapshot
from .briefing import BriefingLog

# ⭐ NEW (PR-A3)
from .snapshot import BreadthSnapshot, SectorFlowSnapshot, ConcentrationSnapshot

__all__ = [
    # PR-A2
    "MarketPulseNews",
    "NewsViewLog",
    "AnomalySignalLog",
    "RegimeSnapshot",
    "BriefingLog",
    # PR-A3
    "BreadthSnapshot",
    "SectorFlowSnapshot",
    "ConcentrationSnapshot",
]
```

### 3.7 `migrations/0002_add_breadth.py`

```python
"""
PR-A3 (1/3): BreadthSnapshot 추가.

A1과 동일 패턴 — schema only, 데이터 적재는 PR-F.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("marketpulse", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="BreadthSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("date", models.DateField(db_index=True)),
                ("universe", models.CharField(
                    max_length=8,
                    choices=[("SPY", "S&P 500"), ("QQQ", "Nasdaq 100"), ("DIA", "Dow 30")],
                    default="SPY",
                )),
                # ... §3.2 모든 필드 ...
                ("is_finalized", models.BooleanField(default=False, db_index=True)),
                ("finalized_at", models.DateTimeField(blank=True, null=True)),
                ("calculated_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-date", "universe"],
            },
        ),
        migrations.AddConstraint(
            model_name="breadthsnapshot",
            constraint=models.UniqueConstraint(
                fields=["date", "universe"],
                name="uniq_breadth_date_universe",
            ),
        ),
        migrations.AddIndex(
            model_name="breadthsnapshot",
            index=models.Index(fields=["universe", "-date"], name="breadth_universe_date_idx"),
        ),
        migrations.AddIndex(
            model_name="breadthsnapshot",
            index=models.Index(fields=["is_finalized", "-date"], name="breadth_finalized_idx"),
        ),
    ]
```

### 3.8 `migrations/0003_add_sector_flow.py`

```python
"""
PR-A3 (2/3): SectorFlowSnapshot 추가.

⚠️ Cross-app dependency: market.0004_seed_market_indices (PR-A1) + marketpulse.0002_add_breadth.
FK PROTECT to MarketIndex (D8).
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("marketpulse", "0002_add_breadth"),
        ("market", "0004_seed_market_indices"),  # ⚠️ PR-A1 마지막 마이그레이션 번호로 교체 필요
    ]

    operations = [
        migrations.CreateModel(
            name="SectorFlowSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("date", models.DateField(db_index=True)),
                ("market_index", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="flow_snapshots",
                    to="market.marketindex",
                )),
                # ... §3.3 모든 필드 ...
                ("is_finalized", models.BooleanField(default=False, db_index=True)),
                ("finalized_at", models.DateTimeField(blank=True, null=True)),
                ("calculated_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-date", "market_index"],
            },
        ),
        migrations.AddConstraint(
            model_name="sectorflowsnapshot",
            constraint=models.UniqueConstraint(
                fields=["date", "market_index"],
                name="uniq_sectorflow_date_index",
            ),
        ),
        migrations.AddIndex(
            model_name="sectorflowsnapshot",
            index=models.Index(fields=["market_index", "-date"], name="sf_index_date_idx"),
        ),
        migrations.AddIndex(
            model_name="sectorflowsnapshot",
            index=models.Index(fields=["-date", "market_index"], name="sf_date_index_idx"),
        ),
        migrations.AddIndex(
            model_name="sectorflowsnapshot",
            index=models.Index(fields=["is_finalized", "-date"], name="sf_finalized_idx"),
        ),
    ]
```

### 3.9 `migrations/0004_add_concentration.py`

```python
"""
PR-A3 (3/3): ConcentrationSnapshot 추가.

A1과 동일 패턴 — schema only, 데이터 적재는 PR-H.
top_contributors는 JSONField (Pydantic schema는 PR-H에서 추가 가능 — 본 PR은 type 없이 적재).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("marketpulse", "0003_add_sector_flow"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConcentrationSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("date", models.DateField(db_index=True)),
                ("universe", models.CharField(
                    max_length=8,
                    choices=[("SPY", "S&P 500"), ("QQQ", "Nasdaq 100"), ("DIA", "Dow 30")],
                    default="SPY",
                )),
                # ... §3.4 모든 필드 ...
                ("top_contributors", models.JSONField(default=list)),
                ("herfindahl_index", models.FloatField()),
                ("is_finalized", models.BooleanField(default=False, db_index=True)),
                ("finalized_at", models.DateTimeField(blank=True, null=True)),
                ("calculated_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-date", "universe"],
            },
        ),
        migrations.AddConstraint(
            model_name="concentrationsnapshot",
            constraint=models.UniqueConstraint(
                fields=["date", "universe"],
                name="uniq_concentration_date_universe",
            ),
        ),
        migrations.AddIndex(
            model_name="concentrationsnapshot",
            index=models.Index(fields=["universe", "-date"], name="conc_universe_date_idx"),
        ),
        migrations.AddIndex(
            model_name="concentrationsnapshot",
            index=models.Index(fields=["is_finalized", "-date"], name="conc_finalized_idx"),
        ),
    ]
```

> ⚠️ 위 마이그레이션 골격은 `python manage.py makemigrations marketpulse` 자동 생성 결과를 그대로 사용 권장. 수동 작성 시 인덱스명·필드 누락 위험.

### 3.10 `admin/__init__.py` 수정 (PR-A2가 만든 파일 확장)

```python
# 기존 (PR-A2) ...

from marketpulse.models.snapshot import (
    BreadthSnapshot,
    SectorFlowSnapshot,
    ConcentrationSnapshot,
)


@admin.register(BreadthSnapshot)
class BreadthSnapshotAdmin(admin.ModelAdmin):
    list_display = ("date", "universe", "advances", "declines", "is_finalized")
    list_filter = ("universe", "is_finalized")
    date_hierarchy = "date"


@admin.register(SectorFlowSnapshot)
class SectorFlowSnapshotAdmin(admin.ModelAdmin):
    list_display = ("date", "market_index", "return_1d", "z_score_temporal", "is_finalized")
    list_filter = ("is_finalized",)
    raw_id_fields = ("market_index",)
    date_hierarchy = "date"


@admin.register(ConcentrationSnapshot)
class ConcentrationSnapshotAdmin(admin.ModelAdmin):
    list_display = ("date", "universe", "top5_contribution", "herfindahl_index", "is_finalized")
    list_filter = ("universe", "is_finalized")
    date_hierarchy = "date"
```

---

## §4. 입출력 예시

### 4.1 단계별 migration forward

```bash
# 0002만 적용 (BreadthSnapshot만)
$ python manage.py migrate marketpulse 0002
Operations to perform:
  Target specific migration: 0002_add_breadth
Running migrations:
  Applying marketpulse.0002_add_breadth... OK

# 0003 추가 (SectorFlowSnapshot, cross-app FK)
$ python manage.py migrate marketpulse 0003
  Applying marketpulse.0003_add_sector_flow... OK

# 0004 추가 (ConcentrationSnapshot)
$ python manage.py migrate marketpulse 0004
  Applying marketpulse.0004_add_concentration... OK

# 또는 한 번에:
$ python manage.py migrate marketpulse
  Applying marketpulse.0002_add_breadth... OK
  Applying marketpulse.0003_add_sector_flow... OK
  Applying marketpulse.0004_add_concentration... OK

# 검증 — 모두 빈 테이블이어야 함 (A3-B.Ⅰ)
$ python manage.py shell -c "
from marketpulse.models import BreadthSnapshot, SectorFlowSnapshot, ConcentrationSnapshot
for M in [BreadthSnapshot, SectorFlowSnapshot, ConcentrationSnapshot]:
    print(f'{M._meta.label:50} count: {M.objects.count()}')
"
# 기대 출력 (PR-A3 정상 상태):
# marketpulse.BreadthSnapshot                        count: 0
# marketpulse.SectorFlowSnapshot                     count: 0
# marketpulse.ConcentrationSnapshot                  count: 0
```

### 4.2 단계별 migration reverse (3분리의 핵심 이점)

```bash
# Concentration만 되돌리기 (Breadth, SectorFlow 유지)
$ python manage.py migrate marketpulse 0003
  Unapplying marketpulse.0004_add_concentration... OK

# SectorFlow까지 되돌리기 (Breadth만 유지)
$ python manage.py migrate marketpulse 0002
  Unapplying marketpulse.0003_add_sector_flow... OK

# Breadth까지 되돌리기 (PR-A3 전체 reverse)
$ python manage.py migrate marketpulse 0001
  Unapplying marketpulse.0002_add_breadth... OK

# PR-A3 전체 재적용
$ python manage.py migrate marketpulse
  Applying marketpulse.0002_add_breadth... OK
  Applying marketpulse.0003_add_sector_flow... OK
  Applying marketpulse.0004_add_concentration... OK
```

### 4.3 FK PROTECT 동작 검증 (D8)

```python
>>> from apps.market.models import MarketIndex
>>> from marketpulse.models import SectorFlowSnapshot
>>> import datetime
>>> xlf = MarketIndex.objects.get(symbol="XLF")
>>> SectorFlowSnapshot.objects.create(
...     date=datetime.date.today(),
...     market_index=xlf,
...     # ... 모든 필수 필드 ...
... )
>>> xlf.delete()
django.db.models.deletion.ProtectedError: Cannot delete some instances of model 'MarketIndex' because they are referenced through protected foreign keys: 'SectorFlowSnapshot.market_index'.
# ✓ PROTECT 정상 동작
```

### 4.4 후속 PR과의 인터페이스 (참고)

```python
# PR-F (BreadthCalculator)에서 본 PR이 정의한 모델 사용
from marketpulse.models import BreadthSnapshot

obj, created = BreadthSnapshot.objects.get_or_create(
    date=today, universe="SPY",
    defaults={
        "advances": ..., "declines": ...,
        "is_finalized": False,  # 장중
        # ...
    },
)

# PR-O finalize task가 KST 05:30에:
BreadthSnapshot.objects.filter(date=yesterday, is_finalized=False).update(
    is_finalized=True,
    finalized_at=timezone.now(),
)
```

---

## §5. 테스트 시나리오

### 5.1 모델 생성·제약 (`test_models_snapshot.py`)

| ID  | 대상          | 시나리오                    | 검증                                               |
| --- | ------------- | --------------------------- | -------------------------------------------------- |
| T1  | Breadth       | universe choices            | SPY/QQQ/DIA 정확히 3개, default="SPY"              |
| T2  | Breadth       | (date, universe) unique     | 동일 키 두 번째 INSERT 시 IntegrityError           |
| T3  | Breadth       | is_finalized 기본값         | False, finalized_at NULL                           |
| T4  | SectorFlow    | (date, market_index) unique | 동일 키 두 번째 INSERT 시 IntegrityError           |
| T5  | SectorFlow    | FK PROTECT                  | MarketIndex 삭제 시 ProtectedError                 |
| T6  | SectorFlow    | long-format INSERT          | 11 섹터 ETF에 대해 11 row 가능 (같은 date)         |
| T7  | Concentration | (date, universe) unique     | 동일 키 두 번째 INSERT 시 IntegrityError           |
| T8  | Concentration | top_contributors JSON       | list of dict 저장·조회                             |
| T9  | 3개 모델      | is_finalized 일관성         | 3개 모두 BooleanField + finalized_at DateTimeField |
| T10 | 3개 모델      | **str** 정의                | 모든 모델 instance.**str**() 정상 호출             |
| T11 | 3개 모델      | Meta.ordering 정의          | 3개 모두 ordering 명시                             |

### 5.2 마이그레이션 단계별 (`test_migrations_a3.py`)

| ID  | 시나리오             | 검증                                                  |
| --- | -------------------- | ----------------------------------------------------- |
| T12 | 0002 forward         | BreadthSnapshot 테이블 생성, count=0                  |
| T13 | 0003 forward         | SectorFlowSnapshot 테이블 생성, FK to MarketIndex     |
| T14 | 0004 forward         | ConcentrationSnapshot 테이블 생성, count=0            |
| T15 | 부분 reverse         | `migrate 0003` → ConcentrationSnapshot 테이블만 DROP  |
| T16 | 멱등성               | forward → reverse → forward → 동일 schema             |
| T17 | cross-app dependency | 0003이 market.0004 의존성 명시 (Django introspection) |

### 5.3 통합 (선택, `test_integration_a3.py`)

| ID  | 시나리오             | 검증                                                                          |
| --- | -------------------- | ----------------------------------------------------------------------------- |
| T18 | 11 섹터 ETF flow row | 11 MarketIndex(sector_group != BENCHMARK)에 대해 SectorFlowSnapshot 생성 가능 |
| T19 | A2 모델과 공존       | RegimeSnapshot + BreadthSnapshot 동일 date row 동시 존재 가능                 |

### 5.4 실행

```bash
pytest backend/tests/marketpulse/test_models_snapshot.py -v
pytest backend/tests/marketpulse/test_migrations_a3.py -v   # (옵션)
```

---

## §6. DoD (Definition of Done)

### 6.1 머지 전 (CI 자동 검증 + 본인 확인)

- [ ] `python manage.py migrate marketpulse` 성공 (0002 → 0003 → 0004 순)
- [ ] 단계별 reverse 성공:
  - [ ] `python manage.py migrate marketpulse 0003` (0004만 reverse)
  - [ ] `python manage.py migrate marketpulse 0002` (0003까지 reverse)
  - [ ] `python manage.py migrate marketpulse 0001` (PR-A3 전체 reverse, A2 유지)
  - [ ] `python manage.py migrate marketpulse` (재적용)
- [ ] `python manage.py makemigrations marketpulse --check --dry-run` → "No changes detected"
- [ ] `python manage.py check` 무경고
- [ ] `pytest backend/tests/marketpulse/test_models_snapshot.py -v` PASS (T1~T11)
- [ ] `pytest backend/tests/marketpulse/test_migrations_a3.py -v` PASS (T12~T17, 옵션)
- [ ] 모든 모델 `is_finalized` + `finalized_at` 컬럼 존재 (3개 모델 모두)
- [ ] `models/__init__.py`에서 8개 모델 모두 import 가능 (PR-A2의 5개 + PR-A3의 3개)
- [ ] Django Admin에서 3개 신규 모델 페이지 접근·검색 동작
- [ ] PR 설명에 §6.2 Post-merge 체크리스트 명시

### 6.2 머지 후 (운영자=본인) — PR 템플릿 고정 섹션

**A1과 결정적 차이**: 백필 command 없음. 본 PR은 **빈 테이블만**.

- [ ] DEV 환경 migration 적용
- [ ] 3개 테이블 모두 비어 있음 확인:
  ```python
  BreadthSnapshot.objects.count() == 0
  SectorFlowSnapshot.objects.count() == 0
  ConcentrationSnapshot.objects.count() == 0
  ```
- [ ] FK PROTECT 동작 검증 (수동, 옵션):
  ```python
  # 임시 SectorFlowSnapshot row 1개 생성 후 MarketIndex 삭제 시도
  # → ProtectedError 확인 후 임시 row 삭제
  ```
- [ ] 후속 PR-F/G/H 위임 프롬프트 작성 시:
  - PR-F: BreadthSnapshot.universe='SPY' 첫 row `get_or_create`
  - PR-G: 11 섹터 ETF 각각에 대해 일별 SectorFlowSnapshot row
  - PR-H: ConcentrationSnapshot.universe='SPY' 첫 row
- [ ] is_finalized 일관성 4개 모델 확인 (RegimeSnapshot 포함):
  ```python
  for M in [RegimeSnapshot, BreadthSnapshot, SectorFlowSnapshot, ConcentrationSnapshot]:
      assert hasattr(M, "is_finalized") and hasattr(M, "finalized_at")
  ```

### 6.3 PR 설명 필수 포함

- 본 PR의 3개 모델 명단 + 각 모델이 의존하는 후속 PR (F/G/H)
- 동결 결정 인용: D2 long-format · D6 SPY only · D8 PROTECT · is_finalized
- "데이터 적재는 후속 PR(F/G/H)" 명시
- A1과 결정적 차이 명시: backfill command 없음

---

## §7. 금지 사항

| #   | 금지 행위                                                                 | 사유                                                                                                                      |
| --- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| F1  | migration 안에서 외부 API 호출                                            | A1과 동일 — 머지 후 새벽 장애 위험                                                                                        |
| F2  | `RunPython.noop` 사용                                                     | reverse_code 정확 작성 강제 (CreateModel은 자동 reverse라 본 PR엔 RunPython 자체 거의 없음)                               |
| F3  | 한 migration 파일에 3개 모델 통합                                         | A3-A.Ⅱ 결정 위반. 0002/0003/0004 엄격 분리                                                                                |
| F4  | 본 PR에서 데이터 row INSERT (RunPython 또는 fixture)                      | A3-B.Ⅰ 결정 위반. 빈 테이블만, 데이터는 PR-F/G/H 책임                                                                     |
| F5  | `SectorFlowSnapshot.market_index` FK on_delete를 PROTECT 외로 변경        | D8 동결 위반                                                                                                              |
| F6  | `BreadthSnapshot.universe` choices에서 QQQ/DIA 제거                       | D6 위반 — Phase 1엔 비활성이지만 schema는 미리 준비                                                                       |
| F7  | `is_finalized` 또는 `finalized_at` 컬럼 누락 (3개 모델 중 어느 하나라도)  | 동결 §2.5 위반                                                                                                            |
| F8  | `from marketpulse.models import X` (migration 안)                         | historical model 미사용. `apps.get_model("marketpulse", "X")` 강제 (본 PR엔 RunPython 거의 없으나 향후 안전망)            |
| F9  | `MarketPulseNews`, `RegimeSnapshot` 등 PR-A2 모델 수정                    | PR-A2 영역                                                                                                                |
| F10 | 카드 계산 로직 (Breadth/SectorFlow/Concentration calculator) 작성         | PR-F/G/H 영역                                                                                                             |
| F11 | Celery task 등록 (mp_calc_breadth_5min 등)                                | PR-F/G/H 영역                                                                                                             |
| F12 | `0001_initial.py` 수정                                                    | PR-A2가 동결한 마이그레이션                                                                                               |
| F13 | Pydantic schema 작성 (`schemas/snapshot/`)                                | 본 PR 모델 3개는 typed 비율 87~100%로 schema 거의 불필요. ConcentrationSnapshot.top_contributors의 schema는 PR-H에서 추가 |
| F14 | 명명 규약 위반 (`0002_card_snapshots.py` 등 통합 명)                      | A3-A.Ⅱ + A1 명명 규약 동결 위반                                                                                           |
| F15 | `dependencies` 체인 끊기 (예: 0003이 0002 건너뛰고 0001 의존)             | 일렬 의존 체인 동결                                                                                                       |
| F16 | `SectorFlowSnapshot.market_index`의 cross-app dependency 누락             | 0003은 `market.000X_seed_market_indices`도 의존성에 명시해야 함                                                           |
| F17 | universe 컬럼을 `BreadthSnapshot`만 두고 `ConcentrationSnapshot`에서 제거 | 두 모델 모두 universe 필드 보유 (D6 일관)                                                                                 |

---

## 참고: 본 위임 프롬프트의 결정 근거

| 결정                                | 선택                                                                | 위임 프롬프트 반영 위치 |
| ----------------------------------- | ------------------------------------------------------------------- | ----------------------- |
| **A3-A.Ⅱ** Migration 3분리          | §1.4.1, §3.7~3.9 (3개 파일), §4.1 단계별 forward, §4.2 부분 reverse | §7 F3·F14·F15           |
| **A3-B.Ⅰ** 빈 테이블만              | §1.4.2, §6.1 count=0 검증, §6.2 백필 command 없음 명시              | §7 F4                   |
| 동결 D2 long-format                 | §3.3 SectorFlowSnapshot (date × market_index)                       | —                       |
| 동결 D6 universe SPY only           | §3.2·3.4 UNIVERSE_CHOICES 3개 정의, default="SPY"                   | §7 F6                   |
| 동결 D8 PROTECT                     | §3.3 `on_delete=models.PROTECT` 명시                                | §7 F5, §5.1 T5          |
| 동결 §2.5 is_finalized              | §3.2~3.4 3개 모델 모두 BooleanField + DateTimeField                 | §7 F7, §5.1 T9          |
| A1과 명명 규약 일관                 | `000X_<verb>_<object>.py`                                           | §7 F14                  |
| **백필 command 불필요** (A1과 차이) | §1.2 명시, §6.2 명시                                                | §7 F4                   |
