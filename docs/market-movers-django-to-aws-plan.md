# Market Movers: Django 로컬 개발 → AWS 전환 계획

**전략**: 로컬에서 검증 후 서버리스로 전환
**장점**: 리스크 최소화, 빠른 반복, 점진적 마이그레이션
**작성일**: 2026-01-06

---

## 전체 로드맵

```
Phase 1 (1.5주) → Phase 2 (1주) → Phase 3 (1주) → Phase 4 (1.5주)
Django 로컬 구현    로컬 검증      AWS 전환 준비    AWS 배포
```

**총 기간**: 5주 (기존 9.5주 대비 47% 단축)

---

## Phase 1: Django 로컬 구현 (1.5주)

### 목표
Market Movers 기능을 Django로 완전히 구현하여 로컬에서 작동 확인

### 프로젝트 구조

```
stock_vis/
├── serverless/              # 새 Django 앱
│   ├── models.py            # PostgreSQL 모델
│   ├── serializers.py       # DRF Serializers
│   ├── views.py             # REST API
│   ├── services/
│   │   ├── fmp_client.py    # FMP API 클라이언트
│   │   ├── indicators.py    # 5개 지표 계산
│   │   └── data_sync.py     # Daily Sync
│   ├── tasks.py             # Celery 작업
│   └── tests/
└── frontend/
    └── services/
        └── serverlessService.ts
```

### 1. Django 앱 생성

```bash
python manage.py startapp serverless
```

### 2. 모델 정의

```python
# serverless/models.py
class MarketMover(models.Model):
    """Market Movers 데이터"""
    date = models.DateField(db_index=True)
    mover_type = models.CharField(max_length=10, choices=[
        ('gainers', 'Gainers'),
        ('losers', 'Losers'),
        ('actives', 'Actives'),
    ])
    rank = models.IntegerField()
    symbol = models.CharField(max_length=10, db_index=True)
    company_name = models.CharField(max_length=255)

    # 가격 정보
    price = models.DecimalField(max_digits=12, decimal_places=2)
    change_percent = models.DecimalField(max_digits=8, decimal_places=2)
    volume = models.BigIntegerField()

    # OHLC
    open_price = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    high = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    low = models.DecimalField(max_digits=12, decimal_places=2, null=True)

    # 지표 (Phase 1: 2개)
    rvol = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    rvol_display = models.CharField(max_length=20, null=True)
    trend_strength = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    trend_display = models.CharField(max_length=20, null=True)

    # 지표 (Phase 2: 추가 3개)
    sector_alpha = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    etf_sync_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    volatility_pct = models.IntegerField(null=True)

    data_quality = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['date', 'mover_type', 'symbol']]
        ordering = ['date', 'mover_type', 'rank']
```

**마이그레이션**:
```bash
python manage.py makemigrations serverless
python manage.py migrate
```

### 3. FMP API 클라이언트

```python
# serverless/services/fmp_client.py
import requests
from django.conf import settings

class FMPClient:
    BASE_URL = "https://financialmodelingprep.com/api/v3"

    def __init__(self):
        self.api_key = settings.FMP_API_KEY

    def get_market_gainers(self):
        """상승 TOP 20"""
        url = f"{self.BASE_URL}/stock_market/gainers?apikey={self.api_key}"
        return requests.get(url, timeout=10).json()

    def get_market_losers(self):
        """하락 TOP 20"""
        url = f"{self.BASE_URL}/stock_market/losers?apikey={self.api_key}"
        return requests.get(url, timeout=10).json()

    def get_market_actives(self):
        """거래량 TOP 20"""
        url = f"{self.BASE_URL}/stock_market/actives?apikey={self.api_key}"
        return requests.get(url, timeout=10).json()

    def get_quote(self, symbol):
        """실시간 시세 (OHLC)"""
        url = f"{self.BASE_URL}/quote/{symbol}?apikey={self.api_key}"
        return requests.get(url, timeout=10).json()[0]

    def get_historical_ohlcv(self, symbol, days=20):
        """히스토리 OHLCV"""
        url = f"{self.BASE_URL}/historical-price-full/{symbol}?apikey={self.api_key}&timeseries={days}"
        return requests.get(url, timeout=10).json().get('historical', [])
```

**설정**:
```python
# config/settings.py
FMP_API_KEY = os.environ.get('FMP_API_KEY', '')
```

```.env
# .env
FMP_API_KEY=your_fmp_api_key_here
```

### 4. 지표 계산 로직

