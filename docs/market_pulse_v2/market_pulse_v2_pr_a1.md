# PR-A1 위임 프롬프트 — v1 확장 마이그레이션

> **메타 정보**
>
> - PR ID: PR-A1
> - 영역: Migration (v1 → v2 확장)
> - 의존 PR: 없음 (선두)
> - 후속 의존: PR-A2, PR-A3, PR-C, PR-G
> - 견적: 3.5h ± 0.5h (PERT P50, A-Ⅲ 3분리 반영)
> - 결정 패키지: **A-Ⅲ(3분리)** + B-Ⅰ(dict 하드코딩) + C-Ⅱ(수동 command)

---

## §1. 컨텍스트

### 1.1 프로젝트 배경

- 프로젝트: **Market Pulse v2 Phase 1**
- 위치: `backend/apps/market/`
- 스택: Django 4.x + PostgreSQL + Celery
- 본 PR-A1은 Phase 1의 16 PR 중 **선두**(의존 없음). PR-A2, A3, C, G가 본 PR에 의존.

### 1.2 본 PR의 목표

v1 → v2 마이그레이션의 첫 단계로 다음 3가지를 **3개의 독립 migration 파일**로 분리 처리:

| Migration | 책임                                            | 파일                               |
| --------- | ----------------------------------------------- | ---------------------------------- |
| **0002**  | SCHEMA — `MarketIndex.sector_group` 컬럼 추가   | `0002_add_sector_group.py`         |
| **0003**  | DATA A — `EconomicIndicator` 11 row 추가        | `0003_seed_economic_indicators.py` |
| **0004**  | DATA B — `MarketIndex` 20 row sector_group 백필 | `0004_seed_market_indices.py`      |

별도로 1년치 시계열 백필을 위한 **management command `backfill_v2_a1`** 작성. **migration 안에서 외부 API 호출 절대 금지** — 백필은 머지 후 운영자가 수동 실행.

### 1.3 의존성

- **상위 PR**: 없음 (선두)
- **하위 PR**: PR-A2 (FK 의존), PR-A3 (FK 의존), PR-C (sector_group 사용), PR-G (sector_group 사용)
- **전제 모델**: `EconomicIndicator`, `MarketIndex`는 v1에 이미 존재 (v1 base 코드 기반)

### 1.4 3분리 선택의 의미와 명명 규약 (Decision A-Ⅲ)

3분리 선택으로 다음과 같은 운영상 이점을 확보:

- **부분 롤백 가능**: `migrate market 0003`으로 DATA B만 되돌리고 schema·DATA A는 유지하는 식의 세밀한 제어
- **git bisect 친화**: 회귀 발생 시 파일명만으로 영역 즉시 식별
- **단계별 헬스체크 삽입 가능**: `migrate 0002` → check → `migrate 0003` → check → `migrate 0004`
- **A2/A3 패턴 재사용**: 동일 명명·구조를 후속 PR에 그대로 적용

**명명 규약 (동결)**:

```
000X_<verb>_<object>.py
   verb:   add | seed | update | drop | rename | backfill
   object: 모델·필드·도메인 명사
```

**의존성 체인 (동결)**:

```
0001_initial → 0002_add_sector_group → 0003_seed_economic_indicators → 0004_seed_market_indices
```

각 migration의 `dependencies`는 **직전 migration만** 명시 (한 줄 의존 체인).

---

## §2. 변경 파일

### 2.1 신규 파일 (8개)

```
backend/apps/market/migrations/0002_add_sector_group.py
backend/apps/market/migrations/0003_seed_economic_indicators.py
backend/apps/market/migrations/0004_seed_market_indices.py
backend/apps/market/management/__init__.py                       # 없으면
backend/apps/market/management/commands/__init__.py              # 없으면
backend/apps/market/management/commands/backfill_v2_a1.py
backend/apps/market/tests/test_migration_a1.py
backend/apps/market/tests/test_backfill_v2_a1.py
```

### 2.2 수정 파일 (1~2개)

```
backend/apps/market/models.py        # MarketIndex.sector_group 필드 추가
backend/apps/market/admin.py         # (선택) MarketIndexAdmin.list_display에 추가
```

