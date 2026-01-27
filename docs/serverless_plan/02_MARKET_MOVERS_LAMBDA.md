# Market Movers Lambda 전환 계획

## 개요

현재 Celery로 운영 중인 Market Movers 동기화 태스크를 AWS Lambda로 전환하는 계획입니다.

---

## 현재 구현 (Celery)

### 태스크 구조

```python
# serverless/tasks.py
@shared_task
def sync_daily_market_movers():
    """매일 07:30 EST 실행"""
    service = MarketMoversSync()
    service.sync_all_types()  # gainers, losers, actives
```

### Celery Beat 스케줄

```python
# config/settings.py
CELERY_BEAT_SCHEDULE = {
    'sync-market-movers': {
        'task': 'serverless.tasks.sync_daily_market_movers',
        'schedule': crontab(hour=7, minute=30),
        'options': {'expires': 3600}
    }
}
```

### 현재 문제점

| 문제 | 영향 |
|------|------|
| Celery Worker 24/7 실행 | 비용 낭비 (하루 1회만 사용) |
| 단일 실패점 | Worker 다운 시 전체 중단 |
| 스케일링 어려움 | 종목 수 증가 시 수동 확장 필요 |

---

## 목표 아키텍처 (Lambda)

```
┌─────────────────────────────────────────────────────────────┐
│                    EventBridge Scheduler                     │
│                  cron(30 7 * * ? *) EST                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  market-movers-orchestrator                  │
│                                                             │
│  1. FMP API에서 Gainers/Losers/Actives 조회                  │
│  2. 각 종목별 SQS 메시지 발행                                 │
│  3. 전체 진행 상태 DynamoDB에 기록                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        SQS Queue                             │
│                  market-movers-indicators                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  market-movers-worker                        │
│                                                             │
│  1. 종목별 히스토리 데이터 조회 (FMP)                         │
│  2. 5개 지표 계산 (RVOL, Trend, Alpha, Sync, Vol)            │
│  3. PostgreSQL에 저장                                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  market-movers-keywords                      │
│                                                             │
│  1. 종목별 컨텍스트 수집                                      │
│  2. Gemini API 호출 (키워드 생성)                            │
│  3. StockKeyword 모델에 저장                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Lambda 함수 설계

### 1. Orchestrator Lambda

```python
# infra/lambda/market_movers_orchestrator/handler.py

import json
import boto3
import httpx
from datetime import datetime
import os

sqs = boto3.client('sqs')
FMP_API_KEY = os.environ['FMP_API_KEY']
QUEUE_URL = os.environ['MOVERS_QUEUE_URL']

def handler(event, context):
    """
    Market Movers 수집 오케스트레이터
    트리거: EventBridge (매일 07:30 EST)
    """
    results = {
        'timestamp': datetime.now().isoformat(),
        'types_processed': [],
        'total_stocks': 0
    }

    mover_types = ['gainers', 'losers', 'actives']

    for mover_type in mover_types:
        try:
            # 1. FMP API에서 Market Movers 조회
            stocks = fetch_market_movers(mover_type)

            # 2. SQS에 종목별 메시지 발행
            for stock in stocks[:20]:  # Top 20만
                message = {
                    'symbol': stock['symbol'],
                    'mover_type': mover_type,
                    'change_percent': stock['changesPercentage'],
                    'price': stock['price'],
                    'company_name': stock.get('name', ''),
                    'date': datetime.now().strftime('%Y-%m-%d')
                }
                sqs.send_message(
                    QueueUrl=QUEUE_URL,
                    MessageBody=json.dumps(message),
                    MessageGroupId=mover_type  # FIFO 큐 사용 시
                )

            results['types_processed'].append({
                'type': mover_type,
                'count': len(stocks[:20])
            })
            results['total_stocks'] += len(stocks[:20])

        except Exception as e:
            results['types_processed'].append({
                'type': mover_type,
                'error': str(e)
            })

    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }


def fetch_market_movers(mover_type: str) -> list:
    """FMP API에서 Market Movers 조회"""
    endpoints = {
        'gainers': 'https://financialmodelingprep.com/stable/biggest-gainers',
        'losers': 'https://financialmodelingprep.com/stable/biggest-losers',
        'actives': 'https://financialmodelingprep.com/stable/most-actives'
    }

    response = httpx.get(
        endpoints[mover_type],
        params={'apikey': FMP_API_KEY},
        timeout=30
    )
    response.raise_for_status()
    return response.json()
```

### 2. Indicator Worker Lambda

```python
# infra/lambda/market_movers_worker/handler.py

