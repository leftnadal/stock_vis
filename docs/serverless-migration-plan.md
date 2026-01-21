# Stock-Vis Market Movers 서버리스 마이그레이션 계획

## 의사결정 요약

**날짜**: 2025-12-31
**아키텍처**: 완전 서버리스 (DynamoDB + Step Functions + Lambda)
**데이터 소스**: FMP API 신규 도입
**목표**: 5개 지표 전체 구현

| 결정 항목 | 선택 |
|-----------|------|
| 데이터 저장소 | DynamoDB 신규 도입 |
| 처리 방식 | AWS Step Functions + Lambda |
| 데이터 소스 | FMP API 신규 도입 |
| MVP 범위 | 5개 지표 전체 |

---

## 전체 아키텍처 비전

### 3-Layer 서버리스 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│  SERVE LAYER (API Gateway + Lambda + DynamoDB + Redis)      │
│  목표: < 200ms 응답, 99.9% 가용성                            │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ (데이터 공급)
                              │
┌─────────────────────────────────────────────────────────────┐
│  FAST COMPUTE LAYER (Step Functions + Lambda)               │
│  목표: Daily Sync 완료 < 5분, 매일 07:30 KST 자동 실행      │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ (이벤트)
                              │
┌─────────────────────────────────────────────────────────────┐
│  DEEP LAYER (Neptune + Bedrock - Phase 7+)                  │
│  목표: Anomaly 종목만 처리, 비용 통제                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 0: AWS 인프라 기초 구축 (1주)

### 목표
- AWS 계정 구조 및 IAM 권한 설정
- 개발/프로덕션 환경 분리
- IaC(Infrastructure as Code) 도구 선택 및 초기 설정

### 구현 범위

#### 1. AWS 계정 및 리전 설정
- **리전**: `ap-northeast-2` (서울) - 한국 시장 데이터, 낮은 레이턴시
- **계정 구조**: 단일 계정, 환경별 태그로 분리 (환경: dev/prod)

#### 2. IAM 설정
```yaml
필요한 IAM 역할:
- LambdaExecutionRole:
    - DynamoDB: GetItem, PutItem, Query, UpdateItem
    - S3: GetObject, PutObject
    - CloudWatch Logs: CreateLogGroup, PutLogEvents
    - EventBridge: PutEvents

- StepFunctionsExecutionRole:
    - Lambda: InvokeFunction
    - CloudWatch: PutMetricData

- EventBridgeSchedulerRole:
    - StepFunctions: StartExecution
```

#### 3. IaC 도구 선택
**옵션 A: AWS CDK (Python)** ✅ 권장
- 장점: Python 기반, Django 개발자 친화적, Type Safety
- 단점: CloudFormation 기반이라 약간 느림

**옵션 B: Terraform**
- 장점: 멀티 클라우드, 성숙한 생태계
- 단점: Python 개발팀이 HCL 학습 필요

**결정**: AWS CDK (Python)
- 이유: 백엔드 팀이 Python 전문, AWS 네이티브, Construct 재사용성

#### 4. 초기 CDK 프로젝트 구조
```
infrastructure/
├── cdk.json
├── app.py                 # CDK 앱 진입점
├── requirements.txt       # CDK 의존성
└── stacks/
    ├── __init__.py
    ├── dynamodb_stack.py  # DynamoDB 테이블
    ├── lambda_stack.py    # Lambda 함수들
    ├── stepfunctions_stack.py
    ├── eventbridge_stack.py
    └── monitoring_stack.py
```

#### 5. 환경 변수 관리
- **개발 환경**: AWS Systems Manager Parameter Store
- **시크릿 관리**: AWS Secrets Manager
- **필요한 파라미터**:
  - `/stockvis/dev/fmp-api-key`
  - `/stockvis/prod/fmp-api-key`
  - `/stockvis/dev/redis-url` (Phase 4)

### 에이전트 작업 할당

#### @infra Agent
- [ ] AWS CLI 설치 및 자격 증명 구성
- [ ] CDK 프로젝트 초기화 (`cdk init app --language python`)
- [ ] IAM 역할 및 정책 정의 (CDK Stack)
- [ ] Parameter Store에 FMP API 키 등록
- [ ] `cdk bootstrap` 실행 (ap-northeast-2)
- [ ] GitHub Actions CI/CD 기본 워크플로우 작성

#### @qa Agent
- [ ] AWS 계정 접근 권한 검증
- [ ] CDK 배포 테스트 (`cdk synth`, `cdk deploy`)
- [ ] IAM 권한 최소 권한 원칙 검토

### 검증 기준
- [ ] CDK로 빈 스택 배포 성공
- [ ] Parameter Store에서 값 읽기 성공
- [ ] CloudFormation 콘솔에서 스택 확인

### 산출물
- `infrastructure/` 디렉토리 및 초기 CDK 코드
- IAM 역할 정의서
- 환경 변수 목록 문서

---

## Phase 1: Fast Path Core (2주)

### 목표
- DynamoDB 테이블 생성
- FMP API에서 Market Movers 데이터 수집
- RVOL + 장중 추세 강도 2개 지표 계산
- Lambda 함수로 지표 저장
- 프론트엔드에서 지표 표시

### 구현 범위

#### 1. DynamoDB 테이블 설계

**테이블: stockvis-market-movers-{env}**
```python
{
  "TableName": "stockvis-market-movers-dev",
  "BillingMode": "PAY_PER_REQUEST",  # On-demand
  "AttributeDefinitions": [
    {"AttributeName": "PK", "AttributeType": "S"},    # DATE#2025-01-01
    {"AttributeName": "SK", "AttributeType": "S"}     # TYPE#GAINERS#RANK#01
  ],
  "KeySchema": [
    {"AttributeName": "PK", "KeyType": "HASH"},
    {"AttributeName": "SK", "KeyType": "RANGE"}
  ],
  "TimeToLiveSpecification": {
    "Enabled": true,
    "AttributeName": "ttl"  # 30일 후 자동 삭제
  },
  "GlobalSecondaryIndexes": [
    {
      "IndexName": "GSI_Symbol",
      "KeySchema": [
        {"AttributeName": "symbol_pk", "KeyType": "HASH"},  # SYMBOL#NVDA
        {"AttributeName": "date_sk", "KeyType": "RANGE"}    # DATE#2025-01-01
      ],
      "Projection": {"ProjectionType": "ALL"}
    }
  ]
}
```

**Item 구조 (Phase 1)**
```json
{
  "PK": "DATE#2025-01-01",
  "SK": "TYPE#GAINERS#RANK#01",
  "symbol": "NVDA",
  "symbol_pk": "SYMBOL#NVDA",
  "date_sk": "DATE#2025-01-01",
  "company_name": "NVIDIA Corporation",
  "price": 495.32,
  "change_percent": 8.45,
  "change_amount": 38.56,
  "volume": 125000000,
  "market_cap": 1220000000000,

  // Phase 1 지표
  "rvol": 3.2,
  "rvol_display": "3.2x",
  "trend_strength": 0.85,
  "trend_display": "▲0.85",

  // Phase 2에서 추가될 필드
  "sector_alpha": null,
  "etf_sync_rate": null,
  "volatility_pct": null,

  // 메타데이터
  "data_quality": {
    "has_20d_volume": true,
    "has_ohlc": true
  },
  "updated_at": "2025-01-01T07:35:00+09:00",
  "ttl": 1738435200  // 30일 후 Unix timestamp
}
```

#### 2. FMP API 통합

**API 엔드포인트 (FMP)**
```python
FMP_ENDPOINTS = {
    "gainers": "https://financialmodelingprep.com/api/v3/stock_market/gainers",
    "losers": "https://financialmodelingprep.com/api/v3/stock_market/losers",
    "actives": "https://financialmodelingprep.com/api/v3/stock_market/actives",
    "quote": "https://financialmodelingprep.com/api/v3/quote/{symbol}",
    "ohlcv": "https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}"
}
```

**Rate Limit 관리**
- FMP 무료: 250 calls/day
- 전략: 배치 작업에서만 사용, 캐싱 최대화
- 하루 사용량:
  - Movers 3번 (gainers, losers, actives)
  - OHLCV 60번 (각 카테고리 20개 종목)
  - 여유분: ~187 calls

#### 3. Lambda 함수 구조

**함수 1: fetch_market_movers**
```python
# lambda/fetch_market_movers/handler.py
import boto3
import requests
from datetime import datetime, timezone, timedelta

def lambda_handler(event, context):
    """
    FMP API에서 Gainers/Losers/Actives 수집
    Output: S3에 JSON 저장
    """
    fmp_api_key = get_parameter('/stockvis/dev/fmp-api-key')
    s3 = boto3.client('s3')

    kst = timezone(timedelta(hours=9))
    date = datetime.now(kst).strftime('%Y-%m-%d')

    results = {}
    for mover_type in ['gainers', 'losers', 'actives']:
        url = f"{FMP_ENDPOINTS[mover_type]}?apikey={fmp_api_key}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        results[mover_type] = response.json()[:20]  # 상위 20개만

    # S3에 원본 데이터 저장
    s3.put_object(
        Bucket='stockvis-data-dev',
        Key=f'raw/{date}/movers.json',
        Body=json.dumps(results),
        ContentType='application/json'
    )

    return {
        'statusCode': 200,
        'date': date,
        'counts': {k: len(v) for k, v in results.items()}
    }
```

**함수 2: fetch_ohlcv_data**
```python
# lambda/fetch_ohlcv_data/handler.py
def lambda_handler(event, context):
    """
    각 종목의 20일 OHLCV 데이터 수집 (RVOL 계산용)
    Input: S3의 movers.json
    Output: S3에 Parquet 저장
    """
    date = event['date']
    s3 = boto3.client('s3')

    # movers.json 읽기
    movers_data = load_movers_from_s3(date)
    symbols = extract_symbols(movers_data)

    ohlcv_data = []
    for symbol in symbols:
        # FMP API 호출
        data = fetch_historical_ohlcv(symbol, days=20)
        ohlcv_data.extend(data)
        time.sleep(1)  # Rate limit 준수

    # Parquet로 변환 및 저장
    df = pd.DataFrame(ohlcv_data)
    save_to_s3_parquet(df, f'raw/{date}/ohlcv.parquet')

    return {'statusCode': 200, 'symbols_count': len(symbols)}
```