### 2.3 변경 금지 파일

- 다른 앱의 `models.py`
- 기존 migration 파일 (`0001_*.py` 등)
- `settings.py`, `urls.py`, `wsgi.py`, `asgi.py`
- 다른 PR이 다룰 모델 (`MarketPulseNews`, `RegimeSnapshot` 등 — PR-A2 영역)

---

## §3. 수도코드 (실 코드 + 의사코드 혼합)

### 3.1 `models.py` 변경

```python
# backend/apps/market/models.py

class MarketIndex(models.Model):
    # ... 기존 필드 (symbol, name, ...) 보존 ...

    SECTOR_GROUP_CHOICES = [
        ("BENCHMARK", "Benchmark"),
        ("FINANCIALS", "Financials"),
        ("TECH", "Technology"),
        ("HEALTHCARE", "Healthcare"),
        ("CONSUMER_DISC", "Consumer Discretionary"),
        ("CONSUMER_STAPLES", "Consumer Staples"),
        ("ENERGY", "Energy"),
        ("INDUSTRIALS", "Industrials"),
        ("MATERIALS", "Materials"),
        ("UTILITIES", "Utilities"),
        ("REAL_ESTATE", "Real Estate"),
        ("COMMUNICATION", "Communication Services"),
    ]

    sector_group = models.CharField(
        max_length=32,
        choices=SECTOR_GROUP_CHOICES,
        default="BENCHMARK",
        db_index=True,
        help_text="GICS 11-sector classification + BENCHMARK",
    )

    class Meta:
        # ... 기존 Meta 보존 ...
        indexes = [
            # 기존 인덱스 보존
            models.Index(fields=["sector_group"], name="midx_sector_group_idx"),
        ]
```

### 3.2 Migration 0002 — SCHEMA만 (`0002_add_sector_group.py`)

```python
"""
PR-A1 (1/3): MarketIndex.sector_group 컬럼 추가.

본 migration은 schema 변경만 수행. 데이터 적재는 0003·0004에서.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("market", "0001_initial"),  # ⚠️ 실제 v1 마지막 migration 번호로 교체
    ]

    operations = [
        migrations.AddField(
            model_name="marketindex",
            name="sector_group",
            field=models.CharField(
                max_length=32,
                choices=[
                    ("BENCHMARK", "Benchmark"),
                    ("FINANCIALS", "Financials"),
                    ("TECH", "Technology"),
                    ("HEALTHCARE", "Healthcare"),
                    ("CONSUMER_DISC", "Consumer Discretionary"),
                    ("CONSUMER_STAPLES", "Consumer Staples"),
                    ("ENERGY", "Energy"),
                    ("INDUSTRIALS", "Industrials"),
                    ("MATERIALS", "Materials"),
                    ("UTILITIES", "Utilities"),
                    ("REAL_ESTATE", "Real Estate"),
                    ("COMMUNICATION", "Communication Services"),
                ],
                default="BENCHMARK",
                db_index=True,
                help_text="GICS 11-sector classification + BENCHMARK",
            ),
        ),
    ]
```

### 3.3 Migration 0003 — DATA A: EconomicIndicator (`0003_seed_economic_indicators.py`)

