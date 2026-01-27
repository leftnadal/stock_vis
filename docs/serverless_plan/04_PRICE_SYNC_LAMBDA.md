# 가격 데이터 동기화 Lambda 전환 계획

## 개요

주식 가격 데이터(일일/주간)를 자동으로 수집하고 DB에 저장하는 AWS Lambda 기반 시스템입니다.

---

## 수집 대상

### 1. 자동 수집 대상

| 카테고리 | 대상 | 수집 빈도 | 예상 종목 수 |
|----------|------|----------|-------------|
| **사용자 Watchlist** | `auto_price_sync = True` | 매일 | 사용자별 상이 |
| **사용자 Portfolio** | 보유 종목 | 매일 | 사용자별 상이 |
| **Market Movers** | 당일 급등/급락/거래량 | 매일 | 60개 |
| **인덱스 구성종목** | S&P 500, NASDAQ 100 | 매일 | ~600개 |
| **섹터 ETF** | 11개 섹터 ETF | 매일 | 11개 |

### 2. 온디맨드 수집

- 사용자가 Stock Detail 페이지 접근 시
- Screener 결과 종목
- 검색 결과 종목

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    EventBridge Scheduler                     │
│               cron(0 22 ? * MON-FRI *)                       │
│                   (EST 17:00 = 장 마감 후)                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  price-sync-orchestrator                     │
│                                                             │
│  1. 수집 대상 종목 조회                                       │
│  2. 배치 분할 (50개씩)                                       │
│  3. SQS 메시지 발행                                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        SQS Queue                             │
│                    price-sync-queue                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   price-sync-worker                          │
│                                                             │
│  1. FMP API에서 가격 데이터 조회                              │
│  2. 데이터 변환 및 검증                                       │
│  3. PostgreSQL Bulk Insert                                  │
│  4. 수집 상태 업데이트                                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     PostgreSQL                               │
│                                                             │
│  - stocks_dailyprice                                        │
│  - stocks_weeklyprice                                       │
│  - stocks_stock (last_price_sync_at)                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Lambda 함수 설계

### 1. Orchestrator Lambda

```python
# infra/lambda/price_sync_orchestrator/handler.py

import json
import boto3
from datetime import datetime
import psycopg2

sqs = boto3.client('sqs')
QUEUE_URL = os.environ['PRICE_SYNC_QUEUE_URL']
BATCH_SIZE = 50  # FMP Batch API 제한

def handler(event, context):
    """
    가격 동기화 오케스트레이터
    트리거: EventBridge (매일 22:00 UTC = 17:00 EST)
    """
    conn = get_db_connection()

    try:
        # 1. 수집 대상 종목 조회
        symbols = get_sync_target_symbols(conn)

        # 2. 배치 분할 및 SQS 발행
        batches_sent = 0
        for i in range(0, len(symbols), BATCH_SIZE):
            batch = symbols[i:i + BATCH_SIZE]

            message = {
                'symbols': batch,
                'sync_type': 'daily',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'batch_id': f"batch_{i // BATCH_SIZE}"
            }

            sqs.send_message(
                QueueUrl=QUEUE_URL,
                MessageBody=json.dumps(message)
            )
            batches_sent += 1

        return {
            'statusCode': 200,
            'body': json.dumps({
                'total_symbols': len(symbols),
                'batches_sent': batches_sent,
                'batch_size': BATCH_SIZE
            })
        }

    finally:
        conn.close()


def get_sync_target_symbols(conn) -> list:
    """수집 대상 종목 조회"""

    query = """
        -- 1. 사용자 Watchlist (auto_price_sync = True)
        SELECT DISTINCT s.symbol
        FROM users_watchlistitem wi
        JOIN stocks_stock s ON wi.stock_id = s.id
        WHERE wi.auto_price_sync = TRUE

        UNION

        -- 2. 사용자 Portfolio
        SELECT DISTINCT s.symbol
        FROM users_portfolioitem pi
        JOIN stocks_stock s ON pi.stock_id = s.id

        UNION

        -- 3. 오늘의 Market Movers
        SELECT DISTINCT symbol
        FROM serverless_marketmover
        WHERE date = CURRENT_DATE

        UNION

        -- 4. 인덱스 구성종목 (미리 등록된 목록)
        SELECT symbol
        FROM stocks_indexconstituent
        WHERE index_symbol IN ('SPY', 'QQQ')

        UNION

        -- 5. 섹터 ETF
        SELECT symbol
        FROM stocks_sectoretf
        WHERE is_active = TRUE
    """

    with conn.cursor() as cur:
        cur.execute(query)
        return [row[0] for row in cur.fetchall()]
```

