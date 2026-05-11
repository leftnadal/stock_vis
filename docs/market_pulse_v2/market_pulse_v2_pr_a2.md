# PR-A2 위임 프롬프트 — 기반 모델 5개 (marketpulse 앱 scaffold)

> **메타 정보**
>
> - PR ID: PR-A2
> - 영역: 신규 Django 앱 scaffold + 5개 모델
> - 의존 PR: 없음 (A1과 독립, FK 없음)
> - 후속 의존: PR-B(News fetcher), PR-C(Regime), PR-D(Anomaly), PR-E(Brief)
> - 견적: 6.5h ± 1.0h (PERT P50, 도메인별 분리 반영)
> - 결정 패키지: **A2-A.Ⅱ(models 도메인 분리) + A2-B.Ⅱ(schemas 도메인 분리) + A2-C.Ⅰ(user FK CASCADE)**
> - 동결 결정 인용: D5(영구/90일 TTL) · D8(SET_NULL/PROTECT/CASCADE) · D9(Pydantic) · 4A prefix · is_finalized(RegimeSnapshot)

---

## §1. 컨텍스트

### 1.1 프로젝트 배경

- 프로젝트: **Market Pulse v2 Phase 1**
- 위치: `backend/marketpulse/` (신규 Django 앱)
- 스택: Django 4.x + PostgreSQL + Pydantic v2
- 본 PR-A2는 신규 `marketpulse` 앱을 처음 scaffold하고 5개 기반 모델을 정의. **PR-A2는 스키마만** 추가, 데이터 적재는 후속 PR(B/C/D/E)이 책임.

### 1.2 본 PR의 목표

신규 `marketpulse` Django 앱 생성 + 다음 5개 모델 정의 (Django 표준 `0001_initial.py` 단일 마이그레이션 파일):

| #   | 모델               | 책임                                                | 후속 PR |
| --- | ------------------ | --------------------------------------------------- | ------- |
| 1   | `MarketPulseNews`  | 뉴스 풀, 6 카테고리, D5 TTL 정책                    | PR-B    |
| 2   | `NewsViewLog`      | 24h 노출 추적, user CASCADE                         | PR-I    |
| 3   | `AnomalySignalLog` | 4 Core 룰 발동 기록, paired_news SET_NULL           | PR-D    |
| 4   | `RegimeSnapshot`   | 일별 레짐 판정, typed+JSON 하이브리드, is_finalized | PR-C    |
| 5   | `BriefingLog`      | Card E LLM 일일 출력 기록                           | PR-E    |

JSONField 검증을 위한 Pydantic schemas는 도메인별 4개 파일(`schemas/news.py`, `schemas/anomaly.py`, `schemas/regime.py`, `schemas/briefing.py`).

### 1.3 의존성

- **상위 PR**: 없음 (PR-A1과 독립적, FK 관계 없음)
- **하위 PR**: PR-B/C/D/E (각자 자신의 도메인 모델 사용), PR-I(API에서 통합 조회)
- **외부 의존**: Django `auth.User` (`NewsViewLog.user` FK, v1 기존 User 모델)

### 1.4 도메인별 분리 패턴 (A2-A.Ⅱ + A2-B.Ⅱ)

후속 4개 PR(B/C/D/E)이 각자 자신의 도메인 파일만 수정하도록 1:1 대응 구조를 강제:

```
backend/marketpulse/
├── models/
│   ├── __init__.py        # re-export all
│   ├── news.py            # MarketPulseNews + NewsViewLog (PR-B 영역)
│   ├── anomaly.py         # AnomalySignalLog (PR-D 영역)
│   ├── regime.py          # RegimeSnapshot (PR-C 영역, is_finalized 포함)
│   └── briefing.py        # BriefingLog (PR-E 영역)
├── schemas/
│   ├── __init__.py        # re-export all
│   ├── news.py            # NewsEntities Pydantic
│   ├── anomaly.py         # R02/R04/R09/R12 Evidence Pydantic
│   ├── regime.py          # IndicatorsSnapshot, MatchedConditions, PendingTransition
│   └── briefing.py        # BriefingSection
├── migrations/
│   └── 0001_initial.py    # Django 표준 — 5개 모델 한 파일에 (신규 앱 scaffold)
├── admin/
│   ├── __init__.py
│   └── ...                # 도메인별 분리 (선택)
└── apps.py
```

**명명 규약 동결**: `models/<domain>.py` ↔ `schemas/<domain>.py` 1:1 대응. 도메인명 단수형(`news`, `anomaly`, `regime`, `briefing`).

### 1.5 결정 패키지의 의미

- **A2-A.Ⅱ + A2-B.Ⅱ**: PR-A1의 A-Ⅲ(3분리) 정신을 코드 organization으로 확장. 후속 PR이 git diff 충돌 없이 병행 가능.
- **A2-C.Ⅰ CASCADE**: NewsViewLog는 24h TTL 데이터로 보존 가치 낮음. GDPR/PIPA 잊혀질 권리 정합. v1 기존 user FK 정책과 일관.

---

## §2. 변경 파일

### 2.1 신규 파일 (15개)