```python
"""
PR-A1 (2/3): 신규 EconomicIndicator 11 row 추가.

⚠️ 외부 API 호출 금지. 시계열 백필은 backfill_v2_a1 command 사용.
⚠️ 변경은 새 migration 작성 — 본 파일 직접 수정 금지.
"""
from django.db import migrations


# ============================================================
# HARDCODED MAPPING (Decision B-Ⅰ)
# DO NOT EDIT — 변경은 새 migration 작성으로
# ============================================================

ECONOMIC_INDICATORS_NEW = [
    {"series_id": "NFCI", "name": "Chicago Fed NFCI", "source": "FRED", "frequency": "weekly", "unit": "index"},
    {"series_id": "ANFCI", "name": "Adjusted NFCI", "source": "FRED", "frequency": "weekly", "unit": "index"},
    {"series_id": "T10Y2Y", "name": "10Y-2Y Treasury Spread", "source": "FRED", "frequency": "daily", "unit": "percent"},
    {"series_id": "T10Y3M", "name": "10Y-3M Treasury Spread", "source": "FRED", "frequency": "daily", "unit": "percent"},
    {"series_id": "BAMLH0A0HYM2", "name": "ICE BofA US HY Index OAS", "source": "FRED", "frequency": "daily", "unit": "percent"},
    {"series_id": "VIXCLS", "name": "CBOE VIX", "source": "FRED", "frequency": "daily", "unit": "index"},
    {"series_id": "DGS10", "name": "10Y Treasury Yield", "source": "FRED", "frequency": "daily", "unit": "percent"},
    {"series_id": "DGS2", "name": "2Y Treasury Yield", "source": "FRED", "frequency": "daily", "unit": "percent"},
    {"series_id": "DFF", "name": "Federal Funds Effective Rate", "source": "FRED", "frequency": "daily", "unit": "percent"},
    {"series_id": "UNRATE", "name": "Unemployment Rate", "source": "FRED", "frequency": "monthly", "unit": "percent"},
    {"series_id": "CPIAUCSL", "name": "Consumer Price Index", "source": "FRED", "frequency": "monthly", "unit": "index"},
]
# 정확히 11개. ↑ 실제 series 목록은 phase1-frozen-decisions.md §2와 정합 확인 필요.

assert len(ECONOMIC_INDICATORS_NEW) == 11, "PR-A1 사양: EconomicIndicator 11개"


def forward(apps, schema_editor):
    """11 row 추가. 이미 있는 series_id는 SKIP (idempotent)."""
    EconomicIndicator = apps.get_model("market", "EconomicIndicator")
    for entry in ECONOMIC_INDICATORS_NEW:
        EconomicIndicator.objects.get_or_create(
            series_id=entry["series_id"],
            defaults={
                "name": entry["name"],
                "source": entry["source"],
                "frequency": entry["frequency"],
                "unit": entry["unit"],
            },
        )


def reverse(apps, schema_editor):
    """series_id로 정확히 11 row만 삭제. 다른 series 보존."""
    EconomicIndicator = apps.get_model("market", "EconomicIndicator")
    series_ids = [e["series_id"] for e in ECONOMIC_INDICATORS_NEW]
    EconomicIndicator.objects.filter(series_id__in=series_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("market", "0002_add_sector_group"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
```

### 3.4 Migration 0004 — DATA B: MarketIndex (`0004_seed_market_indices.py`)

```python
"""
PR-A1 (3/3): MarketIndex 20 row의 sector_group 백필.

- 없는 symbol: get_or_create로 신규 생성
- 있는 symbol: sector_group 필드만 update (다른 필드 보존)

⚠️ 변경은 새 migration 작성 — 본 파일 직접 수정 금지.
"""
from django.db import migrations


# ============================================================
# HARDCODED MAPPING (Decision B-Ⅰ)
# DO NOT EDIT — 변경은 새 migration 작성으로
# ============================================================

MARKET_INDEX_SECTOR_MAPPING = {
    # Benchmarks (3)
    "SPY": "BENCHMARK",
    "QQQ": "BENCHMARK",
    "IWM": "BENCHMARK",
    # GICS 11 sector ETFs
    "XLF": "FINANCIALS",
    "XLK": "TECH",
    "XLV": "HEALTHCARE",
    "XLY": "CONSUMER_DISC",
    "XLP": "CONSUMER_STAPLES",
    "XLE": "ENERGY",
    "XLI": "INDUSTRIALS",
    "XLB": "MATERIALS",
    "XLU": "UTILITIES",
    "XLRE": "REAL_ESTATE",
    "XLC": "COMMUNICATION",
    # Sub-benchmarks / additional (6)
    "DIA": "BENCHMARK",
    "VTI": "BENCHMARK",
    "EFA": "BENCHMARK",
    "EEM": "BENCHMARK",
    "TLT": "BENCHMARK",
    "GLD": "BENCHMARK",
}
# 정확히 20개. ↑ phase1-frozen-decisions.md의 MarketIndex universe와 정합 확인.

assert len(MARKET_INDEX_SECTOR_MAPPING) == 20, "PR-A1 사양: MarketIndex 20개"


def forward(apps, schema_editor):
    """
    20 row의 sector_group 백필.
    - 없는 symbol: get_or_create로 신규 생성 (sector_group + 기본 name)
    - 있는 symbol: sector_group 필드만 update (다른 필드 보존)
    """
    MarketIndex = apps.get_model("market", "MarketIndex")
    for symbol, sector in MARKET_INDEX_SECTOR_MAPPING.items():
        obj, created = MarketIndex.objects.get_or_create(
            symbol=symbol,
            defaults={
                "name": symbol,
                "sector_group": sector,
            },
        )
        if not created and obj.sector_group != sector:
            obj.sector_group = sector
            obj.save(update_fields=["sector_group"])


def reverse(apps, schema_editor):
    """
    역연산: 20 symbol의 sector_group을 default("BENCHMARK")로 복귀.
    row 자체는 보존 (다른 PR/외부에서 참조 가능성).
    """
    MarketIndex = apps.get_model("market", "MarketIndex")
    MarketIndex.objects.filter(
        symbol__in=list(MARKET_INDEX_SECTOR_MAPPING.keys())
    ).update(sector_group="BENCHMARK")


class Migration(migrations.Migration):

    dependencies = [
        ("market", "0003_seed_economic_indicators"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
```