**함수 3: calculate_indicators_phase1**
```python
# lambda/calculate_indicators_phase1/handler.py
from decimal import Decimal

def lambda_handler(event, context):
    """
    Phase 1 지표 계산: RVOL, 장중 추세 강도
    Input: S3의 movers.json + ohlcv.parquet
    Output: DynamoDB에 저장
    """
    date = event['date']

    # 데이터 로드
    movers = load_movers_from_s3(date)
    ohlcv_df = load_ohlcv_from_s3(date)

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('stockvis-market-movers-dev')

    for mover_type in ['gainers', 'losers', 'actives']:
        for rank, item in enumerate(movers[mover_type], start=1):
            symbol = item['symbol']

            # 지표 계산
            rvol = calculate_rvol(symbol, item['volume'], ohlcv_df)
            trend_strength = calculate_trend_strength(
                item['open'], item['high'], item['low'], item['close']
            )

            # DynamoDB Item 생성
            ddb_item = {
                'PK': f'DATE#{date}',
                'SK': f'TYPE#{mover_type.upper()}#RANK#{rank:02d}',
                'symbol': symbol,
                'symbol_pk': f'SYMBOL#{symbol}',
                'date_sk': f'DATE#{date}',
                'company_name': item['name'],
                'price': Decimal(str(item['price'])),
                'change_percent': Decimal(str(item['changesPercentage'])),
                'change_amount': Decimal(str(item['change'])),
                'volume': item['volume'],
                'market_cap': item.get('marketCap', 0),
                'rvol': Decimal(str(rvol)),
                'rvol_display': f'{rvol:.1f}x',
                'trend_strength': Decimal(str(trend_strength)),
                'trend_display': format_trend_display(trend_strength),
                'data_quality': {
                    'has_20d_volume': check_20d_data(symbol, ohlcv_df),
                    'has_ohlc': all([item['open'], item['high'], item['low'], item['close']])
                },
                'updated_at': datetime.now(KST).isoformat(),
                'ttl': int((datetime.now() + timedelta(days=30)).timestamp())
            }

            table.put_item(Item=ddb_item)

    return {'statusCode': 200, 'items_saved': len(movers['gainers']) * 3}

def calculate_rvol(symbol, current_volume, ohlcv_df):
    """RVOL 계산: 당일 거래량 / 20일 평균"""
    hist = ohlcv_df[ohlcv_df['symbol'] == symbol].tail(20)
    if len(hist) < 20:
        return 1.0  # 데이터 부족 시 기본값
    avg_volume = hist['volume'].mean()
    if avg_volume == 0:
        return 1.0
    return current_volume / avg_volume

def calculate_trend_strength(open_price, high, low, close):
    """장중 추세 강도: (종가-시가) / (고가-저가)"""
    if high == low:  # 0으로 나누기 방지
        return 0.0
    return (close - open_price) / (high - low)

def format_trend_display(strength):
    """표시 형식: ▲0.85 or ▼-0.67"""
    if strength >= 0:
        return f'▲{strength:.2f}'
    else:
        return f'▼{strength:.2f}'
```

#### 4. Step Functions 상태 머신 (Phase 1 간소화 버전)

```yaml
# stepfunctions/daily_sync_phase1.asl.json
{
  "Comment": "Market Movers Daily Sync - Phase 1",
  "StartAt": "FetchMarketMovers",
  "States": {
    "FetchMarketMovers": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:ap-northeast-2:xxx:function:fetch_market_movers",
      "ResultPath": "$.movers_result",
      "Next": "FetchOHLCV",
      "Retry": [
        {
          "ErrorEquals": ["States.ALL"],
          "IntervalSeconds": 30,
          "MaxAttempts": 3,
          "BackoffRate": 2.0
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "ResultPath": "$.error",
          "Next": "NotifyFailure"
        }
      ]
    },
    "FetchOHLCV": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:ap-northeast-2:xxx:function:fetch_ohlcv_data",
      "ResultPath": "$.ohlcv_result",
      "Next": "CalculateIndicators",
      "Retry": [...],
      "Catch": [...]
    },
    "CalculateIndicators": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:ap-northeast-2:xxx:function:calculate_indicators_phase1",
      "ResultPath": "$.calc_result",
      "Next": "Success"
    },
    "Success": {
      "Type": "Succeed"
    },
    "NotifyFailure": {
      "Type": "Task",
      "Resource": "arn:aws:states:::sns:publish",
      "Parameters": {
        "TopicArn": "arn:aws:sns:ap-northeast-2:xxx:stockvis-alerts",
        "Subject": "Market Movers Daily Sync Failed",
        "Message.$": "$.error"
      },
      "End": true
    }
  }
}
```

#### 5. EventBridge Scheduler

```python
# CDK 코드
from aws_cdk import aws_scheduler as scheduler

daily_sync_schedule = scheduler.CfnSchedule(
    self, "DailySyncSchedule",
    name="stockvis-daily-sync",
    schedule_expression="cron(30 7 ? * MON-FRI *)",  # 평일 07:30 KST
    schedule_expression_timezone="Asia/Seoul",
    flexible_time_window={"mode": "OFF"},
    target={
        "arn": daily_sync_state_machine.state_machine_arn,
        "roleArn": scheduler_role.role_arn
    }
)
```

#### 6. Backend API (Django - 임시, Phase 4에서 API Gateway로 대체)

**Django View (임시 브리지)**
```python
# stocks/views_market_movers.py
import boto3
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.core.cache import cache

@api_view(['GET'])
def market_movers_api(request):
    """
    GET /api/v1/stocks/market-movers?type=gainers&date=2025-01-01
    """
    mover_type = request.GET.get('type', 'gainers').upper()
    date = request.GET.get('date', get_today_kst())

    # Redis 캐시 확인
    cache_key = f'market_movers:{date}:{mover_type}'
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)

    # DynamoDB 조회
    dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-2')
    table = dynamodb.Table('stockvis-market-movers-dev')

    response = table.query(
        KeyConditionExpression='PK = :pk AND begins_with(SK, :sk_prefix)',
        ExpressionAttributeValues={
            ':pk': f'DATE#{date}',
            ':sk_prefix': f'TYPE#{mover_type}#'
        },
        ScanIndexForward=True  # RANK 오름차순
    )

    items = response['Items']

    # Decimal → float 변환
    items = convert_decimals(items)

    # 캐시 저장 (5분)
    cache.set(cache_key, items, 300)

    return Response({
        'date': date,
        'type': mover_type.lower(),
        'count': len(items),
        'data': items,
        'updated_at': items[0]['updated_at'] if items else None
    })
```

#### 7. Frontend 컴포넌트

**Market Movers 카드 (Phase 1)**
```typescript
// frontend/components/market-pulse/MoverCard.tsx
interface MoverCardProps {
  symbol: string;
  companyName: string;
  price: number;
  changePercent: number;
  rvol: number;
  rvolDisplay: string;
  trendStrength: number;
  trendDisplay: string;
  dataQuality: {
    has_20d_volume: boolean;
    has_ohlc: boolean;
  };
}

export function MoverCard({
  symbol, companyName, price, changePercent,
  rvol, rvolDisplay, trendStrength, trendDisplay,
  dataQuality
}: MoverCardProps) {
  const rvolColor = rvol > 2.0 ? 'text-red-600' : rvol > 1.5 ? 'text-orange-500' : 'text-gray-500';
  const trendColor = trendStrength > 0.7 ? 'text-green-600' : trendStrength < -0.7 ? 'text-red-600' : 'text-gray-600';

  return (
    <div className="border rounded-lg p-4 hover:shadow-lg transition">
      {/* 기본 정보 */}
      <div className="flex justify-between items-start mb-3">
        <div>
          <h3 className="font-bold text-lg">{symbol}</h3>
          <p className="text-sm text-gray-600">{companyName}</p>
        </div>
        <div className="text-right">
          <p className="text-xl font-semibold">${price.toFixed(2)}</p>
          <p className={changePercent >= 0 ? 'text-green-600' : 'text-red-600'}>
            {changePercent >= 0 ? '+' : ''}{changePercent.toFixed(2)}%
          </p>
        </div>
      </div>

      {/* Phase 1 지표 */}
      <div className="grid grid-cols-2 gap-3 pt-3 border-t">
        {/* RVOL */}
        <div className="bg-gray-50 p-3 rounded">
          <div className="flex items-center gap-1 mb-1">
            <span className="text-xs text-gray-500">RVOL</span>
            <Tooltip content="평소 대비 거래량 배수. 2.0 이상이면 비정상적 관심도.">
              <InfoIcon className="w-3 h-3 text-gray-400" />
            </Tooltip>
          </div>
          <p className={`font-bold text-lg ${rvolColor}`}>{rvolDisplay}</p>
          {!dataQuality.has_20d_volume && (
            <p className="text-xs text-yellow-600">데이터 부분 누락</p>
          )}
        </div>

        {/* 장중 추세 강도 */}
        <div className="bg-gray-50 p-3 rounded">
          <div className="flex items-center gap-1 mb-1">
            <span className="text-xs text-gray-500">추세 강도</span>
            <Tooltip content="(종가-시가)/(고가-저가). ±0.7 이상이면 강한 방향성.">
              <InfoIcon className="w-3 h-3 text-gray-400" />
            </Tooltip>
          </div>
          <p className={`font-bold text-lg ${trendColor}`}>{trendDisplay}</p>
        </div>
      </div>
    </div>
  );
}
```

**Market Movers 페이지 통합**
```typescript
// frontend/app/market-pulse/page.tsx (기존 페이지에 추가)
'use client';

import { useMarketMovers } from '@/hooks/useMarketMovers';
import { MoverCard } from '@/components/market-pulse/MoverCard';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

export default function MarketPulsePage() {
  const { data: gainers, isLoading: gainersLoading } = useMarketMovers('gainers');
  const { data: losers, isLoading: losersLoading } = useMarketMovers('losers');
  const { data: actives, isLoading: activesLoading } = useMarketMovers('actives');

  return (
    <div className="container mx-auto py-8">
      <h1 className="text-3xl font-bold mb-6">Market Pulse</h1>

      {/* Market Movers 섹션 */}
      <section className="mb-8">
        <h2 className="text-2xl font-semibold mb-4">Market Movers</h2>
        <p className="text-sm text-gray-600 mb-4">
          마지막 업데이트: {gainers?.updated_at} KST
        </p>

        <Tabs defaultValue="gainers">
          <TabsList>
            <TabsTrigger value="gainers">상승 TOP 20</TabsTrigger>
            <TabsTrigger value="losers">하락 TOP 20</TabsTrigger>
            <TabsTrigger value="actives">거래량 TOP 20</TabsTrigger>
          </TabsList>

          <TabsContent value="gainers" className="mt-4">
            {gainersLoading ? (
              <div>Loading...</div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {gainers?.data.map((item: any) => (
                  <MoverCard key={item.symbol} {...item} />
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="losers" className="mt-4">
            {/* 동일 구조 */}
          </TabsContent>

          <TabsContent value="actives" className="mt-4">
            {/* 동일 구조 */}
          </TabsContent>
        </Tabs>
      </section>

      {/* 기존 Market Pulse 콘텐츠 (Fear & Greed, Interest Rates 등) */}
      {/* ... */}
    </div>
  );
}
```