```
backend/marketpulse/__init__.py
backend/marketpulse/apps.py

backend/marketpulse/models/__init__.py
backend/marketpulse/models/news.py
backend/marketpulse/models/anomaly.py
backend/marketpulse/models/regime.py
backend/marketpulse/models/briefing.py

backend/marketpulse/schemas/__init__.py
backend/marketpulse/schemas/news.py
backend/marketpulse/schemas/anomaly.py
backend/marketpulse/schemas/regime.py
backend/marketpulse/schemas/briefing.py

backend/marketpulse/migrations/__init__.py
backend/marketpulse/migrations/0001_initial.py

backend/marketpulse/admin/__init__.py        # 또는 단일 admin.py — §3.6 참고
```

### 2.2 신규 테스트 파일 (5개)

```
backend/tests/marketpulse/__init__.py
backend/tests/marketpulse/test_models_news.py
backend/tests/marketpulse/test_models_anomaly.py
backend/tests/marketpulse/test_models_regime.py
backend/tests/marketpulse/test_models_briefing.py
backend/tests/marketpulse/test_schemas.py    # Pydantic validation 테스트 통합
```

### 2.3 수정 파일 (1~2개)

```
backend/config/settings.py        # INSTALLED_APPS에 'marketpulse' 추가
backend/config/urls.py            # (선택, PR-I에서 처리하면 본 PR에서는 변경 없음)
```

### 2.4 변경 금지 파일

- `backend/apps/market/` 하위 모든 파일 (PR-A1 영역)
- 다른 v1 앱의 모델
- 본 PR 범위 외 모델 (BreadthSnapshot, SectorFlowSnapshot, ConcentrationSnapshot은 PR-A3 영역)
- `settings.py`의 INSTALLED_APPS 외 다른 설정
- `urls.py`의 v2 API 라우팅 (PR-I 영역)

---

## §3. 수도코드 (실 코드 + 의사코드)

### 3.1 `apps.py`

```python
# backend/marketpulse/apps.py
from django.apps import AppConfig


class MarketPulseConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "marketpulse"
    verbose_name = "Market Pulse v2"
```

### 3.2 `models/news.py` (MarketPulseNews + NewsViewLog)

```python
"""뉴스 도메인 모델. PR-B(news fetcher), PR-I(news refresh API)가 사용."""
from django.db import models
from django.conf import settings


class MarketPulseNews(models.Model):
    """
    뉴스 풀. FMP General/Stock News + Marketaux에서 수집. 6 카테고리 분류.

    D5 TTL 정책:
    - shown_on_layer0=True 전환 시 expires_at=NULL (영구 보존)
    - 미노출 상태는 published_at + 90 days
    - PR-O의 purge_expired_news task가 expires_at < now AND shown_on_layer0=False 삭제
    """

    CATEGORY_CHOICES = [
        ("MACRO",       "Macro"),
        ("GEOPOLITICS", "Geopolitics & Policy"),
        ("SECTOR",      "Sector"),
        ("INDEX",       "Index Event"),
        ("MAG7",        "Magnificent 7"),
        ("SMART_MONEY", "Smart Money"),
    ]
    SOURCE_CHOICES = [
        ("FMP_GENERAL", "FMP General News"),
        ("FMP_STOCK",   "FMP Stock News"),
        ("MARKETAUX",   "Marketaux"),
    ]

    # 식별
    external_id = models.CharField(max_length=128, db_index=True)
    source = models.CharField(max_length=16, choices=SOURCE_CHOICES)
    url = models.URLField(max_length=1024)

    # 본문
    title = models.CharField(max_length=512)
    summary = models.TextField(blank=True)
    summary_ko = models.TextField(blank=True)  # Phase 2 LLM 번역

    # 분류
    category = models.CharField(max_length=16, choices=CATEGORY_CHOICES, db_index=True)
    category_confidence = models.FloatField(default=0.0)  # 0.0~1.0

    # 엔티티 (페어링용 — JSON, Pydantic NewsEntities 검증)
    entities = models.JSONField(default=dict)
    # 예: {"tickers": ["AAPL","MSFT"], "sectors": ["XLK"], "topics": ["Fed","CPI"]}

    # 점수
    relevance_score = models.FloatField(default=0.0)
    sentiment_score = models.FloatField(null=True, blank=True)  # -1.0~1.0

    # 노출 추적
    shown_on_layer0 = models.BooleanField(default=False, db_index=True)
    shown_at = models.DateTimeField(null=True, blank=True)
    paired_with_anomaly = models.BooleanField(default=False)

    # TTL (D5)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    # NULL = 영구 보존 (shown_on_layer0=True 시점에 NULL로 전환)

    # 메타
    published_at = models.DateTimeField(db_index=True)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_id"],
                name="uniq_news_source_extid",
            ),
        ]
        indexes = [
            models.Index(fields=["category", "-published_at"]),
            models.Index(fields=["-published_at", "shown_on_layer0"]),
            models.Index(fields=["expires_at"]),  # TTL purge 쿼리용
        ]
        ordering = ["-published_at"]

    def __str__(self):
        return f"[{self.category}] {self.title[:60]}"


class NewsViewLog(models.Model):
    """
    Layer 0 뉴스 6건 노출 추적. 24h unique 보장 → 사용자가 같은 뉴스를 24h 내 다시 보지 않음.

    A2-C.Ⅰ CASCADE: 사용자 삭제 시 viewlog 자동 삭제 (24h TTL 데이터 = 보존 가치 낮음).
    GDPR/PIPA 잊혀질 권리 정합.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,        # A2-C.Ⅰ
        related_name="news_view_logs",
    )
    news = models.ForeignKey(
        MarketPulseNews,
        on_delete=models.CASCADE,        # 뉴스 삭제 시 viewlog도 삭제 (24h TTL)
        related_name="view_logs",
    )
    viewed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)  # 보통 viewed_at + 24h

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "news"],
                name="uniq_news_view_user_news",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "-viewed_at"]),
            models.Index(fields=["expires_at"]),  # purge용
        ]
        ordering = ["-viewed_at"]

    def __str__(self):
        return f"User {self.user_id} viewed news {self.news_id} at {self.viewed_at}"
```