import json
import os
import httpx
from datetime import datetime, timedelta
from decimal import Decimal
import psycopg2

FMP_API_KEY = os.environ['FMP_API_KEY']

def handler(event, context):
    """
    종목별 지표 계산 Worker
    트리거: SQS (market-movers-indicators)
    """
    conn = get_db_connection()
    results = []

    try:
        for record in event['Records']:
            message = json.loads(record['body'])
            symbol = message['symbol']
            mover_type = message['mover_type']
            date = message['date']

            try:
                # 1. 히스토리 데이터 조회
                history = fetch_historical_data(symbol, days=30)
                quote = fetch_quote(symbol)

                # 2. 5개 지표 계산
                indicators = calculate_indicators(symbol, history, quote)

                # 3. DB 저장
                save_market_mover(conn, {
                    'symbol': symbol,
                    'date': date,
                    'mover_type': mover_type,
                    'company_name': message.get('company_name', ''),
                    'price': message['price'],
                    'change_percent': message['change_percent'],
                    **indicators
                })

                results.append({
                    'symbol': symbol,
                    'status': 'success',
                    'indicators': indicators
                })

            except Exception as e:
                results.append({
                    'symbol': symbol,
                    'status': 'error',
                    'error': str(e)
                })

        conn.commit()
        return {'statusCode': 200, 'results': results}

    finally:
        conn.close()


def calculate_indicators(symbol: str, history: list, quote: dict) -> dict:
    """5개 지표 계산"""

    # RVOL (Relative Volume)
    avg_volume = sum(h['volume'] for h in history[-20:]) / 20
    current_volume = quote.get('volume', 0)
    rvol = current_volume / avg_volume if avg_volume > 0 else 0

    # Trend Strength
    today = history[-1] if history else {}
    open_price = today.get('open', 0)
    close_price = today.get('close', 0)
    high_price = today.get('high', 0)
    low_price = today.get('low', 0)
    price_range = high_price - low_price
    trend_strength = (close_price - open_price) / price_range if price_range > 0 else 0

    # Sector Alpha (섹터 ETF 대비 초과수익)
    sector_alpha = calculate_sector_alpha(symbol, history)

    # ETF Sync Rate (섹터 ETF와 상관계수)
    etf_sync_rate = calculate_etf_sync(symbol, history)

    # Volatility Percentile
    volatility_percentile = calculate_volatility_percentile(history)

    return {
        'rvol': round(rvol, 2),
        'trend_strength': round(trend_strength, 2),
        'sector_alpha': round(sector_alpha, 2),
        'etf_sync_rate': round(etf_sync_rate, 2),
        'volatility_percentile': round(volatility_percentile, 0)
    }


def save_market_mover(conn, data: dict):
    """Market Mover 데이터 저장"""
    query = """
        INSERT INTO serverless_marketmover
        (symbol, date, mover_type, company_name, price, change_percent,
         rvol, trend_strength, sector_alpha, etf_sync_rate, volatility_percentile,
         created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        ON CONFLICT (symbol, date, mover_type)
        DO UPDATE SET
            price = EXCLUDED.price,
            change_percent = EXCLUDED.change_percent,
            rvol = EXCLUDED.rvol,
            trend_strength = EXCLUDED.trend_strength,
            sector_alpha = EXCLUDED.sector_alpha,
            etf_sync_rate = EXCLUDED.etf_sync_rate,
            volatility_percentile = EXCLUDED.volatility_percentile,
            updated_at = NOW()
    """
    with conn.cursor() as cur:
        cur.execute(query, (
            data['symbol'], data['date'], data['mover_type'],
            data['company_name'], data['price'], data['change_percent'],
            data['rvol'], data['trend_strength'], data['sector_alpha'],
            data['etf_sync_rate'], data['volatility_percentile']
        ))
```

---

## Terraform 구성

```hcl
# infra/terraform/market_movers.tf

# Lambda 함수 - Orchestrator
resource "aws_lambda_function" "movers_orchestrator" {
  filename         = data.archive_file.movers_orchestrator.output_path
  function_name    = "market-movers-orchestrator"
  role            = aws_iam_role.lambda_role.arn
  handler         = "handler.handler"
  runtime         = "python3.11"
  timeout         = 120
  memory_size     = 256

  environment {
    variables = {
      FMP_API_KEY     = data.aws_secretsmanager_secret_version.fmp.secret_string
      MOVERS_QUEUE_URL = aws_sqs_queue.movers_queue.url
    }
  }

  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [aws_security_group.lambda_sg.id]
  }
}