**Custom Hook**
```typescript
// frontend/hooks/useMarketMovers.ts
import { useQuery } from '@tanstack/react-query';
import { marketService } from '@/services/marketService';

export function useMarketMovers(type: 'gainers' | 'losers' | 'actives', date?: string) {
  return useQuery({
    queryKey: ['marketMovers', type, date],
    queryFn: () => marketService.getMarketMovers(type, date),
    staleTime: 5 * 60 * 1000, // 5분
    refetchInterval: 5 * 60 * 1000, // 5분마다 자동 갱신
  });
}
```

**API Service**
```typescript
// frontend/services/marketService.ts
export const marketService = {
  async getMarketMovers(type: 'gainers' | 'losers' | 'actives', date?: string) {
    const params = new URLSearchParams({ type });
    if (date) params.append('date', date);

    const response = await fetch(`/api/v1/stocks/market-movers?${params}`);
    if (!response.ok) throw new Error('Failed to fetch market movers');
    return response.json();
  },
};
```

### 에이전트 작업 할당

#### @infra Agent
- [ ] CDK로 DynamoDB 테이블 생성 (`dynamodb_stack.py`)
- [ ] S3 버킷 생성 및 수명주기 정책 설정
- [ ] Lambda 함수 3개 배포 (fetch_movers, fetch_ohlcv, calculate_indicators)
- [ ] Step Functions 상태 머신 정의 및 배포
- [ ] EventBridge Scheduler 설정 (매일 07:30 KST)
- [ ] SNS Topic 생성 (알림용)
- [ ] CloudWatch Logs 그룹 생성

#### @backend Agent
- [ ] Lambda 함수 코드 작성 (Python 3.12)
  - [ ] `lambda/fetch_market_movers/handler.py`
  - [ ] `lambda/fetch_ohlcv_data/handler.py`
  - [ ] `lambda/calculate_indicators_phase1/handler.py`
  - [ ] `lambda/common/utils.py` (공통 유틸)
- [ ] FMP API 클라이언트 구현 (requests + 재시도 로직)
- [ ] RVOL, 장중 추세 강도 계산 함수 구현
- [ ] DynamoDB Item 구조 Pydantic 모델 정의
- [ ] Django API View 작성 (`stocks/views_market_movers.py`)
- [ ] Django URL 라우팅 추가

#### @frontend Agent
- [ ] `MoverCard.tsx` 컴포넌트 구현
- [ ] `useMarketMovers` 커스텀 훅 구현
- [ ] Market Pulse 페이지에 Tabs 통합
- [ ] Tooltip 컴포넌트 구현 (지표 설명용)
- [ ] 반응형 그리드 레이아웃 구현
- [ ] 로딩/에러 상태 처리

#### @investment-advisor Agent
- [ ] RVOL 임계값 정의 (>2.0 스파이크, >1.5 높음, 등)
- [ ] 장중 추세 강도 해석 가이드 작성
- [ ] 툴팁 문구 작성 (초보 투자자용)
- [ ] 데이터 품질 저하 시 사용자 안내 문구

#### @qa Agent
- [ ] Lambda 함수 단위 테스트 (pytest)
- [ ] 지표 계산 정확도 검증 (엣지케이스: 고가=저가, 거래량 0)
- [ ] Step Functions 수동 실행 테스트
- [ ] DynamoDB 쿼리 성능 테스트 (20개 아이템 조회 < 100ms)
- [ ] API 응답 시간 측정 (Django → DynamoDB)
- [ ] 프론트엔드 UI/UX 테스트 (모바일 반응형)

### 검증 기준
- [ ] Step Functions가 매일 07:30에 자동 실행되고 성공
- [ ] DynamoDB에 60개 아이템 저장 (Gainers 20 + Losers 20 + Actives 20)
- [ ] Django API에서 데이터 조회 가능 (< 200ms)
- [ ] 프론트엔드에서 3개 탭 모두 정상 표시
- [ ] RVOL과 추세 강도 값이 수학적으로 정확함
- [ ] CloudWatch Logs에서 에러 없음

### 예상 기간
**2주** (10 영업일)

### 산출물
- DynamoDB 테이블 (stockvis-market-movers-dev)
- Lambda 함수 3개 + Step Functions 상태 머신
- Django API 엔드포인트
- 프론트엔드 컴포넌트 (MoverCard, 페이지 통합)
- 단위 테스트 및 통합 테스트

---

## Phase 2: 지표 확장 - 5개 지표 전체 (2주)

### 목표
- 섹터/ETF 매핑 테이블 구축
- 섹터 대비 초과수익, ETF 동행률 추가
- 60일 히스토리 데이터 수집 → 변동성 백분위 계산
- 모든 지표가 DynamoDB Item에 포함

### 구현 범위

#### 1. 섹터/ETF 매핑 테이블 (DynamoDB)

**테이블: stockvis-sector-etf-mapping**
```python
# Item 예시 1: 섹터별 ETF 목록
{
  "PK": "SECTOR#Technology",
  "SK": "ETF#XLK",
  "etf_name": "Technology Select Sector SPDR Fund",
  "is_primary": true,
  "expense_ratio": 0.0010
}

# Item 예시 2: 종목의 섹터 정보
{
  "PK": "SYMBOL#NVDA",
  "SK": "SECTOR#Technology",
  "gics_code": "45301010",
  "gics_sector": "Information Technology",
  "gics_industry": "Semiconductors"
}
```

**초기 데이터 로딩 Lambda**
```python
# lambda/load_sector_mapping/handler.py
def lambda_handler(event, context):
    """
    GICS 11개 섹터 + Primary ETF 매핑 초기화
    """
    SECTOR_ETF_MAP = {
        "Technology": ["XLK", "QQQ"],
        "Healthcare": ["XLV", "IBB"],
        "Financials": ["XLF", "KBE"],
        "Consumer Discretionary": ["XLY"],
        "Communication Services": ["XLC"],
        "Industrials": ["XLI"],
        "Consumer Staples": ["XLP"],
        "Energy": ["XLE"],
        "Utilities": ["XLU"],
        "Real Estate": ["XLRE"],
        "Materials": ["XLB"]
    }

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('stockvis-sector-etf-mapping')

    for sector, etfs in SECTOR_ETF_MAP.items():
        for idx, etf in enumerate(etfs):
            table.put_item(Item={
                'PK': f'SECTOR#{sector}',
                'SK': f'ETF#{etf}',
                'etf_name': etf,
                'is_primary': idx == 0
            })

    return {'statusCode': 200}
```

**종목 섹터 정보 수집 Lambda**
```python
# lambda/enrich_sector_info/handler.py
def lambda_handler(event, context):
    """
    Market Movers 종목들의 섹터 정보를 FMP API로 수집
    """
    date = event['date']
    movers = load_movers_from_s3(date)
    symbols = extract_symbols(movers)

    fmp_api_key = get_parameter('/stockvis/dev/fmp-api-key')
    mapping_table = boto3.resource('dynamodb').Table('stockvis-sector-etf-mapping')

    for symbol in symbols:
        # FMP Company Profile API
        url = f"https://financialmodelingprep.com/api/v3/profile/{symbol}?apikey={fmp_api_key}"
        response = requests.get(url).json()[0]

        sector = response.get('sector', 'Unknown')
        industry = response.get('industry', 'Unknown')

        mapping_table.put_item(Item={
            'PK': f'SYMBOL#{symbol}',
            'SK': f'SECTOR#{sector}',
            'gics_sector': sector,
            'gics_industry': industry
        })

        time.sleep(1)  # Rate limit

    return {'statusCode': 200}
```

#### 2. 변동성 백분위 계산을 위한 60일 히스토리

**Weekend Batch Lambda (Fargate 대신 Lambda로 시작)**
```python
# lambda/fetch_60d_history/handler.py
def lambda_handler(event, context):
    """
    주말 배치: 60일 히스토리 데이터 수집
    최근 거래일 기준 60일 OHLCV 데이터 수집
    """
    # S&P 500 전체 종목 또는 최근 Movers 종목 대상
    symbols = get_sp500_symbols()  # 또는 최근 30일 Movers 종목

    all_data = []
    for symbol in symbols:
        try:
            data = fetch_historical_ohlcv(symbol, days=60)
            all_data.extend(data)
        except Exception as e:
            logger.error(f"Failed to fetch {symbol}: {e}")
            continue
        time.sleep(1)

    # Parquet로 저장
    df = pd.DataFrame(all_data)
    save_to_s3_parquet(df, 'history/60d_ohlcv.parquet')

    return {'statusCode': 200, 'symbols_count': len(symbols)}
```

**변동성 백분위 계산**
```python
# lambda/calculate_volatility_baseline/handler.py
def lambda_handler(event, context):
    """
    60일 히스토리에서 종목별 변동성 백분위 기준 데이터 생성
    """
    df = load_parquet_from_s3('history/60d_ohlcv.parquet')

    volatility_table = boto3.resource('dynamodb').Table('stockvis-volatility-baseline')

    for symbol in df['symbol'].unique():
        symbol_data = df[df['symbol'] == symbol].tail(60)

        # 일중 변동폭 계산
        symbol_data['intraday_range'] = (symbol_data['high'] - symbol_data['low']) / symbol_data['low'] * 100

        # 백분위 계산
        percentiles = {
            'p5': symbol_data['intraday_range'].quantile(0.05),
            'p20': symbol_data['intraday_range'].quantile(0.20),
            'p50': symbol_data['intraday_range'].quantile(0.50),
            'p80': symbol_data['intraday_range'].quantile(0.80),
            'p95': symbol_data['intraday_range'].quantile(0.95),
        }

        volatility_table.put_item(Item={
            'PK': f'SYMBOL#{symbol}',
            'SK': 'BASELINE#60D',
            'percentiles': percentiles,
            'updated_at': datetime.now(KST).isoformat()
        })

    return {'statusCode': 200}
```

#### 3. 지표 계산 확장 (Lambda 업데이트)