### 3.3 `models/anomaly.py`

```python
"""이상 신호 도메인. PR-D(anomaly engine)가 사용."""
from django.db import models

from .news import MarketPulseNews


class AnomalySignalLog(models.Model):
    """
    이상 신호 탐지 결과. 4개 Core 규칙(R02, R04, R09, R12) 발동 기록.

    D8 정책:
    - paired_news=SET_NULL: 뉴스 삭제 후에도 신호 로그 보존
    """

    AXIS_CHOICES = [
        ("flow", "Flow"),
        ("capital", "Capital"),
    ]
    RULE_ID_CHOICES = [
        ("R02", "R02 concentration_extreme"),
        ("R04", "R04 vix_spike"),
        ("R09", "R09 sector_extreme_z"),
        ("R12", "R12 dispersion_spike"),
    ]
    DISPLAY_MODE_CHOICES = [
        ("ANOMALY", "Anomaly"),
        ("HYBRID",  "Hybrid"),
        ("CALM",    "Calm"),
    ]

    # 식별
    rule_id = models.CharField(max_length=16, choices=RULE_ID_CHOICES, db_index=True)
    rule_version = models.CharField(max_length=16, default="v0.2")

    # 분류
    axis = models.CharField(max_length=16, choices=AXIS_CHOICES)
    related_card = models.CharField(max_length=4, null=True, blank=True)  # 'A','B','C','D'

    # 표시 콘텐츠
    headline = models.CharField(max_length=255)
    detail = models.TextField()

    # 점수
    severity = models.IntegerField()       # 1~5
    rarity_score = models.FloatField()     # 0.0~1.0
    final_score = models.FloatField()      # severity*0.4 + rarity*0.4 (사전계산)

    # 근거 (JSON — 규칙별 가변 구조, Pydantic R02Evidence/R04/R09/R12 검증)
    evidence = models.JSONField(default=dict)

    # 페어링 (D8: SET_NULL)
    paired_news = models.ForeignKey(
        MarketPulseNews,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="paired_signals",
    )

    # 노출 상태
    shown_on_layer0 = models.BooleanField(default=False, db_index=True)
    display_mode = models.CharField(
        max_length=16,
        choices=DISPLAY_MODE_CHOICES,
        null=True, blank=True,
    )

    # 시간
    detected_at = models.DateTimeField(db_index=True)
    detection_date = models.DateField(db_index=True)  # KST 기준 거래일

    class Meta:
        indexes = [
            models.Index(fields=["rule_id", "-detected_at"]),
            models.Index(fields=["-detected_at", "shown_on_layer0"]),
            models.Index(fields=["detection_date", "axis"]),
        ]
        ordering = ["-detected_at"]

    def __str__(self):
        return f"[{self.rule_id}] sev={self.severity} {self.headline[:50]}"
```

### 3.4 `models/regime.py`