# Lambda 함수 - Worker
resource "aws_lambda_function" "movers_worker" {
  filename         = data.archive_file.movers_worker.output_path
  function_name    = "market-movers-worker"
  role            = aws_iam_role.lambda_role.arn
  handler         = "handler.handler"
  runtime         = "python3.11"
  timeout         = 60
  memory_size     = 256

  reserved_concurrent_executions = 5  # Rate Limit 고려

  environment {
    variables = {
      FMP_API_KEY = data.aws_secretsmanager_secret_version.fmp.secret_string
      DB_HOST     = var.db_host
      DB_NAME     = var.db_name
      DB_USER     = var.db_user
      DB_PASSWORD = data.aws_secretsmanager_secret_version.db.secret_string
    }
  }

  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [aws_security_group.lambda_sg.id]
  }
}

# SQS 큐
resource "aws_sqs_queue" "movers_queue" {
  name                       = "market-movers-indicators"
  visibility_timeout_seconds = 120
  message_retention_seconds  = 86400  # 1일

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.movers_dlq.arn
    maxReceiveCount     = 3
  })
}

# Dead Letter Queue
resource "aws_sqs_queue" "movers_dlq" {
  name = "market-movers-indicators-dlq"
}

# EventBridge 스케줄
resource "aws_cloudwatch_event_rule" "movers_schedule" {
  name                = "market-movers-daily"
  description         = "Trigger Market Movers sync at 07:30 EST"
  schedule_expression = "cron(30 12 ? * MON-FRI *)"  # UTC 12:30 = EST 07:30
}

resource "aws_cloudwatch_event_target" "movers_target" {
  rule      = aws_cloudwatch_event_rule.movers_schedule.name
  target_id = "movers-orchestrator"
  arn       = aws_lambda_function.movers_orchestrator.arn
}

# Lambda 트리거 (SQS -> Worker)
resource "aws_lambda_event_source_mapping" "movers_worker_trigger" {
  event_source_arn = aws_sqs_queue.movers_queue.arn
  function_name    = aws_lambda_function.movers_worker.arn
  batch_size       = 5
}
```

---

## 마이그레이션 계획

### Phase 1: 병행 운영 (1주)

```
EventBridge ──▶ Lambda (신규)
                   │
Celery Beat ──▶ Celery Worker (기존)
                   │
                   ▼
              PostgreSQL (동일 테이블)
```

- Lambda와 Celery 모두 실행
- 결과 비교 검증
- Lambda 결과에 `_source = 'lambda'` 태그

### Phase 2: Lambda 전환 (1주)

- Celery Beat 스케줄 비활성화
- Lambda만 실행
- 모니터링 강화

### Phase 3: Celery 제거

- `serverless/tasks.py`에서 태스크 삭제
- Celery Beat 스케줄 제거
- 문서 업데이트

---

## 비용 비교

### 현재 (Celery)

| 항목 | 비용 |
|------|------|
| EC2 (t3.small) 24/7 | ~$15/월 |
| Redis (ElastiCache) | ~$15/월 |
| **총합** | **~$30/월** |

### Lambda 전환 후

| 항목 | 계산 | 비용 |
|------|------|------|
| Lambda Orchestrator | 30일 × 1회 × 10초 | ~$0.01 |
| Lambda Worker | 30일 × 60종목 × 5초 | ~$0.05 |
| SQS | 1,800 메시지/월 | ~$0.01 |
| EventBridge | 30 이벤트/월 | ~$0.001 |
| **총합** | | **~$0.10/월** |

**절감액: ~$29.90/월 (99.7% 절감)**

---

## 모니터링

### CloudWatch 메트릭

- `MarketMovers.Orchestrator.Duration`
- `MarketMovers.Worker.SuccessRate`
- `MarketMovers.Worker.ErrorCount`
- `MarketMovers.SQS.ApproximateNumberOfMessages`

### 알림 설정

```hcl
resource "aws_cloudwatch_metric_alarm" "movers_errors" {
  alarm_name          = "market-movers-high-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Market Movers Lambda 에러율 높음"

  dimensions = {
    FunctionName = aws_lambda_function.movers_worker.function_name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
}
```

---

## 롤백 계획

Lambda 전환 후 문제 발생 시:

1. EventBridge Rule 비활성화
2. Celery Beat 스케줄 재활성화
3. 원인 분석 및 수정
4. 재배포

```bash
# 긴급 롤백 명령
aws events disable-rule --name market-movers-daily

# Celery Beat 재시작
celery -A config beat -l info
```

---

## 버전 히스토리

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 0.1 | 2026-01-26 | 초안 작성 |