**calculate_indicators_phase2.py**
```python
def lambda_handler(event, context):
    """
    Phase 2: 5개 지표 전체 계산
    """
    date = event['date']

    # 데이터 로드
    movers = load_movers_from_s3(date)
    ohlcv_20d = load_ohlcv_from_s3(date)
    history_60d = load_parquet_from_s3('history/60d_ohlcv.parquet')

    dynamodb = boto3.resource('dynamodb')
    movers_table = dynamodb.Table('stockvis-market-movers-dev')
    mapping_table = dynamodb.Table('stockvis-sector-etf-mapping')
    volatility_table = dynamodb.Table('stockvis-volatility-baseline')

    # 당일 ETF 가격도 수집 (섹터 대비 초과수익 계산용)
    etf_prices = fetch_etf_prices_for_date(date)

    for mover_type in ['gainers', 'losers', 'actives']:
        for rank, item in enumerate(movers[mover_type], start=1):
            symbol = item['symbol']

            # Phase 1 지표
            rvol = calculate_rvol(symbol, item['volume'], ohlcv_20d)
            trend_strength = calculate_trend_strength(
                item['open'], item['high'], item['low'], item['close']
            )

            # Phase 2 지표
            sector_alpha, sector_etf = calculate_sector_alpha(
                symbol, item['changesPercentage'], mapping_table, etf_prices
            )
            etf_sync_rate, synced_etfs = calculate_etf_sync_rate(
                symbol, item['changesPercentage'] > 0, mapping_table, etf_prices
            )
            volatility_pct = calculate_volatility_percentile(
                symbol, item['high'], item['low'], item['close'], volatility_table
            )

            # DynamoDB Item (Phase 2 완전체)
            ddb_item = {
                'PK': f'DATE#{date}',
                'SK': f'TYPE#{mover_type.upper()}#RANK#{rank:02d}',
                'symbol': symbol,
                # ... 기본 정보 ...

                # Phase 1 지표
                'rvol': Decimal(str(rvol)),
                'rvol_display': f'{rvol:.1f}x',
                'trend_strength': Decimal(str(trend_strength)),
                'trend_display': format_trend_display(trend_strength),

                # Phase 2 지표
                'sector_alpha': Decimal(str(sector_alpha)) if sector_alpha else None,
                'sector_alpha_display': f'{sector_alpha:+.1f}%p vs {sector_etf}' if sector_alpha else 'N/A',
                'etf_sync_rate': Decimal(str(etf_sync_rate)) if etf_sync_rate else None,
                'etf_sync_display': format_etf_sync(synced_etfs),
                'volatility_pct': int(volatility_pct) if volatility_pct else None,
                'volatility_display': format_volatility_display(volatility_pct),

                # 데이터 품질
                'data_quality': {
                    'has_20d_volume': check_20d_data(symbol, ohlcv_20d),
                    'has_60d_history': check_60d_data(symbol, history_60d),
                    'has_sector_mapping': sector_alpha is not None,
                    'has_ohlc': True
                },
                'updated_at': datetime.now(KST).isoformat(),
                'ttl': int((datetime.now() + timedelta(days=30)).timestamp())
            }

            movers_table.put_item(Item=ddb_item)

    return {'statusCode': 200}

def calculate_sector_alpha(symbol, stock_change_pct, mapping_table, etf_prices):
    """섹터 대비 초과수익"""
    # 종목의 섹터 조회
    response = mapping_table.get_item(
        Key={'PK': f'SYMBOL#{symbol}', 'SK': 'SECTOR#*'}
    )
    if 'Item' not in response:
        return None, None

    sector = response['Item']['gics_sector']

    # 섹터의 Primary ETF 조회
    response = mapping_table.query(
        KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
        FilterExpression='is_primary = :is_primary',
        ExpressionAttributeValues={
            ':pk': f'SECTOR#{sector}',
            ':sk': 'ETF#',
            ':is_primary': True
        }
    )
    if not response['Items']:
        return None, None

    primary_etf = response['Items'][0]['etf_name']
    etf_change = etf_prices.get(primary_etf, {}).get('changesPercentage', 0)

    alpha = stock_change_pct - etf_change
    return alpha, primary_etf

def calculate_etf_sync_rate(symbol, is_up, mapping_table, etf_prices):
    """ETF 동행률: 관련 ETF 중 같은 방향 비율"""
    # 종목 섹터 → 관련 ETF 목록
    sector_item = mapping_table.get_item(
        Key={'PK': f'SYMBOL#{symbol}', 'SK': 'SECTOR#*'}
    )
    if 'Item' not in sector_item:
        return None, []

    sector = sector_item['Item']['gics_sector']

    etf_items = mapping_table.query(
        KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
        ExpressionAttributeValues={
            ':pk': f'SECTOR#{sector}',
            ':sk': 'ETF#'
        }
    )

    etfs = [item['etf_name'] for item in etf_items['Items']]
    synced = []

    for etf in etfs:
        etf_change = etf_prices.get(etf, {}).get('changesPercentage', 0)
        if (is_up and etf_change > 0) or (not is_up and etf_change < 0):
            synced.append(etf)

    sync_rate = len(synced) / len(etfs) if etfs else None
    return sync_rate, synced

def calculate_volatility_percentile(symbol, high, low, close, volatility_table):
    """변동성 백분위: 60일 기준"""
    baseline = volatility_table.get_item(
        Key={'PK': f'SYMBOL#{symbol}', 'SK': 'BASELINE#60D'}
    )
    if 'Item' not in baseline:
        return None

    percentiles = baseline['Item']['percentiles']
    intraday_range = (high - low) / close * 100

    # 백분위 계산
    if intraday_range >= percentiles['p95']:
        return 95
    elif intraday_range >= percentiles['p80']:
        return 80
    elif intraday_range >= percentiles['p50']:
        return 50
    elif intraday_range >= percentiles['p20']:
        return 20
    else:
        return 5

def format_etf_sync(synced_etfs):
    """🟢🟢⚪ 형태"""
    total = 3  # 보통 섹터당 2-3개 ETF
    green = len(synced_etfs)
    return '🟢' * green + '⚪' * (total - green)

def format_volatility_display(pct):
    """상위 5% 형태"""
    if pct is None:
        return 'N/A'
    if pct >= 95:
        return f'상위 {100-pct}% 🔴'
    elif pct >= 80:
        return f'상위 {100-pct}%'
    else:
        return f'중간 {pct}%'
```

#### 4. Step Functions 업데이트 (Phase 2)

```yaml
# Phase 2 추가 단계
{
  "States": {
    # ... Phase 1 단계 ...
    "EnrichSectorInfo": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:enrich_sector_info",
      "Next": "FetchETFPrices"
    },
    "FetchETFPrices": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:fetch_etf_prices",
      "Next": "CalculateIndicatorsPhase2"
    },
    "CalculateIndicatorsPhase2": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:calculate_indicators_phase2",
      "Next": "Success"
    }
  }
}
```

#### 5. Weekend Batch Step Functions

```yaml
# stepfunctions/weekend_batch.asl.json
{
  "Comment": "Weekend Historical Data Refresh",
  "StartAt": "Fetch60DHistory",
  "States": {
    "Fetch60DHistory": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:fetch_60d_history",
      "TimeoutSeconds": 600,
      "Next": "CalculateVolatilityBaseline"
    },
    "CalculateVolatilityBaseline": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:calculate_volatility_baseline",
      "Next": "UpdateSectorMapping"
    },
    "UpdateSectorMapping": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:update_sector_mapping",
      "End": true
    }
  }
}
```

**EventBridge Scheduler (주말 배치)**
```python
weekend_batch_schedule = scheduler.CfnSchedule(
    self, "WeekendBatchSchedule",
    name="stockvis-weekend-batch",
    schedule_expression="cron(0 3 ? * SAT *)",  # 토요일 03:00 KST
    schedule_expression_timezone="Asia/Seoul",
    flexible_time_window={"mode": "OFF"},
    target={
        "arn": weekend_batch_state_machine.state_machine_arn,
        "roleArn": scheduler_role.role_arn
    }
)
```

#### 6. Frontend 업데이트 (5개 지표 전체)

**MoverCard 확장**
```typescript
// frontend/components/market-pulse/MoverCard.tsx (Phase 2)
export function MoverCard({
  // ... Phase 1 props ...
  sectorAlpha,
  sectorAlphaDisplay,
  etfSyncRate,
  etfSyncDisplay,
  volatilityPct,
  volatilityDisplay,
  dataQuality
}: MoverCardProps) {
  return (
    <div className="border rounded-lg p-4">
      {/* ... 기본 정보 ... */}

      {/* 5개 지표 그리드 */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 pt-3 border-t">
        {/* RVOL */}
        <IndicatorBadge
          label="RVOL"
          value={rvolDisplay}
          color={getRvolColor(rvol)}
          tooltip="평소 대비 거래량 배수. 2.0 이상이면 비정상적 관심도."
          hasData={dataQuality.has_20d_volume}
        />

        {/* 장중 추세 강도 */}
        <IndicatorBadge
          label="추세 강도"
          value={trendDisplay}
          color={getTrendColor(trendStrength)}
          tooltip="(종가-시가)/(고가-저가). ±0.7 이상이면 강한 방향성."
        />

        {/* 섹터 대비 초과수익 */}
        <IndicatorBadge
          label="섹터 Alpha"
          value={sectorAlphaDisplay}
          color={sectorAlpha > 0 ? 'text-blue-600' : 'text-gray-600'}
          tooltip="같은 섹터 ETF 대비 초과 수익률. 개별 이슈 파악 가능."
          hasData={dataQuality.has_sector_mapping}
        />

        {/* ETF 동행률 */}
        <IndicatorBadge
          label="ETF 동행률"
          value={etfSyncDisplay}
          tooltip="관련 ETF 중 같은 방향 비율. 섹터 전체 흐름 파악."
        />

        {/* 변동성 백분위 */}
        <IndicatorBadge
          label="변동성"
          value={volatilityDisplay}
          color={volatilityPct >= 95 ? 'text-red-600' : 'text-gray-600'}
          tooltip="60일 기준 일중 변동폭 백분위. 상위 5%는 극단적."
          hasData={dataQuality.has_60d_history}
        />
      </div>
    </div>
  );
}

// 재사용 가능한 지표 뱃지 컴포넌트
function IndicatorBadge({ label, value, color, tooltip, hasData = true }) {
  return (
    <div className="bg-gray-50 p-3 rounded">
      <div className="flex items-center gap-1 mb-1">
        <span className="text-xs text-gray-500">{label}</span>
        <Tooltip content={tooltip}>
          <InfoIcon className="w-3 h-3 text-gray-400" />
        </Tooltip>
      </div>
      <p className={`font-bold text-lg ${color}`}>{value}</p>
      {!hasData && (
        <p className="text-xs text-yellow-600">데이터 부분 누락</p>
      )}
    </div>
  );
}
```

### 에이전트 작업 할당

#### @infra Agent
- [ ] DynamoDB 테이블 2개 추가 생성
  - [ ] stockvis-sector-etf-mapping
  - [ ] stockvis-volatility-baseline
- [ ] Lambda 함수 5개 추가 배포
  - [ ] enrich_sector_info
  - [ ] fetch_etf_prices
  - [ ] fetch_60d_history
  - [ ] calculate_volatility_baseline
  - [ ] update_sector_mapping
- [ ] Step Functions 2개 상태 머신
  - [ ] Daily Sync Phase 2 (업데이트)
  - [ ] Weekend Batch (신규)
- [ ] EventBridge Scheduler (주말 배치)
- [ ] Lambda Layer: pandas 추가 (Parquet 처리용)

#### @backend Agent
- [ ] Lambda 함수 코드 작성
  - [ ] 섹터/ETF 매핑 초기화
  - [ ] 종목 섹터 정보 수집 (FMP Profile API)
  - [ ] 60일 히스토리 수집
  - [ ] 변동성 백분위 계산
  - [ ] Phase 2 지표 계산 (3개 추가)
- [ ] DynamoDB 쿼리 최적화 (GSI 활용)
- [ ] Parquet 파일 처리 로직 (pandas)