### 3.5 management command 골격 (`backfill_v2_a1.py`)

```python
"""
PR-A1 후속: 신규 EconomicIndicator 11종 + MarketIndex 11종에 대한 1년치 시계열 백필.
Idempotent — 동일 명령 재실행 시 중복 행 발생 0.
"""
import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from apps.market.models import EconomicIndicator, MarketIndex, EconomicObservation, OHLC
# ↑ 실제 v1 모델명에 맞게 import (EconomicObservation/OHLC는 placeholder)

# 본 PR이 추가한 신규 백필 대상 (migration 0003·0004의 상수와 정합)
NEW_ECONOMIC_SERIES = [
    "NFCI", "ANFCI", "T10Y2Y", "T10Y3M", "BAMLH0A0HYM2",
    "VIXCLS", "DGS10", "DGS2", "DFF", "UNRATE", "CPIAUCSL",
]
NEW_MARKET_SYMBOLS = [
    "XLF", "XLK", "XLV", "XLY", "XLP", "XLE", "XLI", "XLB",
    "XLU", "XLRE", "XLC",  # 11 sector ETFs (기존 SPY/QQQ 등은 백필 외)
]

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Backfill 1-year history for v2 PR-A1 신규 indicators and indices"

    def add_arguments(self, parser):
        parser.add_argument("--series-id", type=str, default=None,
                            help="특정 series_id만 백필 (생략 시 11개 전체)")
        parser.add_argument("--symbol", type=str, default=None,
                            help="특정 symbol만 백필 (생략 시 신규 11개 전체)")
        parser.add_argument("--from", dest="from_date", type=str, default=None,
                            help="YYYY-MM-DD (기본: 365일 전)")
        parser.add_argument("--to", dest="to_date", type=str, default=None,
                            help="YYYY-MM-DD (기본: 오늘)")
        parser.add_argument("--dry-run", action="store_true",
                            help="실행 없이 대상 목록만 출력")
        parser.add_argument("--check-pending", action="store_true",
                            help="데이터 0인 신규 series/symbol 탐지 후 종료")
        parser.add_argument("--limit", type=int, default=None,
                            help="대상 수 제한 (테스트용)")

    def handle(self, *args, **options):
        # --check-pending 모드
        if options["check_pending"]:
            self._check_pending()
            return

        # 기간 결정
        to_date = self._parse_date(options["to_date"]) or timezone.now().date()
        from_date = self._parse_date(options["from_date"]) or (to_date - timedelta(days=365))

        # 대상 필터
        series_targets = self._resolve_economic_targets(options)
        symbol_targets = self._resolve_market_targets(options)

        if options["dry_run"]:
            self.stdout.write(f"[DRY-RUN] {from_date} ~ {to_date}")
            self.stdout.write(f"[DRY-RUN] Economic ({len(series_targets)}): {series_targets}")
            self.stdout.write(f"[DRY-RUN] Market ({len(symbol_targets)}): {symbol_targets}")
            return

        # 백필 실행 (idempotent)
        n_econ_inserted = 0
        for series_id in series_targets:
            try:
                inserted = self._backfill_economic(series_id, from_date, to_date)
                n_econ_inserted += inserted
                self.stdout.write(f"  {series_id}: {inserted} obs inserted")
            except Exception as e:
                logger.error(f"Failed to backfill {series_id}: {e}", exc_info=True)
                self.stderr.write(self.style.WARNING(f"  {series_id}: SKIPPED ({e})"))

        n_market_inserted = 0
        for symbol in symbol_targets:
            try:
                inserted = self._backfill_market(symbol, from_date, to_date)
                n_market_inserted += inserted
                self.stdout.write(f"  {symbol}: {inserted} bars inserted")
            except Exception as e:
                logger.error(f"Failed to backfill {symbol}: {e}", exc_info=True)
                self.stderr.write(self.style.WARNING(f"  {symbol}: SKIPPED ({e})"))

        self.stdout.write(self.style.SUCCESS(
            f"Backfill complete: "
            f"{n_econ_inserted} econ obs ({len(series_targets)} series), "
            f"{n_market_inserted} bars ({len(symbol_targets)} symbols)"
        ))

    # --- helpers (요지) ---

    def _parse_date(self, s):
        from datetime import datetime
        return datetime.strptime(s, "%Y-%m-%d").date() if s else None

    def _resolve_economic_targets(self, options):
        if options["series_id"]:
            return [options["series_id"]]
        targets = NEW_ECONOMIC_SERIES
        if options["limit"]:
            targets = targets[:options["limit"]]
        return targets

    def _resolve_market_targets(self, options):
        if options["symbol"]:
            return [options["symbol"]]
        targets = NEW_MARKET_SYMBOLS
        if options["limit"]:
            targets = targets[:options["limit"]]
        return targets

    def _check_pending(self):
        """데이터 0인 신규 series_id / symbol 출력"""
        pending_series = []
        for sid in NEW_ECONOMIC_SERIES:
            if not EconomicObservation.objects.filter(indicator__series_id=sid).exists():
                pending_series.append(sid)
        pending_symbols = []
        for sym in NEW_MARKET_SYMBOLS:
            if not OHLC.objects.filter(index__symbol=sym).exists():
                pending_symbols.append(sym)
        self.stdout.write(f"[CHECK] Pending economic ({len(pending_series)}): {pending_series}")
        self.stdout.write(f"[CHECK] Pending market ({len(pending_symbols)}): {pending_symbols}")

    @transaction.atomic
    def _backfill_economic(self, series_id, from_date, to_date):
        """FRED API 호출 → EconomicObservation에 idempotent 적재."""
        from apps.market.services.fred_client import fetch_series  # placeholder
        indicator = EconomicIndicator.objects.get(series_id=series_id)
        observations = fetch_series(series_id, from_date, to_date)
        inserted = 0
        for obs in observations:
            _, created = EconomicObservation.objects.get_or_create(
                indicator=indicator,
                date=obs["date"],
                defaults={"value": obs["value"]},
            )
            if created:
                inserted += 1
        return inserted

    @transaction.atomic
    def _backfill_market(self, symbol, from_date, to_date):
        """Yahoo/Polygon API 호출 → OHLC에 idempotent 적재."""
        from apps.market.services.market_client import fetch_ohlc  # placeholder
        index = MarketIndex.objects.get(symbol=symbol)
        bars = fetch_ohlc(symbol, from_date, to_date)
        inserted = 0
        for bar in bars:
            _, created = OHLC.objects.get_or_create(
                index=index,
                date=bar["date"],
                defaults={
                    "open": bar["open"],
                    "high": bar["high"],
                    "low": bar["low"],
                    "close": bar["close"],
                    "volume": bar["volume"],
                },
            )
            if created:
                inserted += 1
        return inserted
```