```python
"""레짐 판정 도메인. PR-C(regime classifier)가 사용. is_finalized 정책 포함."""
from django.db import models


class RegimeSnapshot(models.Model):
    """
    Card A 핵심. 일별 1 row. 14개 입력 지표·판정 결과·히스테리시스 상태 보관.

    is_finalized 정책 (동결 §2.5):
    - 장중 임시 row는 is_finalized=False
    - KST 05:30 finalize task가 finalized=True + finalized_at 마킹
    """

    REGIME_CHOICES = [
        ("RISK_ON_EXPANSION",     "강세 확장"),
        ("LATE_CYCLE_CAUTION",    "상승 후반 경계"),
        ("TRANSITION",            "전환"),
        ("RISK_OFF_CONTRACTION",  "약세 수축"),
        ("CRISIS",                "위기"),
        ("INSUFFICIENT_DATA",     "데이터 부족"),
    ]
    LAYER_STATE_CHOICES = [
        ("strong",     "Strong"),
        ("weak",       "Weak"),
        ("mixed",      "Mixed"),
        ("greed",      "Greed"),
        ("fear",       "Fear"),
        ("neutral",    "Neutral"),
        ("easing",     "Easing"),
        ("tightening", "Tightening"),
        ("crisis",     "Crisis"),
        ("unknown",    "Unknown"),
    ]

    # 식별
    date = models.DateField(unique=True, db_index=True)

    # 판정 결과 (typed)
    regime = models.CharField(max_length=32, choices=REGIME_CHOICES)
    confidence = models.IntegerField(default=0)  # 0~100

    # 레이어 상태 (typed — Card A 펼침 직접 노출)
    price_layer = models.CharField(max_length=16, choices=LAYER_STATE_CHOICES)
    sentiment_layer = models.CharField(max_length=16, choices=LAYER_STATE_CHOICES)
    structural_layer = models.CharField(max_length=16, choices=LAYER_STATE_CHOICES)

    # 변화 정보 (typed)
    yesterday_regime = models.CharField(max_length=32, null=True, blank=True)
    is_transition = models.BooleanField(default=False)
    days_in_regime = models.IntegerField(default=1)

    # JSON 영역 (Pydantic 검증)
    indicators_snapshot = models.JSONField(default=dict)   # 14 지표 raw 값
    matched_conditions = models.JSONField(default=list)    # 규칙 매칭 근거
    pending_transition = models.JSONField(null=True, blank=True)
    # 예: {"target": "CRISIS", "candidate_since": "2026-04-25", "days_pending": 1}

    # 메타
    data_coverage = models.FloatField(default=0.0)  # 0.0~1.0
    rule_version = models.CharField(max_length=16, default="v0.2")

    # is_finalized (동결 §2.5)
    is_finalized = models.BooleanField(default=False, db_index=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    calculated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["-date"]),
            models.Index(fields=["regime", "-date"]),
            models.Index(fields=["is_finalized", "-date"]),
        ]
        ordering = ["-date"]

    def __str__(self):
        finalized = "✓" if self.is_finalized else "△"
        return f"{self.date} {self.regime} (conf={self.confidence}) {finalized}"
```

### 3.5 `models/briefing.py`

```python
"""Card E 브리핑 도메인. PR-E(LLM brief generator)가 사용."""
from django.db import models


class BriefingLog(models.Model):
    """
    Card E (Today's Brief) LLM 출력 일일 기록.
    매일 KST 06:15 1회 생성. 일일 멱등(date unique).
    """

    STATUS_CHOICES = [
        ("PENDING",  "Pending"),
        ("SUCCESS",  "Success"),
        ("FAILED",   "Failed"),
        ("FALLBACK", "Fallback (template-based)"),
    ]

    # 식별
    date = models.DateField(db_index=True)

    # 산출물
    headline = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)            # 3~4 문단
    body_sections = models.JSONField(default=list)
    # 예: [{"section": "regime", "title": "...", "text": "..."}]

    # 입력 추적 (재현성, Phase 2 백테스트·감사용)
    prompt_inputs = models.JSONField(default=dict)

    # LLM 메타
    model_name = models.CharField(max_length=64, default="gemini-2.5-flash")
    model_version = models.CharField(max_length=32, default="v1")
    prompt_tokens = models.IntegerField(null=True, blank=True)
    output_tokens = models.IntegerField(null=True, blank=True)
    cost_usd = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)

    # 상태
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="PENDING")
    error_message = models.TextField(blank=True)

    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["date", "model_version"],
                name="uniq_briefing_date_modelver",
            ),
        ]
        indexes = [
            models.Index(fields=["-date"]),
            models.Index(fields=["status", "-date"]),
        ]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.date} [{self.status}] {self.headline[:50]}"
```

### 3.6 `models/__init__.py` (re-export)

```python
"""All marketpulse models. Import from `marketpulse.models import X`."""
from .news import MarketPulseNews, NewsViewLog
from .anomaly import AnomalySignalLog
from .regime import RegimeSnapshot
from .briefing import BriefingLog

__all__ = [
    "MarketPulseNews",
    "NewsViewLog",
    "AnomalySignalLog",
    "RegimeSnapshot",
    "BriefingLog",
]
```

### 3.7 `schemas/news.py` (Pydantic v2)

```python
"""뉴스 JSONField 검증. MarketPulseNews.entities 용."""
from pydantic import BaseModel, Field


class NewsEntities(BaseModel):
    """MarketPulseNews.entities JSON 스키마."""
    tickers: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)  # XLF, XLK 등 ETF symbol
    topics: list[str] = Field(default_factory=list)   # Fed, CPI, FOMC 등 키워드

    class Config:
        json_schema_extra = {
            "example": {
                "tickers": ["AAPL", "MSFT"],
                "sectors": ["XLK"],
                "topics": ["Fed", "CPI"],
            }
        }
```

### 3.8 `schemas/anomaly.py`