#### @frontend Agent
- [ ] MoverCard 컴포넌트 확장 (5개 지표 그리드)
- [ ] IndicatorBadge 재사용 컴포넌트 추출
- [ ] 반응형 그리드 (모바일: 2열, 데스크톱: 3열)
- [ ] 데이터 품질 경고 UI

#### @investment-advisor Agent
- [ ] 섹터 Alpha 해석 가이드
- [ ] ETF 동행률 임계값 정의
- [ ] 변동성 백분위 컬러 코딩 기준
- [ ] 지표 조합 해석 (예: RVOL↑ + 추세↑ + ETF괴리 → 개별 이슈)

#### @qa Agent
- [ ] 3개 신규 지표 계산 정확도 검증
- [ ] 섹터 매핑 데이터 무결성 테스트
- [ ] Weekend Batch 실행 테스트 (수동)
- [ ] 60일 히스토리 Parquet 파일 검증
- [ ] 프론트엔드 5개 지표 UI 테스트

### 검증 기준
- [ ] DynamoDB에 섹터 매핑 데이터 존재 (11개 섹터 × 평균 2개 ETF)
- [ ] 변동성 백분위 테이블에 최소 100개 종목 데이터
- [ ] 5개 지표가 모두 DynamoDB Item에 포함
- [ ] Weekend Batch가 토요일 03:00에 자동 실행
- [ ] 프론트엔드에서 5개 지표 모두 표시
- [ ] 데이터 품질 플래그에 따라 UI 경고 표시

### 예상 기간
**2주** (10 영업일)

### 산출물
- DynamoDB 테이블 2개
- Lambda 함수 5개 추가
- Step Functions 상태 머신 2개
- 확장된 MoverCard 컴포넌트

---

## Phase 3: 이벤트 아키텍처 (1주)

### 목표
- EventBridge를 통한 이벤트 기반 아키텍처 구축
- MarketMoversCalculated 이벤트 스키마 정의
- Anomaly 플래그 기반 라우팅 (Phase 4+ Deep Layer 준비)
- 이벤트 히스토리 저장

### 구현 범위

#### 1. 이벤트 스키마 정의

**AWS EventBridge Schema Registry**
```json
// schema: com.stockvis.MarketMoversCalculated.v1
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["source", "detail-type", "detail"],
  "properties": {
    "source": {
      "type": "string",
      "const": "stockvis.calc"
    },
    "detail-type": {
      "type": "string",
      "const": "MarketMoversCalculated"
    },
    "detail": {
      "type": "object",
      "required": ["metadata", "data"],
      "properties": {
        "metadata": {
          "type": "object",
          "properties": {
            "version": {"type": "string"},
            "timestamp_kst": {"type": "string", "format": "date-time"},
            "idempotency_key": {"type": "string"}
          }
        },
        "data": {
          "type": "object",
          "properties": {
            "date": {"type": "string"},
            "symbol": {"type": "string"},
            "mover_type": {"enum": ["gainers", "losers", "actives"]},
            "rank": {"type": "integer"},
            "indicators": {
              "type": "object",
              "properties": {
                "rvol": {"type": "number"},
                "trend_strength": {"type": "number"},
                "sector_alpha": {"type": "number"},
                "etf_sync_rate": {"type": "number"},
                "volatility_pct": {"type": "integer"}
              }
            },
            "anomaly_flags": {
              "type": "object",
              "properties": {
                "is_rvol_spike": {"type": "boolean"},
                "is_trend_strong": {"type": "boolean"},
                "is_volatility_extreme": {"type": "boolean"},
                "is_sector_divergent": {"type": "boolean"}
              }
            },
            "data_quality": {
              "type": "object"
            }
          }
        }
      }
    }
  }
}
```

#### 2. 이벤트 발행 Lambda

**Lambda: publish_movers_events**
```python
# lambda/publish_movers_events/handler.py
def lambda_handler(event, context):
    """
    계산 완료된 Market Movers를 EventBridge로 발행
    """
    date = event['date']
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('stockvis-market-movers-dev')
    eventbridge = boto3.client('events')

    # 당일 모든 Movers 조회
    all_movers = []
    for mover_type in ['GAINERS', 'LOSERS', 'ACTIVES']:
        response = table.query(
            KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
            ExpressionAttributeValues={
                ':pk': f'DATE#{date}',
                ':sk': f'TYPE#{mover_type}#'
            }
        )
        all_movers.extend(response['Items'])

    # 각 종목을 이벤트로 발행
    events = []
    for item in all_movers:
        # Anomaly 플래그 계산
        anomaly_flags = {
            'is_rvol_spike': float(item['rvol']) > 2.0,
            'is_trend_strong': abs(float(item['trend_strength'])) > 0.7,
            'is_volatility_extreme': item.get('volatility_pct', 50) >= 95,
            'is_sector_divergent': check_sector_divergence(item)
        }

        event_detail = {
            'metadata': {
                'version': '1.0',
                'timestamp_kst': datetime.now(KST).isoformat(),
                'idempotency_key': f"{date}_{item['symbol']}_{item['SK'].split('#')[1]}"
            },
            'data': {
                'date': date,
                'symbol': item['symbol'],
                'mover_type': item['SK'].split('#')[1].lower(),
                'rank': int(item['SK'].split('#')[-1]),
                'indicators': {
                    'rvol': float(item['rvol']),
                    'trend_strength': float(item['trend_strength']),
                    'sector_alpha': float(item.get('sector_alpha', 0)),
                    'etf_sync_rate': float(item.get('etf_sync_rate', 0)),
                    'volatility_pct': item.get('volatility_pct', 0)
                },
                'anomaly_flags': anomaly_flags,
                'data_quality': item['data_quality']
            }
        }

        events.append({
            'Source': 'stockvis.calc',
            'DetailType': 'MarketMoversCalculated',
            'Detail': json.dumps(event_detail),
            'EventBusName': 'stockvis-events'
        })

    # 배치로 이벤트 발행 (최대 10개씩)
    for i in range(0, len(events), 10):
        batch = events[i:i+10]
        eventbridge.put_events(Entries=batch)

    return {'statusCode': 200, 'events_published': len(events)}

def check_sector_divergence(item):
    """섹터와 반대 방향 여부"""
    stock_change = float(item['change_percent'])
    sector_alpha = float(item.get('sector_alpha', 0))

    # 섹터 Alpha가 크고(>5%p) 방향이 반대면 divergent
    if abs(sector_alpha) > 5:
        # 주가 상승인데 섹터는 하락 (alpha > 5)
        # 또는 주가 하락인데 섹터는 상승 (alpha < -5)
        return True
    return False
```

#### 3. EventBridge 라우팅 룰

**Rule: route-to-event-store**
```python
# CDK 코드
event_store_rule = events.Rule(
    self, "EventStoreRule",
    event_bus=custom_bus,
    event_pattern=events.EventPattern(
        source=["stockvis.calc"],
        detail_type=["MarketMoversCalculated"]
    ),
    targets=[
        targets.LambdaFunction(store_event_lambda),
        targets.CloudWatchLogGroup(log_group)
    ]
)
```

**Rule: route-to-deep-layer (Phase 4+용)**
```python
deep_layer_rule = events.Rule(
    self, "DeepLayerRule",
    event_bus=custom_bus,
    event_pattern=events.EventPattern(
        source=["stockvis.calc"],
        detail_type=["MarketMoversCalculated"],
        detail={
            "data": {
                "anomaly_flags": {
                    "is_rvol_spike": [True]  # RVOL 스파이크만
                }
            }
        }
    ),
    targets=[
        # Phase 4+: Step Functions (Insight Pipeline)
        # targets.SfnStateMachine(insight_pipeline)
    ],
    enabled=False  # Phase 3에서는 비활성화
)
```

#### 4. 이벤트 저장 Lambda (감사 로그)

**Lambda: store_event**
```python
# lambda/store_event/handler.py
def lambda_handler(event, context):
    """
    EventBridge 이벤트를 DynamoDB에 저장 (감사 로그)
    """
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('stockvis-event-store')

    # EventBridge 이벤트 구조
    event_id = event['id']
    source = event['source']
    detail_type = event['detail-type']
    detail = event['detail']

    table.put_item(Item={
        'PK': f"EVENT#{detail['data']['date']}",
        'SK': f"{detail['metadata']['timestamp_kst']}#{event_id}",
        'event_id': event_id,
        'source': source,
        'detail_type': detail_type,
        'symbol': detail['data']['symbol'],
        'mover_type': detail['data']['mover_type'],
        'anomaly_flags': detail['data']['anomaly_flags'],
        'detail': detail,
        'ttl': int((datetime.now() + timedelta(days=90)).timestamp())
    })

    return {'statusCode': 200}
```

**DynamoDB 테이블: stockvis-event-store**
```python
{
  "TableName": "stockvis-event-store",
  "BillingMode": "PAY_PER_REQUEST",
  "KeySchema": [
    {"AttributeName": "PK", "KeyType": "HASH"},   # EVENT#2025-01-01
    {"AttributeName": "SK", "KeyType": "RANGE"}   # 2025-01-01T07:40:00+09:00#uuid
  ],
  "TimeToLiveSpecification": {
    "Enabled": true,
    "AttributeName": "ttl"  # 90일 보관
  }
}
```

#### 5. Step Functions 업데이트 (이벤트 발행 추가)

```yaml
# Daily Sync에 이벤트 발행 단계 추가
{
  "States": {
    # ... Phase 2 단계 ...
    "CalculateIndicatorsPhase2": {
      "Next": "PublishEvents"  # 변경
    },
    "PublishEvents": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:publish_movers_events",
      "Next": "Success"
    }
  }
}
```

### 에이전트 작업 할당

#### @infra Agent
- [ ] EventBridge Custom Bus 생성 (stockvis-events)
- [ ] EventBridge Schema Registry에 스키마 등록
- [ ] Lambda: publish_movers_events 배포
- [ ] Lambda: store_event 배포
- [ ] DynamoDB: stockvis-event-store 생성
- [ ] EventBridge Rules 2개 생성 (event-store, deep-layer)
- [ ] CloudWatch Logs 그룹 (이벤트 로그용)

#### @backend Agent
- [ ] MarketMoversCalculated 이벤트 Pydantic 모델 정의
- [ ] publish_movers_events Lambda 코드 작성
- [ ] Anomaly 플래그 계산 로직 구현
- [ ] store_event Lambda 코드 작성
- [ ] Idempotency Key 생성 로직

#### @qa Agent
- [ ] 이벤트 스키마 검증 (JSON Schema 준수)
- [ ] Idempotency 테스트 (동일 이벤트 재발행 시 중복 처리 방지)
- [ ] EventBridge 라우팅 룰 테스트
- [ ] 이벤트 저장 확인 (DynamoDB 쿼리)
- [ ] Anomaly 플래그 정확도 검증