### 2. Worker Lambda

```python
# infra/lambda/price_sync_worker/handler.py

import json
import os
import httpx
from datetime import datetime, timedelta
from decimal import Decimal
import psycopg2
from psycopg2.extras import execute_values

FMP_API_KEY = os.environ['FMP_API_KEY']

def handler(event, context):
    """
    가격 데이터 수집 Worker
    트리거: SQS (price-sync-queue)
    """
    conn = get_db_connection()
    results = []

    try:
        for record in event['Records']:
            message = json.loads(record['body'])
            symbols = message['symbols']
            sync_type = message.get('sync_type', 'daily')
            batch_id = message.get('batch_id', '')

            try:
                # 1. FMP Batch API 호출
                price_data = fetch_batch_prices(symbols)

                # 2. 히스토리 데이터 조회 (최근 30일)
                history_data = fetch_batch_history(symbols, days=30)

                # 3. DB Bulk Insert
                saved_daily = bulk_insert_daily_prices(conn, price_data, history_data)

                # 4. 수집 상태 업데이트
                update_sync_status(conn, symbols)

                results.append({
                    'batch_id': batch_id,
                    'status': 'success',
                    'symbols_count': len(symbols),
                    'prices_saved': saved_daily
                })

            except Exception as e:
                results.append({
                    'batch_id': batch_id,
                    'status': 'error',
                    'error': str(e),
                    'symbols': symbols
                })

        conn.commit()
        return {'statusCode': 200, 'results': results}

    finally:
        conn.close()


def fetch_batch_prices(symbols: list) -> dict:
    """FMP Batch Quote API 호출"""
    symbols_str = ','.join(symbols)
    url = f"https://financialmodelingprep.com/stable/batch-quote"

    response = httpx.get(
        url,
        params={'symbols': symbols_str, 'apikey': FMP_API_KEY},
        timeout=30
    )
    response.raise_for_status()

    # symbol을 키로 하는 dict로 변환
    return {item['symbol']: item for item in response.json()}


def fetch_batch_history(symbols: list, days: int = 30) -> dict:
    """FMP Historical Price API 호출 (종목별)"""
    history = {}

    for symbol in symbols:
        try:
            url = f"https://financialmodelingprep.com/stable/historical-price-eod/full"
            response = httpx.get(
                url,
                params={
                    'symbol': symbol,
                    'apikey': FMP_API_KEY,
                    'from': (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d'),
                    'to': datetime.now().strftime('%Y-%m-%d')
                },
                timeout=15
            )
            response.raise_for_status()
            data = response.json()

            if isinstance(data, list):
                history[symbol] = data
            elif isinstance(data, dict) and 'historical' in data:
                history[symbol] = data['historical']

        except Exception as e:
            print(f"Failed to fetch history for {symbol}: {e}")
            history[symbol] = []

    return history


def bulk_insert_daily_prices(conn, quotes: dict, history: dict) -> int:
    """일일 가격 Bulk Insert"""

    # Stock ID 매핑
    symbols = list(quotes.keys())
    stock_ids = get_stock_ids(conn, symbols)

    # Insert 데이터 준비
    insert_data = []

    for symbol, quote in quotes.items():
        stock_id = stock_ids.get(symbol)
        if not stock_id:
            continue

        # 오늘 데이터
        insert_data.append((
            stock_id,
            datetime.now().date(),
            Decimal(str(quote.get('open', 0))),
            Decimal(str(quote.get('dayHigh', 0))),
            Decimal(str(quote.get('dayLow', 0))),
            Decimal(str(quote.get('price', 0))),
            quote.get('volume', 0)
        ))

        # 히스토리 데이터
        for h in history.get(symbol, []):
            try:
                insert_data.append((
                    stock_id,
                    datetime.strptime(h['date'], '%Y-%m-%d').date(),
                    Decimal(str(h.get('open', 0))),
                    Decimal(str(h.get('high', 0))),
                    Decimal(str(h.get('low', 0))),
                    Decimal(str(h.get('close', 0))),
                    h.get('volume', 0)
                ))
            except (ValueError, KeyError):
                continue

    # Bulk Upsert
    query = """
        INSERT INTO stocks_dailyprice
        (stock_id, date, open_price, high_price, low_price, close_price, volume)
        VALUES %s
        ON CONFLICT (stock_id, date) DO UPDATE SET
            open_price = EXCLUDED.open_price,
            high_price = EXCLUDED.high_price,
            low_price = EXCLUDED.low_price,
            close_price = EXCLUDED.close_price,
            volume = EXCLUDED.volume,
            updated_at = NOW()
    """

    with conn.cursor() as cur:
        execute_values(cur, query, insert_data)

    return len(insert_data)


def get_stock_ids(conn, symbols: list) -> dict:
    """Symbol -> Stock ID 매핑"""
    query = "SELECT symbol, id FROM stocks_stock WHERE symbol = ANY(%s)"

    with conn.cursor() as cur:
        cur.execute(query, (symbols,))
        return {row[0]: row[1] for row in cur.fetchall()}


def update_sync_status(conn, symbols: list):
    """수집 상태 업데이트"""
    query = """
        UPDATE stocks_stock
        SET last_price_sync_at = NOW()
        WHERE symbol = ANY(%s)
    """

    with conn.cursor() as cur:
        cur.execute(query, (symbols,))
```