```python
# serverless/services/indicators.py
from decimal import Decimal
from typing import List, Optional

class IndicatorCalculator:
    """
    5개 지표 계산
    ⭐ AWS Lambda로 전환 시 이 클래스를 그대로 재사용
    """

    @staticmethod
    def calculate_rvol(current_volume: int, historical_volumes: List[int]) -> Optional[Decimal]:
        """RVOL: 당일 거래량 / 20일 평균"""
        if not historical_volumes or len(historical_volumes) < 10:
            return None

        avg_volume = sum(historical_volumes) / len(historical_volumes)
        if avg_volume == 0:
            return Decimal('1.0')

        rvol = current_volume / avg_volume
        return Decimal(str(round(rvol, 2)))

    @staticmethod
    def calculate_trend_strength(open_p, high, low, close) -> Optional[Decimal]:
        """장중 추세 강도: (종가-시가) / (고가-저가)"""
        if high == low:  # 0 나누기 방지
            return Decimal('0.0')

        strength = (close - open_p) / (high - low)
        return Decimal(str(round(strength, 2)))

    @staticmethod
    def format_trend_display(strength: Decimal) -> str:
        """▲0.85 또는 ▼-0.67"""
        if strength >= 0:
            return f'▲{strength:.2f}'
        else:
            return f'▼{strength:.2f}'
```

### 5. 데이터 동기화

```python
# serverless/services/data_sync.py
from django.db import transaction
from django.utils import timezone
import logging

from serverless.models import MarketMover
from serverless.services.fmp_client import FMPClient
from serverless.services.indicators import IndicatorCalculator

logger = logging.getLogger(__name__)

class MarketMoversSync:
    def __init__(self):
        self.fmp = FMPClient()
        self.calc = IndicatorCalculator()

    @transaction.atomic
    def sync_daily_movers(self, target_date=None):
        """Daily Sync: Gainers/Losers/Actives 수집"""
        target_date = target_date or timezone.now().date()
        logger.info(f"Syncing movers for {target_date}")

        results = {'gainers': 0, 'losers': 0, 'actives': 0}

        # 1. FMP API 호출
        movers_data = {
            'gainers': self.fmp.get_market_gainers(),
            'losers': self.fmp.get_market_losers(),
            'actives': self.fmp.get_market_actives(),
        }

        # 2. 각 종목 처리
        for mover_type, items in movers_data.items():
            for rank, item in enumerate(items[:20], start=1):
                self._process_item(target_date, mover_type, rank, item)
                results[mover_type] += 1

        logger.info(f"Sync completed: {results}")
        return results

    def _process_item(self, date, mover_type, rank, item):
        """개별 종목 처리"""
        symbol = item['symbol']

        # OHLC 데이터
        quote = self.fmp.get_quote(symbol)

        # 20일 히스토리
        historical = self.fmp.get_historical_ohlcv(symbol, days=20)

        # 지표 계산
        rvol = self._calc_rvol(item['volume'], historical)
        trend_strength = self.calc.calculate_trend_strength(
            quote.get('open', item['price']),
            quote.get('dayHigh', item['price']),
            quote.get('dayLow', item['price']),
            item['price']
        )

        # DB 저장
        MarketMover.objects.update_or_create(
            date=date,
            mover_type=mover_type,
            symbol=symbol,
            defaults={
                'rank': rank,
                'company_name': item['name'],
                'price': item['price'],
                'change_percent': item['changesPercentage'],
                'volume': item['volume'],
                'open_price': quote.get('open'),
                'high': quote.get('dayHigh'),
                'low': quote.get('dayLow'),
                'rvol': rvol,
                'rvol_display': f'{rvol:.1f}x' if rvol else 'N/A',
                'trend_strength': trend_strength,
                'trend_display': self.calc.format_trend_display(trend_strength) if trend_strength else 'N/A',
                'data_quality': {
                    'has_20d_volume': len(historical) >= 20,
                    'has_ohlc': all([quote.get('open'), quote.get('dayHigh')]),
                }
            }
        )

    def _calc_rvol(self, current_volume, historical):
        if not historical or len(historical) < 10:
            return None
        volumes = [d['volume'] for d in historical if d.get('volume')]
        return self.calc.calculate_rvol(current_volume, volumes)
```

### 6. Celery Task

```python
# serverless/tasks.py
from celery import shared_task
from serverless.services.data_sync import MarketMoversSync

@shared_task
def sync_daily_market_movers():
    """매일 07:30 실행"""
    sync = MarketMoversSync()
    return sync.sync_daily_movers()
```

**Celery Beat 설정**:
```python
# config/settings.py
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'sync-market-movers': {
        'task': 'serverless.tasks.sync_daily_market_movers',
        'schedule': crontab(hour=7, minute=30),  # 매일 07:30
    },
}
```

### 7. REST API

```python
# serverless/serializers.py
from rest_framework import serializers
from serverless.models import MarketMover

class MarketMoverSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketMover
        fields = '__all__'
```