> ⚠️ `fred_client.fetch_series`, `market_client.fetch_ohlc`는 v1에 이미 존재하는 service 모듈 이름으로 교체. 없으면 본 PR 범위 외 — Claude Code 위임 시 기존 모듈명 확인 후 import 경로 수정.

---

## §4. 입출력 예시

### 4.1 단계별 migration forward

```bash
# 0002만 적용 (schema 추가만)
$ python manage.py migrate market 0002
Operations to perform:
  Target specific migration: 0002_add_sector_group
Running migrations:
  Applying market.0002_add_sector_group... OK

# 검증: 컬럼 존재 + 모든 기존 row sector_group=BENCHMARK
$ python manage.py shell -c "
from apps.market.models import MarketIndex
print('field exists:', 'sector_group' in [f.name for f in MarketIndex._meta.get_fields()])
print('all default:', MarketIndex.objects.exclude(sector_group='BENCHMARK').count() == 0)
"

# 0003 추가 적용 (DATA A)
$ python manage.py migrate market 0003
  Applying market.0003_seed_economic_indicators... OK

# 0004 추가 적용 (DATA B)
$ python manage.py migrate market 0004
  Applying market.0004_seed_market_indices... OK

# 또는 한 번에:
$ python manage.py migrate market
  Applying market.0002_add_sector_group... OK
  Applying market.0003_seed_economic_indicators... OK
  Applying market.0004_seed_market_indices... OK
```