---

## 온디맨드 수집 (API Gateway)

사용자가 Stock Detail 페이지 접근 시 실시간 가격 수집.

```
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway                             │
│              POST /api/v1/stocks/sync/{symbol}               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  price-sync-ondemand                         │
│                                                             │
│  1. Rate Limit 체크 (분당 10회/사용자)                        │
│  2. FMP API 호출                                            │
│  3. DB 저장                                                  │
│  4. 캐시 갱신                                                │
└─────────────────────────────────────────────────────────────┘
```

```python
# infra/lambda/price_sync_ondemand/handler.py

def handler(event, context):
    """
    온디맨드 가격 동기화
    트리거: API Gateway
    """
    symbol = event['pathParameters']['symbol'].upper()
    user_id = event['requestContext'].get('authorizer', {}).get('user_id')

    # Rate Limit 체크
    if not check_rate_limit(user_id, limit=10, window=60):
        return {
            'statusCode': 429,
            'body': json.dumps({'error': 'Rate limit exceeded'})
        }

    try:
        # FMP API 호출
        price_data = fetch_single_price(symbol)
        history = fetch_history(symbol, days=30)

        # DB 저장
        conn = get_db_connection()
        save_price_data(conn, symbol, price_data, history)
        conn.commit()
        conn.close()

        # 캐시 갱신
        invalidate_cache(f"stock:{symbol}:price")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'symbol': symbol,
                'status': 'synced',
                'price': price_data.get('price'),
                'last_sync': datetime.now().isoformat()
            })
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

---

## Terraform 구성

```hcl
# infra/terraform/price_sync.tf

# Orchestrator Lambda
resource "aws_lambda_function" "price_sync_orchestrator" {
  filename         = data.archive_file.price_sync_orchestrator.output_path
  function_name    = "price-sync-orchestrator"
  role            = aws_iam_role.lambda_role.arn
  handler         = "handler.handler"
  runtime         = "python3.11"
  timeout         = 300  # 5분
  memory_size     = 256

  environment {
    variables = {
      PRICE_SYNC_QUEUE_URL = aws_sqs_queue.price_sync_queue.url
      DB_HOST              = var.db_host
      DB_NAME              = var.db_name
    }
  }
}

# Worker Lambda
resource "aws_lambda_function" "price_sync_worker" {
  filename         = data.archive_file.price_sync_worker.output_path
  function_name    = "price-sync-worker"
  role            = aws_iam_role.lambda_role.arn
  handler         = "handler.handler"
  runtime         = "python3.11"
  timeout         = 120
  memory_size     = 512

  reserved_concurrent_executions = 10  # FMP Rate Limit

  environment {
    variables = {
      FMP_API_KEY = data.aws_secretsmanager_secret_version.fmp.secret_string
      DB_HOST     = var.db_host
    }
  }
}

# On-demand Lambda
resource "aws_lambda_function" "price_sync_ondemand" {
  filename         = data.archive_file.price_sync_ondemand.output_path
  function_name    = "price-sync-ondemand"
  role            = aws_iam_role.lambda_role.arn
  handler         = "handler.handler"
  runtime         = "python3.11"
  timeout         = 30
  memory_size     = 256
}