```python
# serverless/views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.core.cache import cache
from django.utils import timezone

from serverless.models import MarketMover
from serverless.serializers import MarketMoverSerializer

@api_view(['GET'])
def market_movers_api(request):
    """
    GET /api/v1/serverless/movers?type=gainers&date=2025-01-01
    """
    mover_type = request.GET.get('type', 'gainers')
    date_str = request.GET.get('date', timezone.now().date().isoformat())

    # 캐시 확인
    cache_key = f'movers:{date_str}:{mover_type}'
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)

    # DB 조회
    movers = MarketMover.objects.filter(
        date=date_str,
        mover_type=mover_type
    ).order_by('rank')

    serializer = MarketMoverSerializer(movers, many=True)
    data = {
        'date': date_str,
        'type': mover_type,
        'count': len(serializer.data),
        'data': serializer.data
    }

    # 캐시 저장 (5분)
    cache.set(cache_key, data, 300)

    return Response(data)
```

```python
# serverless/urls.py
from django.urls import path
from serverless import views

urlpatterns = [
    path('movers', views.market_movers_api, name='market-movers'),
]
```

**프로젝트 URLs**:
```python
# config/urls.py
urlpatterns = [
    # ...
    path('api/v1/serverless/', include('serverless.urls')),
]
```

### 8. 프론트엔드 통합

```typescript
// frontend/services/serverlessService.ts
export const serverlessService = {
  async getMarketMovers(type: 'gainers' | 'losers' | 'actives', date?: string) {
    const params = new URLSearchParams({ type });
    if (date) params.append('date', date);

    const res = await fetch(`/api/v1/serverless/movers?${params}`);
    return res.json();
  }
};
```

```typescript
// frontend/hooks/useMarketMovers.ts
import { useQuery } from '@tanstack/react-query';
import { serverlessService } from '@/services/serverlessService';

export function useMarketMovers(type: 'gainers' | 'losers' | 'actives') {
  return useQuery({
    queryKey: ['marketMovers', type],
    queryFn: () => serverlessService.getMarketMovers(type),
    staleTime: 5 * 60 * 1000,
  });
}
```

```tsx
// frontend/app/market-pulse/page.tsx
import { useMarketMovers } from '@/hooks/useMarketMovers';

export default function MarketPulsePage() {
  const { data: gainers } = useMarketMovers('gainers');

  return (
    <div>
      <h1>Market Movers</h1>
      {gainers?.data.map(mover => (
        <div key={mover.symbol}>
          {mover.symbol}: {mover.rvol_display} RVOL, {mover.trend_display}
        </div>
      ))}
    </div>
  );
}
```

### 작업 할당

#### @backend
- [ ] Django 앱 생성
- [ ] 모델 정의 및 마이그레이션
- [ ] FMP API 클라이언트
- [ ] 지표 계산 로직
- [ ] 데이터 동기화
- [ ] Celery Task
- [ ] REST API

#### @frontend
- [ ] serverlessService.ts
- [ ] useMarketMovers Hook
- [ ] MoverCard 컴포넌트
- [ ] Market Pulse 페이지 통합

#### @qa
- [ ] 단위 테스트
- [ ] API 테스트
- [ ] 지표 계산 검증

### 검증 기준
- [ ] Celery Task 수동 실행 성공
- [ ] PostgreSQL에 60개 레코드 저장
- [ ] API 응답 < 500ms
- [ ] 프론트엔드 정상 표시

---

## Phase 2: 로컬 검증 및 최적화 (1주)

### 목표
- 단위 테스트 작성
- 5개 지표 전체 구현
- 성능 측정
- 사용자 피드백

### 단위 테스트

```python
# serverless/tests/test_indicators.py
import pytest
from decimal import Decimal
from serverless.services.indicators import IndicatorCalculator

def test_rvol_calculation():
    calc = IndicatorCalculator()

    # 정상 케이스
    rvol = calc.calculate_rvol(10000000, [5000000] * 20)
    assert rvol == Decimal('2.00')

    # 데이터 부족
    rvol = calc.calculate_rvol(10000000, [5000000] * 5)
    assert rvol is None

def test_trend_strength():
    calc = IndicatorCalculator()

    # 강한 상승
    strength = calc.calculate_trend_strength(100, 110, 100, 110)
    assert strength == Decimal('1.00')

    # 0 나누기 방지
    strength = calc.calculate_trend_strength(100, 100, 100, 100)
    assert strength == Decimal('0.00')
```

### 5개 지표 확장

Phase 1에서 2개 구현 → Phase 2에서 추가:
- 섹터 대비 초과수익
- ETF 동행률
- 변동성 백분위

(코드는 `indicators.py`에 메서드 추가)