### 4.2 단계별 migration reverse (3분리의 핵심 이점)

```bash
# DATA B만 되돌리기 (sector_group 값 → BENCHMARK 복귀, schema·DATA A 유지)
$ python manage.py migrate market 0003
  Unapplying market.0004_seed_market_indices... OK

# DATA A까지 추가로 되돌리기 (EconomicIndicator 11 row 삭제, schema 유지)
$ python manage.py migrate market 0002
  Unapplying market.0003_seed_economic_indicators... OK

# 전체 되돌리기 (schema도 제거)
$ python manage.py migrate market 0001
  Unapplying market.0002_add_sector_group... OK
```

### 4.3 backfill command 사용 예

```bash
# 1) 어떤 series가 백필 미완인지 확인
$ python manage.py backfill_v2_a1 --check-pending
[CHECK] Pending economic (11): ['NFCI', 'ANFCI', ...]
[CHECK] Pending market (11): ['XLF', 'XLK', ...]

# 2) 실 실행 전 dry-run으로 대상 검토
$ python manage.py backfill_v2_a1 --dry-run
[DRY-RUN] 2025-04-29 ~ 2026-04-29
[DRY-RUN] Economic (11): ['NFCI', 'ANFCI', ...]
[DRY-RUN] Market (11): ['XLF', 'XLK', ...]

# 3) 단일 series 테스트 백필
$ python manage.py backfill_v2_a1 --series-id NFCI --from 2025-04-01 --to 2026-04-01
  NFCI: 52 obs inserted
Backfill complete: 52 econ obs (1 series), 0 bars (0 symbols)

# 4) 전체 백필 (운영자 실 실행)
$ python manage.py backfill_v2_a1
  NFCI: 52 obs inserted
  ANFCI: 52 obs inserted
  T10Y2Y: 252 obs inserted
  ... (11 series)
  XLF: 252 bars inserted
  ... (11 symbols)
Backfill complete: 1452 econ obs (11 series), 2772 bars (11 symbols)

# 5) 재실행 (idempotency 확인)
$ python manage.py backfill_v2_a1
  NFCI: 0 obs inserted
  ... (모두 0)
Backfill complete: 0 econ obs (11 series), 0 bars (11 symbols)
```

---

## §5. 테스트 시나리오

### 5.1 Migration 테스트 (`tests/test_migration_a1.py`)