```python
"""4 Core 룰별 evidence Pydantic 스키마. AnomalySignalLog.evidence 용."""
from typing import Literal
from pydantic import BaseModel


class R02Evidence(BaseModel):
    """concentration_extreme — 상위 5종목 기여도 극단."""
    universe: str                   # "SPY"
    top5_contrib: float             # 0~1
    top5_pct_1y: float              # 0~1
    threshold_pct: float = 0.85
    breadth_50ma: float             # 보조 — 30 미만이면 더 위험


class R04Evidence(BaseModel):
    """vix_spike — VIX 급등."""
    vix_today: float
    vix_yesterday: float
    pct_change: float
    vix_pct_1y: float
    threshold_abs: float = 30.0
    threshold_pct: float = 0.80


class R09Evidence(BaseModel):
    """sector_extreme_z — 섹터 Z-score 극단."""
    sector_etf: str                 # "XLE", "XLK" 등
    z_score_temporal: float         # 자기 시계열 대비
    z_score_cross: float            # 같은 날 섹터 간 cross-sectional
    threshold_z: float = 2.5
    direction: Literal["up", "down"]


class R12Evidence(BaseModel):
    """dispersion_spike — 섹터 분산 극단."""
    dispersion_today: float
    dispersion_pct_1y: float
    threshold_pct: float = 0.85
```

### 3.9 `schemas/regime.py`

```python
"""RegimeSnapshot의 3개 JSONField Pydantic 스키마."""
from typing import Literal
from pydantic import BaseModel, Field


class IndicatorValue(BaseModel):
    """14 지표 중 1개의 raw 값 + 메타."""
    name: str                       # "nfci", "vix_level" 등
    value: float | None             # null = 데이터 누락
    source: str                     # "FRED:NFCI" 등
    fetched_at: str                 # ISO datetime


class IndicatorsSnapshot(BaseModel):
    """RegimeSnapshot.indicators_snapshot — 14 지표 raw 값 보관."""
    indicators: list[IndicatorValue]
    coverage_ratio: float = Field(ge=0.0, le=1.0)


class MatchedCondition(BaseModel):
    """한 매칭 근거."""
    indicator: str
    threshold_expr: str             # ">= 0", "< 30" 등
    actual_value: float | None
    status: Literal["matched", "unmatched", "missing"]


class PendingTransition(BaseModel):
    """히스테리시스 상태."""
    target: str                     # "CRISIS" 등
    candidate_since: str            # ISO date
    days_pending: int = Field(ge=0)
```

### 3.10 `schemas/briefing.py`

```python
"""BriefingLog의 body_sections Pydantic 스키마."""
from typing import Literal
from pydantic import BaseModel


class BriefingSection(BaseModel):
    """Card E 본문 섹션 1개."""
    section: Literal["regime", "flow", "macro", "focus"]
    title: str
    text: str
```

### 3.11 `schemas/__init__.py` (re-export)

```python
"""All marketpulse Pydantic schemas."""
from .news import NewsEntities
from .anomaly import R02Evidence, R04Evidence, R09Evidence, R12Evidence
from .regime import (
    IndicatorValue,
    IndicatorsSnapshot,
    MatchedCondition,
    PendingTransition,
)
from .briefing import BriefingSection

__all__ = [
    "NewsEntities",
    "R02Evidence", "R04Evidence", "R09Evidence", "R12Evidence",
    "IndicatorValue", "IndicatorsSnapshot",
    "MatchedCondition", "PendingTransition",
    "BriefingSection",
]
```

### 3.12 `migrations/0001_initial.py` (골격)

```python
"""
PR-A2: marketpulse 앱 scaffold + 5개 기반 모델 생성.

⚠️ Django 표준 0001_initial — 신규 앱이라 단일 파일 강제.
A1과 달리 PR-A2는 빈 테이블만 생성 — 데이터 적재는 후속 PR(B/C/D/E).
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MarketPulseNews",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("external_id", models.CharField(max_length=128, db_index=True)),
                # ... §3.2 모든 필드 그대로 ...
            ],
            options={"ordering": ["-published_at"]},
        ),
        migrations.CreateModel(
            name="AnomalySignalLog",
            # ... §3.3
        ),
        migrations.CreateModel(
            name="RegimeSnapshot",
            # ... §3.4
        ),
        migrations.CreateModel(
            name="BriefingLog",
            # ... §3.5
        ),
        migrations.CreateModel(
            name="NewsViewLog",
            # ... §3.2 (MarketPulseNews 다음에 와야 FK 가능)
        ),
        # 인덱스·제약은 각 CreateModel.options에 포함하거나 AddConstraint/AddIndex로 분리
    ]
```

> ⚠️ 위는 골격 — 실제 작성은 `python manage.py makemigrations marketpulse` 자동 생성 결과를 그대로 사용. 수동 작성 시 필드 누락 위험.

### 3.13 `admin/__init__.py` (선택, 도메인별 분리)

각 모델을 Django Admin에 등록. 후속 PR에서 list_display·search_fields 보강 가능. 본 PR은 기본 등록만.