### 검증 기준
- [ ] Daily Sync 완료 후 60개 이벤트가 EventBridge로 발행
- [ ] 이벤트가 DynamoDB event-store에 저장
- [ ] CloudWatch Logs에 이벤트 로그 기록
- [ ] Anomaly 플래그가 올바르게 설정 (RVOL>2.0 종목만 true)
- [ ] Deep Layer 룰은 비활성화 상태

### 예상 기간
**1주** (5 영업일)

### 산출물
- EventBridge Custom Bus + Schema
- Lambda 함수 2개 (publish_events, store_event)
- DynamoDB 테이블 (event-store)
- 이벤트 스키마 문서

---

## Phase 4: Serve Layer 최적화 (1.5주)

### 목표
- API Gateway를 통한 서버리스 API 제공
- ElastiCache Redis 도입으로 캐싱 최적화
- Django API 제거 (완전 서버리스 전환)
- 응답 시간 < 200ms 달성

### 구현 범위

#### 1. API Gateway REST API

**API 구조**
```
GET /movers?type={gainers|losers|actives}&date={YYYY-MM-DD}
  → Lambda: api_handler_movers
  → Redis 캐시 확인 → DynamoDB 조회 → 응답

GET /movers/{symbol}/history?days={30}
  → Lambda: api_handler_mover_history
  → GSI_Symbol 쿼리
```

**Lambda: api_handler_movers**
```python
# lambda/api_handler_movers/handler.py
import json
import boto3
import redis
from decimal import Decimal

redis_client = redis.from_url(os.environ['REDIS_URL'])

def lambda_handler(event, context):
    """
    API Gateway → Redis → DynamoDB → 응답
    """
    # Query Parameters
    mover_type = event['queryStringParameters'].get('type', 'gainers').upper()
    date = event['queryStringParameters'].get('date', get_today_kst())

    # Redis 캐시 확인
    cache_key = f'movers:{date}:{mover_type}'
    cached = redis_client.get(cache_key)
    if cached:
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Cache-Control': 'max-age=300',
                'X-Cache': 'HIT'
            },
            'body': cached.decode('utf-8')
        }

    # DynamoDB 조회
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('stockvis-market-movers-dev')

    response = table.query(
        KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
        ExpressionAttributeValues={
            ':pk': f'DATE#{date}',
            ':sk': f'TYPE#{mover_type}#'
        },
        ScanIndexForward=True
    )

    items = response['Items']

    # Decimal → float 변환
    items = json.loads(json.dumps(items, default=decimal_default))

    result = {
        'date': date,
        'type': mover_type.lower(),
        'count': len(items),
        'data': items,
        'updated_at': items[0]['updated_at'] if items else None
    }

    result_json = json.dumps(result)

    # Redis 캐시 저장 (5분)
    redis_client.setex(cache_key, 300, result_json)

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Cache-Control': 'max-age=300',
            'X-Cache': 'MISS'
        },
        'body': result_json
    }

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError
```

**API Gateway 설정 (CDK)**
```python
# CDK
from aws_cdk import aws_apigateway as apigw

api = apigw.RestApi(
    self, "StockvisAPI",
    rest_api_name="stockvis-market-movers-api",
    description="Market Movers Serverless API",
    deploy_options=apigw.StageOptions(
        stage_name="v1",
        throttling_rate_limit=100,
        throttling_burst_limit=200,
        logging_level=apigw.MethodLoggingLevel.INFO,
        data_trace_enabled=True,
        metrics_enabled=True
    )
)

movers_resource = api.root.add_resource("movers")
movers_resource.add_method(
    "GET",
    apigw.LambdaIntegration(api_handler_movers_lambda),
    request_parameters={
        'method.request.querystring.type': False,
        'method.request.querystring.date': False
    }
)

# CORS 설정
movers_resource.add_cors_preflight(
    allow_origins=["https://yourdomain.com"],
    allow_methods=["GET", "OPTIONS"]
)
```

#### 2. ElastiCache Redis Serverless

**ElastiCache Serverless 설정 (CDK)**
```python
# Phase 4: ElastiCache Serverless 도입
from aws_cdk import aws_elasticache as elasticache

redis_serverless = elasticache.CfnServerlessCache(
    self, "RedisServerless",
    engine="redis",
    serverless_cache_name="stockvis-cache",
    description="Market Movers Cache",

    # 자동 스케일링 (ECU: ElastiCache Units)
    cache_usage_limits={
        "dataStorage": {
            "maximum": 10,  # GB
            "unit": "GB"
        },
        "ecpuPerSecond": {
            "maximum": 5000  # ECPU/sec
        }
    },

    # 보안
    security_group_ids=[security_group.security_group_id],
    subnet_ids=[subnet.subnet_id for subnet in vpc.private_subnets]
)
```

**Lambda VPC 연결**
```python
# Lambda가 ElastiCache에 접근하려면 VPC 연결 필요
api_handler_movers_lambda = _lambda.Function(
    self, "ApiHandlerMovers",
    runtime=_lambda.Runtime.PYTHON_3_12,
    handler="handler.lambda_handler",
    code=_lambda.Code.from_asset("lambda/api_handler_movers"),
    vpc=vpc,
    vpc_subnets={"subnet_type": ec2.SubnetType.PRIVATE_WITH_EGRESS},
    security_groups=[lambda_security_group],
    environment={
        'REDIS_URL': redis_serverless.attr_endpoint_address,
        'DYNAMODB_TABLE': 'stockvis-market-movers-dev'
    },
    timeout=Duration.seconds(10)
)
```

#### 3. 프론트엔드 API 엔드포인트 변경

**환경 변수 (.env)**
```bash
# 기존
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

# 변경
NEXT_PUBLIC_API_URL=https://abc123.execute-api.ap-northeast-2.amazonaws.com/v1
```

**API Service 업데이트**
```typescript
// frontend/services/marketService.ts
export const marketService = {
  async getMarketMovers(type: 'gainers' | 'losers' | 'actives', date?: string) {
    const params = new URLSearchParams({ type });
    if (date) params.append('date', date);

    // API Gateway 직접 호출
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/movers?${params}`,
      {
        headers: {
          'Content-Type': 'application/json'
        }
      }
    );

    if (!response.ok) throw new Error('Failed to fetch market movers');
    return response.json();
  },
};
```

#### 4. Custom Domain + CloudFront (선택)

**Route 53 + CloudFront (프로덕션용)**
```python
# CDK
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_certificatemanager as acm

certificate = acm.Certificate(
    self, "ApiCertificate",
    domain_name="api.stockvis.com",
    validation=acm.CertificateValidation.from_dns()
)

distribution = cloudfront.Distribution(
    self, "ApiDistribution",
    default_behavior=cloudfront.BehaviorOptions(
        origin=origins.HttpOrigin(
            f"{api.rest_api_id}.execute-api.ap-northeast-2.amazonaws.com"
        ),
        cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
        allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
        viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS
    ),
    certificate=certificate,
    domain_names=["api.stockvis.com"]
)
```

### 에이전트 작업 할당

#### @infra Agent
- [ ] API Gateway REST API 생성
- [ ] Lambda: api_handler_movers 배포
- [ ] ElastiCache Serverless 생성
- [ ] VPC + Security Group 설정 (Lambda ↔ Redis 연결)
- [ ] Lambda VPC 연결 구성
- [ ] CloudWatch Alarms (API 레이턴시, 캐시 히트율)
- [ ] (선택) CloudFront + Custom Domain 설정

#### @backend Agent
- [ ] api_handler_movers Lambda 코드 작성
- [ ] Redis 클라이언트 통합 (redis-py)
- [ ] Decimal → float 변환 유틸 함수
- [ ] 에러 처리 (DynamoDB 스로틀링, Redis 연결 실패)

#### @frontend Agent
- [ ] 환경 변수 업데이트 (API Gateway URL)
- [ ] API Service 엔드포인트 변경
- [ ] 에러 처리 강화 (API Gateway 에러 응답)
- [ ] Cache-Control 헤더 활용 (브라우저 캐싱)

#### @qa Agent
- [ ] API Gateway 응답 시간 측정 (<200ms 목표)
- [ ] Redis 캐시 히트율 확인 (>90% 목표)
- [ ] 부하 테스트 (100 req/s)
- [ ] Django API 제거 후 프론트엔드 통합 테스트
- [ ] VPC Lambda Cold Start 시간 측정

### 검증 기준
- [ ] API Gateway에서 Market Movers 조회 성공
- [ ] 캐시 히트 시 응답 시간 < 50ms
- [ ] 캐시 미스 시 응답 시간 < 200ms
- [ ] Redis 캐시 히트율 > 90%
- [ ] 프론트엔드에서 API Gateway 연동 정상
- [ ] Django API 완전 제거

### 예상 기간
**1.5주** (7-8 영업일)

### 산출물
- API Gateway REST API
- Lambda: api_handler_movers
- ElastiCache Serverless
- VPC 네트워크 구성
- (선택) CloudFront 배포

---

## Phase 5: Weekend Batch + 모니터링 (1주)

### 목표
- Weekend Batch 안정화
- CloudWatch 대시보드 구축
- 비용 모니터링 및 최적화
- 알림 시스템 강화

### 구현 범위

#### 1. Weekend Batch 최적화

**Lambda → Fargate Spot 전환 (대량 데이터 처리)**
```python
# CDK: Fargate Task Definition
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ecs_patterns as ecs_patterns

fargate_task = ecs.FargateTaskDefinition(
    self, "WeekendBatchTask",
    cpu=2048,  # 2 vCPU
    memory_limit_mib=4096  # 4 GB
)

container = fargate_task.add_container(
    "BatchContainer",
    image=ecs.ContainerImage.from_asset("./batch_container"),
    logging=ecs.LogDrivers.aws_logs(stream_prefix="weekend-batch"),
    environment={
        'FMP_API_KEY_PARAM': '/stockvis/prod/fmp-api-key',
        'S3_BUCKET': 'stockvis-data-prod'
    }
)

# Step Functions에서 Fargate Task 호출
weekend_batch_state_machine = sfn.StateMachine(
    self, "WeekendBatch",
    definition=sfn.Chain.start(
        tasks.EcsRunTask(
            self, "RunFargateTask",
            cluster=ecs_cluster,
            task_definition=fargate_task,
            launch_target=tasks.EcsFargateLaunchTarget(
                platform_version=ecs.FargatePlatformVersion.LATEST
            ),
            integration_pattern=sfn.IntegrationPattern.RUN_JOB,
            timeout=Duration.minutes(30)
        )
    )
)
```

**Batch Container (Docker)**
```dockerfile
# batch_container/Dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY batch_script.py .

CMD ["python", "batch_script.py"]
```

```python
# batch_container/batch_script.py
import boto3
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