| ID  | 대상         | 시나리오       | 검증                                                                                 |
| --- | ------------ | -------------- | ------------------------------------------------------------------------------------ |
| T1  | 0002         | forward 적용   | `MarketIndex._meta.get_field('sector_group')` 존재, choices 12개                     |
| T2  | 0002         | 기존 row       | 기존 MarketIndex 모든 row의 sector_group=`BENCHMARK` (default 적용 검증)             |
| T3  | 0003         | forward 적용   | `EconomicIndicator.objects.filter(series_id__in=NEW_ECONOMIC_SERIES).count() == 11`  |
| T4  | 0003         | reverse        | reverse 후 11 row 삭제, 기존 series 보존                                             |
| T5  | 0004         | forward 적용   | `MarketIndex.objects.filter(sector_group='TECH').count() >= 1`, BENCHMARK 9          |
| T6  | 0004         | reverse        | sector_group 값만 BENCHMARK 복귀, row 자체 삭제 X                                    |
| T7  | 0002~0004    | 멱등성         | forward → reverse → forward → 동일 상태 (행 수·필드 값 동일)                         |
| T8  | 0003         | get_or_create  | 기존에 존재하는 series_id가 있어도 `IntegrityError` 없이 SKIP                        |
| T9  | 0002         | choices 정합   | `MarketIndex.SECTOR_GROUP_CHOICES`와 0002 안 choices 동일                            |
| T10 | 0003·0004    | 상수 길이 검증 | `assert len(...) == 11` / `== 20` (코드 내 assert가 import 시점에 실패하면 testfail) |
| T11 | 부분 reverse | `migrate 0003` | 0004만 reverse, 0002·0003 유지                                                       |

### 5.2 Backfill command 테스트 (`tests/test_backfill_v2_a1.py`)

| ID  | 시나리오              | 검증                                                                                     |
| --- | --------------------- | ---------------------------------------------------------------------------------------- |
| T12 | --dry-run             | DB 변경 0, stdout에 대상 목록 출력                                                       |
| T13 | --check-pending       | 데이터 0인 series만 출력 (mock으로 일부 series에 데이터 사전 주입)                       |
| T14 | idempotency           | 동일 command 2회 실행 → 두 번째에서 inserted=0                                           |
| T15 | --series-id 단일 실행 | 지정 series만 fetch, 나머지 미호출                                                       |
| T16 | API 부분 실패         | mock에서 1개 series 예외 발생 → 다른 series 정상 진행, 종료 코드 0, stderr에 SKIP 메시지 |
| T17 | --from/--to 범위      | fetch 호출 인자 검증                                                                     |
| T18 | --limit               | 대상 수 제한 동작                                                                        |

### 5.3 통합 테스트 (선택, `tests/test_integration_a1.py`)

- T19: migration 0002~0004 → command 실행 → 검증용 query (sector_group filter, observation 개수) 모두 정상

### 5.4 실행

```bash
pytest backend/apps/market/tests/test_migration_a1.py -v
pytest backend/apps/market/tests/test_backfill_v2_a1.py -v
```

---

## §6. DoD (Definition of Done)

### 6.1 머지 전 (CI 자동 검증 + 본인 확인)

- [ ] `python manage.py migrate market` 성공 (0002 → 0003 → 0004 순)
- [ ] 단계별 reverse 성공:
  - [ ] `python manage.py migrate market 0003` (0004만 되돌리기)
  - [ ] `python manage.py migrate market 0002` (0003까지 되돌리기)
  - [ ] `python manage.py migrate market 0001` (전체 되돌리기)
  - [ ] `python manage.py migrate market` (재적용)
- [ ] `python manage.py makemigrations market --check --dry-run` → "No changes detected"
- [ ] `python manage.py check` 무경고
- [ ] `pytest backend/apps/market/tests/test_migration_a1.py -v` PASS (T1~T11)
- [ ] `pytest backend/apps/market/tests/test_backfill_v2_a1.py -v` PASS (T12~T18)
- [ ] `ECONOMIC_INDICATORS_NEW` 정확히 11개 / `MARKET_INDEX_SECTOR_MAPPING` 정확히 20개 (assert로 자동 검증됨)
- [ ] PR 설명에 §6.2 Post-merge 체크리스트 명시

### 6.2 머지 후 (운영자=본인) — PR 템플릿 고정 섹션