```python
"""Django admin registration for marketpulse models."""
from django.contrib import admin

from marketpulse.models import (
    MarketPulseNews,
    NewsViewLog,
    AnomalySignalLog,
    RegimeSnapshot,
    BriefingLog,
)


@admin.register(MarketPulseNews)
class MarketPulseNewsAdmin(admin.ModelAdmin):
    list_display = ("category", "title", "source", "published_at", "shown_on_layer0")
    list_filter = ("category", "source", "shown_on_layer0")
    search_fields = ("title", "url", "external_id")
    date_hierarchy = "published_at"


@admin.register(NewsViewLog)
class NewsViewLogAdmin(admin.ModelAdmin):
    list_display = ("user", "news", "viewed_at", "expires_at")
    list_filter = ("viewed_at",)
    raw_id_fields = ("user", "news")


@admin.register(AnomalySignalLog)
class AnomalySignalLogAdmin(admin.ModelAdmin):
    list_display = ("rule_id", "axis", "severity", "headline", "detected_at", "shown_on_layer0")
    list_filter = ("rule_id", "axis", "shown_on_layer0", "display_mode")
    search_fields = ("headline", "detail")
    raw_id_fields = ("paired_news",)
    date_hierarchy = "detected_at"


@admin.register(RegimeSnapshot)
class RegimeSnapshotAdmin(admin.ModelAdmin):
    list_display = ("date", "regime", "confidence", "is_finalized", "data_coverage")
    list_filter = ("regime", "is_finalized")
    date_hierarchy = "date"


@admin.register(BriefingLog)
class BriefingLogAdmin(admin.ModelAdmin):
    list_display = ("date", "status", "headline", "model_name", "cost_usd")
    list_filter = ("status", "model_name")
    search_fields = ("headline", "body")
    date_hierarchy = "date"
```

### 3.14 `settings.py` 수정

```python
# backend/config/settings.py
INSTALLED_APPS = [
    # ... 기존 v1 앱들 ...
    "apps.market",      # v1 (PR-A1이 확장)
    "marketpulse",      # ⭐ NEW — PR-A2가 추가
]
```

---

## §4. 입출력 예시

### 4.1 Migration forward

```bash
$ python manage.py makemigrations marketpulse
Migrations for 'marketpulse':
  marketpulse/migrations/0001_initial.py
    - Create model MarketPulseNews
    - Create model AnomalySignalLog
    - Create model RegimeSnapshot
    - Create model BriefingLog
    - Create model NewsViewLog
    - Create constraint uniq_news_source_extid on model marketpulsenews
    - Create constraint uniq_news_view_user_news on model newsviewlog
    - Create constraint uniq_briefing_date_modelver on model briefinglog
    - Create index ... (여러 개)

$ python manage.py migrate marketpulse
Operations to perform:
  Apply all migrations: marketpulse
Running migrations:
  Applying marketpulse.0001_initial... OK

# 검증
$ python manage.py shell -c "
from marketpulse.models import MarketPulseNews, NewsViewLog, AnomalySignalLog, RegimeSnapshot, BriefingLog
for M in [MarketPulseNews, NewsViewLog, AnomalySignalLog, RegimeSnapshot, BriefingLog]:
    print(f'{M._meta.label:40} -> {M._meta.db_table:35} fields: {len(M._meta.fields)}')
    print(f'  count: {M.objects.count()}')
"
# 기대 출력:
# marketpulse.MarketPulseNews    -> marketpulse_marketpulsenews    fields: 17  count: 0
# marketpulse.NewsViewLog        -> marketpulse_newsviewlog        fields: 5   count: 0
# marketpulse.AnomalySignalLog   -> marketpulse_anomalysignallog   fields: 16  count: 0
# marketpulse.RegimeSnapshot     -> marketpulse_regimesnapshot     fields: 17  count: 0
# marketpulse.BriefingLog        -> marketpulse_briefinglog        fields: 13  count: 0
```

### 4.2 Migration reverse

```bash
$ python manage.py migrate marketpulse zero
Operations to perform:
  Unapply all migrations: marketpulse
Running migrations:
  Unapplying marketpulse.0001_initial... OK

# 5개 테이블 모두 DROP. 외부 v1 영향 없음.
```

### 4.3 Pydantic schema 사용 예 (테스트·후속 PR)

```python
from marketpulse.schemas import NewsEntities, R04Evidence

# fetcher에서 entities 검증
entities = NewsEntities(tickers=["AAPL"], topics=["Fed"])
news = MarketPulseNews.objects.create(
    ...,
    entities=entities.model_dump(),  # JSON으로 직렬화
)

# anomaly engine에서 evidence 검증
evidence = R04Evidence(
    vix_today=32.4, vix_yesterday=18.2,
    pct_change=0.78, vix_pct_1y=0.92,
    threshold_abs=30.0, threshold_pct=0.80,
)
AnomalySignalLog.objects.create(
    rule_id="R04",
    ...,
    evidence=evidence.model_dump(),
)
```

### 4.4 NewsViewLog CASCADE 동작 검증

```python
>>> from django.contrib.auth import get_user_model
>>> from marketpulse.models import MarketPulseNews, NewsViewLog
>>> User = get_user_model()
>>> u = User.objects.create_user("test", "test@example.com", "pwd")
>>> n = MarketPulseNews.objects.create(...)
>>> NewsViewLog.objects.create(user=u, news=n, expires_at=...)
>>> NewsViewLog.objects.count()
1
>>> u.delete()  # 사용자 삭제
>>> NewsViewLog.objects.count()
0  # CASCADE 동작 확인
```

---

## §5. 테스트 시나리오

### 5.1 News 도메인 (`test_models_news.py`)