def main():
    """
    60일 히스토리 데이터 수집 (S&P 500 전체)
    """
    s3 = boto3.client('s3')
    ssm = boto3.client('ssm')

    # S&P 500 종목 리스트 (500개)
    sp500_symbols = get_sp500_symbols()

    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)  # 여유분 포함

    all_data = []
    for i, symbol in enumerate(sp500_symbols):
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date)
            hist['symbol'] = symbol
            all_data.append(hist)

            if i % 50 == 0:
                print(f"Progress: {i}/{len(sp500_symbols)}")
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            continue

    # 병합 및 Parquet 저장
    df = pd.concat(all_data, ignore_index=True)
    df = df.tail(60 * len(sp500_symbols))  # 최근 60일만

    parquet_buffer = df.to_parquet(engine='pyarrow', compression='snappy')
    s3.put_object(
        Bucket='stockvis-data-prod',
        Key='history/60d_ohlcv.parquet',
        Body=parquet_buffer
    )

    print(f"Uploaded {len(df)} rows to S3")

if __name__ == "__main__":
    main()
```

#### 2. CloudWatch 대시보드

**주요 메트릭**
```python
# CDK
import aws_cdk.aws_cloudwatch as cloudwatch

dashboard = cloudwatch.Dashboard(
    self, "StockvisDashboard",
    dashboard_name="stockvis-market-movers"
)

# 1. Daily Sync 성공률
dashboard.add_widgets(
    cloudwatch.GraphWidget(
        title="Daily Sync Success Rate",
        left=[
            cloudwatch.Metric(
                namespace="AWS/States",
                metric_name="ExecutionsFailed",
                statistic="Sum",
                dimensions_map={"StateMachineArn": daily_sync_state_machine.state_machine_arn}
            ),
            cloudwatch.Metric(
                namespace="AWS/States",
                metric_name="ExecutionsSucceeded",
                statistic="Sum"
            )
        ]
    )
)

# 2. API 레이턴시
dashboard.add_widgets(
    cloudwatch.GraphWidget(
        title="API Latency (p50, p95, p99)",
        left=[
            cloudwatch.Metric(
                namespace="AWS/ApiGateway",
                metric_name="Latency",
                statistic="p50",
                dimensions_map={"ApiName": "stockvis-market-movers-api"}
            ),
            cloudwatch.Metric(
                namespace="AWS/ApiGateway",
                metric_name="Latency",
                statistic="p95"
            ),
            cloudwatch.Metric(
                namespace="AWS/ApiGateway",
                metric_name="Latency",
                statistic="p99"
            )
        ]
    )
)

# 3. Redis 캐시 히트율
dashboard.add_widgets(
    cloudwatch.GraphWidget(
        title="Redis Cache Hit Rate",
        left=[
            # Custom Metric (Lambda에서 발행)
            cloudwatch.Metric(
                namespace="Stockvis",
                metric_name="CacheHitRate",
                statistic="Average"
            )
        ]
    )
)

# 4. DynamoDB 스로틀링
dashboard.add_widgets(
    cloudwatch.GraphWidget(
        title="DynamoDB Throttles",
        left=[
            cloudwatch.Metric(
                namespace="AWS/DynamoDB",
                metric_name="UserErrors",
                statistic="Sum",
                dimensions_map={"TableName": "stockvis-market-movers-dev"}
            )
        ]
    )
)
```

**Custom Metric 발행 (Lambda)**
```python
# Lambda에서 캐시 히트율 발행
import boto3

cloudwatch = boto3.client('cloudwatch')

def publish_cache_metrics(cache_hit):
    """캐시 히트/미스 메트릭 발행"""
    cloudwatch.put_metric_data(
        Namespace='Stockvis',
        MetricData=[
            {
                'MetricName': 'CacheHitRate',
                'Value': 1.0 if cache_hit else 0.0,
                'Unit': 'None',
                'Timestamp': datetime.now()
            }
        ]
    )
```

#### 3. 비용 모니터링

**AWS Cost Explorer API**
```python
# lambda/cost_monitor/handler.py
def lambda_handler(event, context):
    """
    일별 서버리스 비용 추적
    """
    ce = boto3.client('ce')

    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

    response = ce.get_cost_and_usage(
        TimePeriod={'Start': start_date, 'End': end_date},
        Granularity='DAILY',
        Metrics=['UnblendedCost'],
        Filter={
            'Tags': {
                'Key': 'Project',
                'Values': ['stockvis']
            }
        },
        GroupBy=[
            {'Type': 'SERVICE', 'Key': 'SERVICE'}
        ]
    )

    # 주요 서비스 비용 분석
    costs = {}
    for result in response['ResultsByTime']:
        date = result['TimePeriod']['Start']
        for group in result['Groups']:
            service = group['Keys'][0]
            cost = float(group['Metrics']['UnblendedCost']['Amount'])

            if service not in costs:
                costs[service] = []
            costs[service].append({'date': date, 'cost': cost})

    # SNS 알림 (일 $10 초과 시)
    total_cost_today = sum(costs[s][-1]['cost'] for s in costs)
    if total_cost_today > 10.0:
        sns = boto3.client('sns')
        sns.publish(
            TopicArn='arn:aws:sns:...:stockvis-alerts',
            Subject='[ALERT] Daily Cost Exceeded $10',
            Message=f'Today cost: ${total_cost_today:.2f}\n\nBreakdown:\n' +
                    '\n'.join([f'{s}: ${costs[s][-1]["cost"]:.2f}' for s in costs])
        )

    return {'statusCode': 200, 'costs': costs}
```

**비용 최적화 포인트**
- Lambda: 메모리 최적화 (512MB → 256MB if possible)
- DynamoDB: On-Demand → Provisioned (예측 가능한 트래픽 시)
- S3: Lifecycle policy (90일 후 Glacier)
- ElastiCache: Serverless 자동 스케일 다운

#### 4. 알림 시스템

**SNS Topics**
```python
# CDK
critical_alerts = sns.Topic(
    self, "CriticalAlerts",
    display_name="Stockvis Critical Alerts",
    topic_name="stockvis-critical"
)

warning_alerts = sns.Topic(
    self, "WarningAlerts",
    display_name="Stockvis Warning Alerts",
    topic_name="stockvis-warnings"
)

# 이메일 구독
critical_alerts.add_subscription(
    subscriptions.EmailSubscription("admin@yourcompany.com")
)
```

**CloudWatch Alarms**
```python
# 1. Daily Sync 실패
daily_sync_alarm = cloudwatch.Alarm(
    self, "DailySyncFailureAlarm",
    metric=cloudwatch.Metric(
        namespace="AWS/States",
        metric_name="ExecutionsFailed",
        statistic="Sum",
        dimensions_map={"StateMachineArn": daily_sync_state_machine.state_machine_arn}
    ),
    threshold=1,
    evaluation_periods=1,
    comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
    alarm_description="Daily Sync failed"
)
daily_sync_alarm.add_alarm_action(actions.SnsAction(critical_alerts))

# 2. API 고장 (5xx 에러율 > 5%)
api_error_alarm = cloudwatch.Alarm(
    self, "ApiErrorAlarm",
    metric=cloudwatch.Metric(
        namespace="AWS/ApiGateway",
        metric_name="5XXError",
        statistic="Average"
    ),
    threshold=5,  # 5%
    evaluation_periods=2,
    comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD
)
api_error_alarm.add_alarm_action(actions.SnsAction(critical_alerts))

# 3. Lambda 타임아웃 급증
lambda_throttle_alarm = cloudwatch.Alarm(
    self, "LambdaThrottleAlarm",
    metric=cloudwatch.Metric(
        namespace="AWS/Lambda",
        metric_name="Throttles",
        statistic="Sum"
    ),
    threshold=10,
    evaluation_periods=1,
    comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD
)
lambda_throttle_alarm.add_alarm_action(actions.SnsAction(warning_alerts))
```

### 에이전트 작업 할당

#### @infra Agent
- [ ] Fargate Task Definition + ECS Cluster 생성
- [ ] Weekend Batch Docker 컨테이너 빌드
- [ ] CloudWatch Dashboard 구성
- [ ] SNS Topics + Email Subscription
- [ ] CloudWatch Alarms 5개 생성
- [ ] Cost Explorer 권한 설정
- [ ] Lambda: cost_monitor 배포 (일 1회 실행)

#### @backend Agent
- [ ] Weekend Batch Python 스크립트 작성
- [ ] S&P 500 종목 리스트 수집 로직
- [ ] Parquet 파일 생성 및 S3 업로드
- [ ] cost_monitor Lambda 코드 작성
- [ ] Custom Metric 발행 로직 추가 (캐시 히트율)

#### @qa Agent
- [ ] Weekend Batch 수동 실행 테스트 (Fargate)
- [ ] CloudWatch Dashboard 메트릭 검증
- [ ] Alarms 트리거 테스트 (수동으로 실패 유도)
- [ ] 비용 모니터링 Lambda 테스트
- [ ] SNS 알림 수신 확인

### 검증 기준
- [ ] Weekend Batch가 토요일 03:00에 자동 실행
- [ ] 60일 히스토리 Parquet 파일이 S3에 업로드
- [ ] CloudWatch Dashboard에서 모든 메트릭 표시
- [ ] Alarms가 임계값 초과 시 SNS 알림 발송
- [ ] 비용 모니터링 Lambda가 일 1회 실행

### 예상 기간
**1주** (5 영업일)

### 산출물
- Fargate Task Definition
- CloudWatch Dashboard
- SNS Topics + Alarms
- Lambda: cost_monitor

---

## Phase 6: 프로덕션 배포 (1주)

### 목표
- dev 환경에서 검증 완료 후 prod 환경 배포
- 프론트엔드 프로덕션 빌드 및 배포
- 최종 통합 테스트
- 런칭 준비

### 구현 범위

#### 1. 환경 분리 (dev / prod)

**CDK 앱 수정**
```python
# infrastructure/app.py
import os
from aws_cdk import App, Environment

app = App()

# dev 환경
StockvisStack(
    app, "StockvisMarketMoversDev",
    env=Environment(
        account=os.environ['CDK_DEFAULT_ACCOUNT'],
        region='ap-northeast-2'
    ),
    stage='dev'
)

# prod 환경
StockvisStack(
    app, "StockvisMarketMoversProd",
    env=Environment(
        account=os.environ['CDK_DEFAULT_ACCOUNT'],
        region='ap-northeast-2'
    ),
    stage='prod'
)

app.synth()
```

**리소스 이름에 stage 포함**
```python
# infrastructure/stacks/dynamodb_stack.py
class DynamoDBStack(Stack):
    def __init__(self, scope, id, stage, **kwargs):
        super().__init__(scope, id, **kwargs)

        movers_table = dynamodb.Table(
            self, "MoversTable",
            table_name=f"stockvis-market-movers-{stage}",  # dev or prod
            # ...
        )
```

#### 2. 프론트엔드 프로덕션 빌드

**환경 변수 (.env.production)**
```bash
NEXT_PUBLIC_API_URL=https://api.stockvis.com/v1
NEXT_PUBLIC_ENV=production
```

**Next.js 빌드 및 배포 (Vercel 추천)**
```bash
cd frontend
npm run build