- [ ] DEV 환경 migration 적용
- [ ] `python manage.py backfill_v2_a1 --check-pending` → 11 series + 11 symbols pending 확인
- [ ] `python manage.py backfill_v2_a1 --dry-run` → 대상 검토
- [ ] `python manage.py backfill_v2_a1` 실행 → 로그 검토 (SKIP 발생 시 원인 추적)
- [ ] DB 검증:
  - 신규 series별 `EconomicObservation` ≥ 50 (주별) 또는 ≥ 200 (일별)
  - 신규 symbol별 `OHLC` ≥ 200 (영업일 1년)
- [ ] Celery beat에 신규 series/symbol 정기 fetch 작업 등록 확인 (별도 PR 영역일 수 있음 — 추적용 이슈만 생성)

---

## §7. 금지 사항

| #   | 금지 행위                                                                                      | 사유                                                                                                 |
| --- | ---------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| F1  | migration 안에서 외부 API(FRED, Yahoo, Polygon 등) 호출                                        | 머지 후 새벽 장애 위험. Decision C-Ⅱ 결정의 핵심 사유                                                |
| F2  | `RunPython.noop` 사용                                                                          | 모든 RunPython은 정확한 reverse 함수 페어 필수. 부분 롤백 가능성 W3 확보가 A-Ⅲ 추천 근거             |
| F3  | 한 migration 파일에 schema 변경과 data 변경 혼재                                               | A-Ⅲ 3분리 결정 위반. 0002=schema, 0003=DATA A, 0004=DATA B 엄격 분리                                 |
| F4  | 운영 DB로 직접 SQL `INSERT/UPDATE/DELETE`                                                      | 변경 이력 추적 불가                                                                                  |
| F5  | 매핑(`ECONOMIC_INDICATORS_NEW` / `MARKET_INDEX_SECTOR_MAPPING`) 변경 시 본 migration 직접 수정 | Django 관행 위반. 변경은 새 migration 작성                                                           |
| F6  | `get_or_create` 대신 `create` 사용                                                             | idempotency 깨짐. 재실행 시 IntegrityError                                                           |
| F7  | `from apps.market.models import MarketIndex` (migration 안)                                    | historical model 미사용 → 미래 schema 변경 시 깨짐. 반드시 `apps.get_model("market", "MarketIndex")` |
| F8  | API 토큰/비밀키 하드코딩                                                                       | 보안. env var 또는 Django settings 사용                                                              |
| F9  | 기존 v1 데이터 손상 (MarketIndex 기존 row의 다른 필드 수정)                                    | PR 범위 외                                                                                           |
| F10 | `MarketPulseNews`, `RegimeSnapshot` 등 v2 다른 모델 생성                                       | PR-A2 영역 — 본 PR 범위 외                                                                           |
| F11 | `db_index=False` 또는 인덱스 생략                                                              | sector_group은 PR-C/G의 query 핵심 필터                                                              |
| F12 | command에서 `transaction.atomic` 없이 다중 row 적재                                            | 부분 실패 시 일관성 깨짐                                                                             |
| F13 | migration `dependencies` 체인을 끊거나 건너뛰기                                                | 0002 → 0003 → 0004 일렬 의존 동결                                                                    |
| F14 | 명명 규약 위반 (`000X_<verb>_<object>.py`)                                                     | A2/A3 패턴 재사용 일관성 깨짐                                                                        |

---

## 참고: 본 위임 프롬프트의 결정 근거

| 결정              | 선택                                                                          | 위임 프롬프트 반영 위치                                                |
| ----------------- | ----------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| **A-Ⅲ 3분리**     | §3.2~3.4 독립 migration 파일 3개 (0002 / 0003 / 0004)                         | §1.4 명명 규약, §4.2 부분 reverse 예시, §6.1 단계별 DoD, §7 F3·F13·F14 |
| B-Ⅰ dict 하드코딩 | §3.3·3.4 모듈 상수 (`ECONOMIC_INDICATORS_NEW`, `MARKET_INDEX_SECTOR_MAPPING`) | §7 F5                                                                  |
| C-Ⅱ 수동 command  | §3.5 `backfill_v2_a1.py`                                                      | §1.2, §6.2, §7 F1                                                      |