| ID  | 시나리오                               | 검증                                                                          |
| --- | -------------------------------------- | ----------------------------------------------------------------------------- |
| T1  | MarketPulseNews 6 카테고리 enum        | `CATEGORY_CHOICES` MACRO/GEOPOLITICS/SECTOR/INDEX/MAG7/SMART_MONEY 정확히 6개 |
| T2  | source/external_id unique              | 동일 (source, external_id) 두 번째 INSERT 시 IntegrityError                   |
| T3  | shown_on_layer0 → expires_at NULL 토글 | model 메서드 또는 service 함수 (PR-B에서 구현, 본 PR은 인덱스만 검증)         |
| T4  | NewsViewLog (user, news) unique        | 동일 user × news 두 번째 INSERT 시 IntegrityError                             |
| T5  | NewsViewLog user CASCADE               | user 삭제 → NewsViewLog count 0                                               |
| T6  | NewsViewLog news CASCADE               | news 삭제 → NewsViewLog count 0                                               |
| T7  | TTL 인덱스 존재                        | `expires_at` 인덱스 SQL 검증                                                  |

### 5.2 Anomaly 도메인 (`test_models_anomaly.py`)

| ID  | 시나리오             | 검증                                                      |
| --- | -------------------- | --------------------------------------------------------- |
| T8  | rule_id enum 4종     | R02/R04/R09/R12 정확히 4개                                |
| T9  | axis enum            | flow/capital 정확히 2개                                   |
| T10 | paired_news SET_NULL | news 삭제 후 signal.paired_news IS NULL, signal 자체 보존 |
| T11 | display_mode enum    | ANOMALY/HYBRID/CALM 정확히 3개                            |
| T12 | severity 정수 1~5    | (validator는 Phase 2, 본 PR은 IntegerField만 검증)        |

### 5.3 Regime 도메인 (`test_models_regime.py`)

| ID  | 시나리오                  | 검증                                                                         |
| --- | ------------------------- | ---------------------------------------------------------------------------- |
| T13 | regime enum 6종           | RISK_ON/LATE_CYCLE/TRANSITION/RISK_OFF/CRISIS/INSUFFICIENT_DATA              |
| T14 | layer_state enum          | 10개 (strong/weak/mixed/greed/fear/neutral/easing/tightening/crisis/unknown) |
| T15 | date unique               | 같은 date 두 번째 INSERT 시 IntegrityError                                   |
| T16 | is_finalized 기본값 False | `RegimeSnapshot()` 생성 시 is_finalized=False                                |
| T17 | finalized_at nullable     | is_finalized=False일 때 finalized_at NULL OK                                 |

### 5.4 Briefing 도메인 (`test_models_briefing.py`)

| ID  | 시나리오                     | 검증                                               |
| --- | ---------------------------- | -------------------------------------------------- |
| T18 | (date, model_version) unique | 동일 date+version 두 번째 INSERT 시 IntegrityError |
| T19 | status enum 4종              | PENDING/SUCCESS/FAILED/FALLBACK                    |
| T20 | cost_usd 정밀도              | DecimalField max_digits=8, decimal_places=4        |

### 5.5 Pydantic schemas (`test_schemas.py`)

| ID  | 시나리오                               | 검증                                              |
| --- | -------------------------------------- | ------------------------------------------------- |
| T21 | NewsEntities 빈 default                | `NewsEntities()` → tickers/sectors/topics 모두 [] |
| T22 | R02Evidence 필수 필드                  | `R02Evidence(universe="SPY")` ValidationError     |
| T23 | R04Evidence 정상 케이스                | 모든 float 필드 채워서 검증 통과                  |
| T24 | R09Evidence direction Literal          | `direction="sideways"` ValidationError            |
| T25 | IndicatorsSnapshot coverage_ratio 범위 | -0.1 또는 1.1 ValidationError                     |
| T26 | BriefingSection section Literal        | `section="other"` ValidationError                 |

### 5.6 통합 검증

```bash
# 모든 테스트 실행
pytest backend/tests/marketpulse/ -v

# Pydantic schema → JSONField round-trip
python manage.py shell -c "
from marketpulse.schemas import NewsEntities
from marketpulse.models import MarketPulseNews
e = NewsEntities(tickers=['AAPL','MSFT'], topics=['Fed'])
print(e.model_dump())  # dict
parsed = NewsEntities(**e.model_dump())
assert parsed == e
print('round-trip OK')
"
```

---

## §6. DoD (Definition of Done)

### 6.1 머지 전 (CI 자동 검증 + 본인 확인)

- [ ] `python manage.py makemigrations marketpulse` 성공 (단일 0001_initial.py 생성)
- [ ] `python manage.py makemigrations marketpulse --check --dry-run` → "No changes detected" (재실행 시)
- [ ] `python manage.py migrate marketpulse` 성공
- [ ] `python manage.py migrate marketpulse zero` (reverse) 성공 → `migrate marketpulse` 재적용 성공
- [ ] `python manage.py check` 무경고
- [ ] `pytest backend/tests/marketpulse/ -v` 모두 PASS (T1~T26)
- [ ] `models/__init__.py`에서 5개 모델 모두 import 가능 (`from marketpulse.models import *`)
- [ ] `schemas/__init__.py`에서 9개 Pydantic 클래스 모두 import 가능
- [ ] Django Admin (`/admin/`)에서 5개 모델 페이지 접근 가능 (search/filter 동작 확인)
- [ ] 모든 모델 `__str__()` 정의 + `Meta.ordering` 정의