# API Gateway
resource "aws_apigatewayv2_api" "price_sync_api" {
  name          = "price-sync-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_route" "price_sync_route" {
  api_id    = aws_apigatewayv2_api.price_sync_api.id
  route_key = "POST /stocks/sync/{symbol}"
  target    = "integrations/${aws_apigatewayv2_integration.price_sync.id}"
}

# EventBridge 스케줄 (장 마감 후)
resource "aws_cloudwatch_event_rule" "price_sync_schedule" {
  name                = "price-sync-daily"
  description         = "Trigger price sync at 17:00 EST (market close)"
  schedule_expression = "cron(0 22 ? * MON-FRI *)"  # UTC 22:00 = EST 17:00
}

# SQS 큐
resource "aws_sqs_queue" "price_sync_queue" {
  name                       = "price-sync-queue"
  visibility_timeout_seconds = 180
  message_retention_seconds  = 86400
}
```

---

## 데이터베이스 스키마 변경

### Stock 모델 수정

```python
# stocks/models.py

class Stock(models.Model):
    symbol = models.CharField(max_length=10, primary_key=True)
    # ... 기존 필드

    # 신규 필드
    last_price_sync_at = models.DateTimeField(null=True, blank=True)
    auto_price_sync = models.BooleanField(default=False)
    price_sync_priority = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['auto_price_sync', 'last_price_sync_at']),
        ]
```

### WatchlistItem 모델 수정

```python
# users/models.py

class WatchlistItem(models.Model):
    # ... 기존 필드

    # 신규 필드 (뉴스와 별도로 가격 동기화 설정)
    auto_price_sync = models.BooleanField(
        default=True,  # 기본 활성화
        help_text="가격 데이터 자동 동기화"
    )
```

---

## 비용 분석

### 예상 종목 수

| 카테고리 | 종목 수 |
|----------|---------|
| 사용자 Watchlist | ~100 |
| 사용자 Portfolio | ~50 |
| Market Movers | 60 |
| S&P 500 + NASDAQ 100 | ~600 |
| 섹터 ETF | 11 |
| **중복 제거 후** | **~700개** |

### 월간 비용

| 항목 | 계산 | 비용 |
|------|------|------|
| **Lambda Orchestrator** | 22일 × 1회 | ~$0.01 |
| **Lambda Worker** | 22일 × 14배치 × 30초 | ~$0.10 |
| **Lambda On-demand** | 1,000회 × 5초 | ~$0.05 |
| **SQS** | ~5,000 메시지 | ~$0.01 |
| **FMP API** | Starter Plan 내 | $0 (기존 플랜) |
| **총합** | | **~$0.20/월** |

---

## FMP API Rate Limit 관리

### Starter Plan 제한

| 제한 | 값 | 대응 |
|------|-----|------|
| 분당 호출 | 10 | Worker 동시성 10 |
| 일일 호출 | 250 | 배치 API 활용 |

### Batch API 활용

```python
# 개별 호출 (비효율)
for symbol in symbols:  # 700개 = 700 API calls
    fetch_price(symbol)

# Batch 호출 (효율)
for batch in chunks(symbols, 50):  # 700/50 = 14 API calls
    fetch_batch_prices(batch)
```

---

## 에러 처리

### 재시도 전략

```python
# SQS 재시도 설정
{
    'maxReceiveCount': 3,  # 3회 재시도
    'deadLetterTargetArn': dlq_arn
}

# Lambda 내부 재시도
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=30)
)
def fetch_with_retry(url, params):
    response = httpx.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()
```

### DLQ 처리

```python
def process_dlq(event, context):
    """실패한 배치 처리"""
    for record in event['Records']:
        message = json.loads(record['body'])

        # 개별 종목 단위로 재시도
        for symbol in message['symbols']:
            try:
                sync_single_symbol(symbol)
            except Exception as e:
                # 알림 전송
                send_alert(f"Price sync failed for {symbol}: {e}")
```

---

## 모니터링

### CloudWatch 메트릭

- `PriceSync.Orchestrator.SymbolsScheduled`
- `PriceSync.Worker.SymbolsSynced`
- `PriceSync.Worker.Errors`
- `PriceSync.OnDemand.Latency`

### 알림 설정

```hcl
resource "aws_cloudwatch_metric_alarm" "price_sync_failures" {
  alarm_name          = "price-sync-high-failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 10

  dimensions = {
    FunctionName = aws_lambda_function.price_sync_worker.function_name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
}
```

---

## 버전 히스토리

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 0.1 | 2026-01-26 | 초안 작성 |