### 검증 기준
- [ ] 단위 테스트 커버리지 > 80%
- [ ] 5개 지표 정확도 검증
- [ ] Daily Sync < 5분 (60종목)

---

## Phase 3: AWS 전환 준비 (1주)

### 목표
Django 코드를 Lambda로 변환할 수 있도록 준비

### Lambda 코드 구조

```
lambda/
├── common/
│   ├── indicators.py      # Django 코드 복사
│   ├── fmp_client.py      # Django 코드 복사
│   └── dynamodb_utils.py
├── fetch_movers/
│   └── handler.py
└── calculate_indicators/
    └── handler.py
```

**핵심**: `IndicatorCalculator`와 `FMPClient`는 Django 의존성 없으므로 그대로 재사용!

```python
# lambda/common/indicators.py
# serverless/services/indicators.py와 동일 코드

# lambda/common/fmp_client.py
# settings.FMP_API_KEY → os.environ['FMP_API_KEY']만 변경
```

### DynamoDB 스키마 매핑

Django → DynamoDB 변환 테이블 작성

| Django | DynamoDB |
|--------|----------|
| date + mover_type | PK: `DATE#2025-01-01` |
| rank | SK: `TYPE#GAINERS#RANK#01` |
| rvol | rvol: Number |

### AWS CDK

```python
# infrastructure/stacks/dynamodb_stack.py
from aws_cdk import aws_dynamodb as dynamodb

table = dynamodb.Table(
    self, "MoversTable",
    partition_key={"name": "PK", "type": dynamodb.AttributeType.STRING},
    sort_key={"name": "SK", "type": dynamodb.AttributeType.STRING},
    billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
)
```

### 검증 기준
- [ ] Lambda 함수 로컬 실행 (SAM)
- [ ] CDK synth 성공

---

## Phase 4: AWS 배포 및 스위칭 (1.5주)

### 목표
- AWS 인프라 배포
- Blue/Green 배포
- 프론트엔드 엔드포인트 전환

### AWS 배포

```bash
cd infrastructure
cdk bootstrap
cdk deploy
```

### 데이터 마이그레이션

```python
# scripts/migrate_to_dynamodb.py
from serverless.models import MarketMover
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('stockvis-market-movers')

# Django → DynamoDB
movers = MarketMover.objects.all()
with table.batch_writer() as batch:
    for m in movers:
        batch.put_item(Item={
            'PK': f'DATE#{m.date}',
            'SK': f'TYPE#{m.mover_type.upper()}#RANK#{m.rank:02d}',
            # ...
        })
```

### Blue/Green 배포

```typescript
// frontend/.env
NEXT_PUBLIC_API_TYPE=django  // or 'aws'
NEXT_PUBLIC_AWS_API_URL=https://xxx.execute-api.ap-northeast-2.amazonaws.com/v1
```

```typescript
// frontend/services/serverlessService.ts
const BASE_URL = process.env.NEXT_PUBLIC_API_TYPE === 'aws'
  ? process.env.NEXT_PUBLIC_AWS_API_URL
  : '/api/v1/serverless';
```

### 점진적 전환

1주차: AWS 배포, 데이터 동기화
2주차: 사용자 10% → AWS
3주차: 100% → AWS, Django API 제거

### 검증 기준
- [ ] AWS 정상 작동
- [ ] API Gateway < 200ms
- [ ] 최종 전환 후 1주일 모니터링

---

## 타임라인 요약

| Phase | 기간 | 주요 산출물 |
|-------|------|----------|
| Phase 1 | 1.5주 | Django 로컬 구현 |
| Phase 2 | 1주 | 검증 + 5개 지표 |
| Phase 3 | 1주 | Lambda 변환 준비 |
| Phase 4 | 1.5주 | AWS 배포 |
| **총합** | **5주** | **완전 전환** |

---

## 아키텍처 비교

### Django (Phase 1-2)

```
Frontend → Django API → PostgreSQL
              ↓
          Celery (Daily Sync)
              ↓
          FMP API
```

### AWS (Phase 4)

```
Frontend → API Gateway → Lambda → DynamoDB
                            ↓
                    EventBridge
                            ↓
                    Step Functions
```

---

## 다음 단계

### 즉시 시작

```bash
# 1. Django 앱 생성
python manage.py startapp serverless

# 2. FMP API 키 설정
echo "FMP_API_KEY=your_key" >> .env

# 3. 마이그레이션
python manage.py makemigrations serverless
python manage.py migrate
```

### 에이전트 호출

1. @backend: 모델 및 API 구현
2. @frontend: 컴포넌트 통합
3. @qa: 테스트 작성

---

**준비 완료!** Phase 1부터 시작하시겠습니까?