# Vercel 배포
vercel --prod
```

**또는 자체 호스팅 (Docker + EC2/ECS)**
```dockerfile
# frontend/Dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

EXPOSE 3000
CMD ["npm", "start"]
```

#### 3. 데이터 마이그레이션 (dev → prod)

**섹터/ETF 매핑 데이터 복사**
```python
# scripts/migrate_mapping_data.py
import boto3

dynamodb = boto3.resource('dynamodb')
dev_table = dynamodb.Table('stockvis-sector-etf-mapping-dev')
prod_table = dynamodb.Table('stockvis-sector-etf-mapping-prod')

# dev 데이터 스캔
response = dev_table.scan()
items = response['Items']

# prod에 배치 쓰기
with prod_table.batch_writer() as batch:
    for item in items:
        batch.put_item(Item=item)

print(f"Migrated {len(items)} items")
```

#### 4. CI/CD 파이프라인 (GitHub Actions)

**.github/workflows/deploy-prod.yml**
```yaml
name: Deploy to Production

on:
  push:
    branches:
      - main
  workflow_dispatch:

jobs:
  deploy-infrastructure:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install CDK
        run: |
          npm install -g aws-cdk
          cd infrastructure
          pip install -r requirements.txt

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-northeast-2

      - name: Deploy CDK Stack (prod)
        run: |
          cd infrastructure
          cdk deploy StockvisMarketMoversProd --require-approval never

  deploy-frontend:
    runs-on: ubuntu-latest
    needs: deploy-infrastructure
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: '20'

      - name: Build Frontend
        run: |
          cd frontend
          npm ci
          npm run build

      - name: Deploy to Vercel
        env:
          VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}
        run: |
          cd frontend
          npx vercel --prod --token $VERCEL_TOKEN
```

#### 5. 최종 통합 테스트

**테스트 시나리오**
1. **Daily Sync 전체 플로우**
   - EventBridge Scheduler → Step Functions → Lambda → DynamoDB
   - 60개 종목 저장 확인
   - 이벤트 발행 확인

2. **API 엔드포인트**
   - GET /movers?type=gainers (캐시 미스)
   - GET /movers?type=gainers (캐시 히트)
   - 응답 시간 측정

3. **프론트엔드 통합**
   - Market Pulse 페이지 로딩
   - 3개 탭 전환
   - 지표 표시 확인

4. **에러 처리**
   - DynamoDB 빈 결과 (미래 날짜 조회)
   - API Gateway 타임아웃
   - Redis 연결 실패 시 fallback

#### 6. 런칭 체크리스트

- [ ] prod 환경 CDK 배포 완료
- [ ] DynamoDB 테이블 3개 생성 확인
- [ ] ElastiCache Redis 연결 테스트
- [ ] API Gateway 엔드포인트 테스트
- [ ] EventBridge Scheduler 설정 확인 (07:30, 03:00)
- [ ] CloudWatch Dashboard 메트릭 정상
- [ ] SNS 알림 테스트
- [ ] 프론트엔드 프로덕션 배포
- [ ] Custom Domain SSL 인증서 (선택)
- [ ] 사용자 문서화 (API 명세, 지표 해석 가이드)

### 에이전트 작업 할당

#### @infra Agent
- [ ] prod 환경 CDK 스택 배포
- [ ] 환경별 Parameter Store 값 설정
- [ ] GitHub Actions 워크플로우 작성
- [ ] CloudFormation 스택 검증
- [ ] (선택) Custom Domain + ACM 인증서

#### @backend Agent
- [ ] 데이터 마이그레이션 스크립트 작성
- [ ] prod 환경 테스트용 Lambda 트리거
- [ ] API 엔드포인트 smoke test

#### @frontend Agent
- [ ] 프로덕션 빌드 테스트
- [ ] Vercel 배포 설정
- [ ] 환경 변수 검증
- [ ] 프로덕션 환경 통합 테스트

#### @qa Agent
- [ ] 최종 통합 테스트 수행
- [ ] 성능 테스트 (레이턴시, 스루풋)
- [ ] 에러 시나리오 테스트
- [ ] 런칭 체크리스트 검증

### 검증 기준
- [ ] prod 환경 Daily Sync 1회 성공 실행
- [ ] API Gateway에서 실제 데이터 조회 가능
- [ ] 프론트엔드 프로덕션 환경에서 정상 작동
- [ ] 모든 CloudWatch Alarms 정상 상태
- [ ] 캐시 히트율 > 80%

### 예상 기간
**1주** (5 영업일)

### 산출물
- 프로덕션 환경 인프라
- CI/CD 파이프라인
- 프론트엔드 프로덕션 배포
- 런칭 문서

---

## Phase 7 (미래): Deep Layer - AI 인사이트

### 목표 (Phase 3 이후 확장)
- Neptune Serverless로 관계 탐색
- Bedrock/LLM으로 AI 인사이트 생성
- Anomaly 종목만 처리하여 비용 통제

### 트리거 조건
- 월 Anomaly 종목 평균 10개 이상
- 사용자 피드백으로 AI 인사이트 수요 확인
- 예산: Neptune NCU 1.0~2.0, Bedrock 월 $50

### 구현 예시 (간략)
```python
# lambda/deep_insight/handler.py
def lambda_handler(event, context):
    """
    EventBridge 이벤트 수신 → Neptune 쿼리 → LLM 호출 → DDB 업데이트
    """
    detail = event['detail']['data']
    symbol = detail['symbol']

    # Neptune: 관계 탐색 (예: 동일 섹터 종목 흐름)
    related_stocks = query_neptune_relationships(symbol)

    # Bedrock: Claude로 인사이트 생성
    prompt = f"""
    {symbol}이 오늘 {detail['indicators']['rvol']}배 거래량 스파이크를 기록했습니다.
    관련 종목: {related_stocks}
    원인을 분석하고 투자자를 위한 인사이트를 작성하세요.
    """

    bedrock = boto3.client('bedrock-runtime')
    response = bedrock.invoke_model(
        modelId='anthropic.claude-3-sonnet-20240229-v1:0',
        body=json.dumps({'prompt': prompt, 'max_tokens': 500})
    )

    ai_summary = response['completion']

    # DynamoDB 업데이트 (ai_summary 필드)
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('stockvis-market-movers-prod')
    table.update_item(
        Key={'PK': f"DATE#{detail['date']}", 'SK': f"TYPE#{detail['mover_type'].upper()}#RANK#{detail['rank']:02d}"},
        UpdateExpression='SET ai_summary = :summary',
        ExpressionAttributeValues={':summary': ai_summary}
    )

    return {'statusCode': 200}
```

---

## 전체 타임라인 요약

| Phase | 기간 | 주요 산출물 | 완료 기준 |
|-------|------|-----------|----------|
| Phase 0 | 1주 | AWS 계정, CDK, IAM | CDK 배포 성공 |
| Phase 1 | 2주 | DynamoDB, Lambda 3개, 2개 지표 | Daily Sync 자동 실행 |
| Phase 2 | 2주 | 5개 지표 전체, 섹터/ETF 매핑 | Weekend Batch 자동 실행 |
| Phase 3 | 1주 | EventBridge, 이벤트 스키마 | 이벤트 발행 성공 |
| Phase 4 | 1.5주 | API Gateway, Redis, Django 제거 | API 레이턴시 <200ms |
| Phase 5 | 1주 | Fargate Batch, 모니터링 | Dashboard 정상 작동 |
| Phase 6 | 1주 | 프로덕션 배포, CI/CD | 프로덕션 환경 런칭 |
| **총합** | **9.5주** | **완전 서버리스 아키텍처** | **프로덕션 서비스 시작** |

---

## 비용 예측 (월간, 프로덕션)

### AWS 리소스 비용

| 리소스 | 사양 | 월 비용 (USD) |
|--------|------|--------------|
| **DynamoDB (3개 테이블)** | On-Demand, ~100K reads/day | $10 |
| **Lambda** | 60 함수 호출/일, 평균 512MB, 3초 | $2 |
| **Step Functions** | 30 실행/월 (Daily + Weekend) | $1 |
| **EventBridge** | 60 이벤트/일 | $0.1 |
| **ElastiCache Serverless** | 평균 1 ECU, 5GB | $30 |
| **API Gateway** | 10K requests/day | $3.50 |
| **S3** | 100GB 저장, Lifecycle | $2.30 |
| **CloudWatch** | Logs, Metrics, Alarms | $5 |
| **Fargate (주말 배치)** | 2 vCPU, 4GB, 30분/주 | $2 |
| **데이터 전송** | CloudFront 제외 | $3 |
| **FMP API** | 무료 (250 calls/day) | $0 |
| **합계** | | **~$59/월** |

### 비용 최적화 기회
- ElastiCache: Serverless 자동 스케일 다운 활용 → ~$20
- DynamoDB: Provisioned 전환 시 → ~$5
- Lambda: 메모리 최적화 → ~$1

**최적화 후 예상 비용: ~$35/월**

---

## 리스크 및 대응 방안

| 리스크 | 영향도 | 대응 방안 |
|--------|--------|----------|
| FMP API 장애 | 높음 | yfinance fallback, 에러 알림 |
| Lambda Cold Start | 중간 | Provisioned Concurrency (필요 시) |
| DynamoDB 스로틀링 | 중간 | On-Demand → Provisioned, 재시도 로직 |
| ElastiCache 연결 실패 | 낮음 | Fallback to DynamoDB 직접 조회 |
| Weekend Batch 타임아웃 | 중간 | Fargate Spot 사용, 종목 분할 처리 |
| 비용 초과 | 중간 | Budget Alerts, 주간 비용 리포트 |

---

## 성공 지표 (KPI)

### 기술적 지표
- [ ] Daily Sync 성공률 > 99%
- [ ] API 응답 시간 p95 < 200ms
- [ ] Redis 캐시 히트율 > 90%
- [ ] Lambda 에러율 < 1%
- [ ] 월 비용 < $60

### 비즈니스 지표
- [ ] Market Pulse 페이지 DAU 증가
- [ ] 지표 표시 대비 클릭률 (CTR)
- [ ] 사용자 피드백 수집 (AI 인사이트 수요)

---

## 다음 단계 (현재 시점)

### 즉시 시작 가능한 작업
1. **@infra Agent**: Phase 0 AWS 계정 설정 및 CDK 초기화
2. **@investment-advisor Agent**: 지표 임계값 및 해석 가이드 작성
3. **@qa Agent**: 테스트 계획 수립

### 의사결정 필요
- [ ] FMP API 키 발급 (무료 플랜 등록)
- [ ] AWS 계정 및 예산 승인
- [ ] 프로젝트 GitHub 리포지토리 생성

---

이 계획서를 기반으로 **Phase 0**부터 시작하시겠습니까?
각 Phase별로 에이전트를 순차적으로 호출하며 진행할 수 있습니다.