### 6.2 머지 후 (운영자=본인) — PR 템플릿 고정 섹션

- [ ] DEV 환경 migration 적용
- [ ] 5개 테이블 모두 비어 있음 확인 (`Model.objects.count() == 0`)
- [ ] PR-B/C/D/E 위임 프롬프트 작성 시 본 PR이 정의한 모델·schema import 경로 명시
- [ ] **백필 command 불필요** (A1과의 결정적 차이 — 본 PR은 빈 테이블만, 데이터는 후속 PR이 적재)

### 6.3 PR 설명 필수 포함

- 본 PR의 5개 모델 명단 + 각 모델이 의존하는 후속 PR
- 동결 결정 인용: D5/D8/D9/4A/is_finalized
- "데이터 적재는 후속 PR(B/C/D/E)" 명시

---

## §7. 금지 사항

| #   | 금지 행위                                                                  | 사유                                                                             |
| --- | -------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| F1  | migration 안에서 외부 API 호출                                             | A1과 동일 — 머지 후 새벽 장애 위험                                               |
| F2  | `RunPython.noop` 사용                                                      | reverse_code 정확 작성 강제                                                      |
| F3  | 단일 `models.py`에 5개 모델 통합                                           | A2-A.Ⅱ 결정 위반. 도메인별 4파일 강제                                            |
| F4  | 모델 파일에 Pydantic schema inline 정의                                    | A2-B.Ⅱ 결정 위반. `schemas/<domain>.py` 별도 파일                                |
| F5  | `NewsViewLog.user` FK on_delete를 CASCADE 외로 변경                        | A2-C.Ⅰ 결정 위반                                                                 |
| F6  | `paired_news` FK on_delete를 SET_NULL 외로 변경                            | D8 동결 위반                                                                     |
| F7  | `from marketpulse.models import MarketPulseNews` (migration 안)            | historical model 미사용. `apps.get_model("marketpulse", "MarketPulseNews")` 강제 |
| F8  | 본 PR에서 데이터 row INSERT (RunPython으로)                                | 본 PR은 스키마만. 데이터는 후속 PR(B/C/D/E)이 책임                               |
| F9  | `BreadthSnapshot`, `SectorFlowSnapshot`, `ConcentrationSnapshot` 모델 추가 | PR-A3 영역                                                                       |
| F10 | INSTALLED_APPS 외 settings.py 다른 부분 변경                               | PR 범위 외                                                                       |
| F11 | API view, serializer, URL 라우팅 작성                                      | PR-I 영역                                                                        |
| F12 | Celery task, scheduler 등록                                                | PR-B/C/D/E 영역                                                                  |
| F13 | `is_finalized` 컬럼을 BreadthSnapshot 등에 추가 (PR-A3 모델)               | PR-A3 영역                                                                       |
| F14 | RegimeSnapshot에 `is_finalized` 누락                                       | 동결 §2.5 위반                                                                   |
| F15 | 모델 prefix 변경 (예: `MPRegimeSnapshot`)                                  | 4A 동결 위반 — 스냅샷류는 prefix 없음                                            |
| F16 | `verbose_name`을 `MarketPulseConfig` 외로 설정                             | 본 PR 범위 외                                                                    |
| F17 | Pydantic v1 문법 사용 (`@validator`)                                       | v2 강제 (`@field_validator`, `model_dump()`)                                     |

---

## 참고: 본 위임 프롬프트의 결정 근거

| 결정                                | 선택                                                  | 위임 프롬프트 반영 위치 |
| ----------------------------------- | ----------------------------------------------------- | ----------------------- |
| **A2-A.Ⅱ** models 도메인 분리       | §1.4 디렉토리 구조, §3.2~3.5 4개 파일, §3.6 re-export | §7 F3                   |
| **A2-B.Ⅱ** schemas 도메인 분리      | §3.7~3.10 4개 파일, §3.11 re-export                   | §7 F4                   |
| **A2-C.Ⅰ** NewsViewLog.user CASCADE | §3.2 `on_delete=models.CASCADE` 명시                  | §7 F5, §5.1 T5          |
| 동결 D5 영구/90일 TTL               | §3.2 `expires_at` nullable + 주석                     | —                       |
| 동결 D8 SET_NULL/PROTECT/CASCADE    | §3.3 paired_news SET_NULL, §3.2 user CASCADE          | §7 F6                   |
| 동결 D9 Pydantic                    | §3.7~3.10, §5.5 T21~T26                               | §7 F17                  |
| 동결 4A prefix                      | 전 모델 prefix 없음 (News/SignalLog만 도메인 명사)    | §7 F15                  |
| 동결 §2.5 is_finalized              | §3.4 RegimeSnapshot 컬럼 2개                          | §7 F14                  |
