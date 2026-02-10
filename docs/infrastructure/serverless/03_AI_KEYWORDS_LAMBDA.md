# AI 키워드 생성 Lambda 전환 계획

## 개요

Market Movers 및 Screener 종목에 대한 AI 키워드 생성 시스템을 AWS Lambda로 전환하는 계획입니다.

---

## 현재 구현 (Celery)

### 태스크 구조

```python
# serverless/tasks.py

@shared_task
def generate_keywords_for_movers(mover_type: str, date: str):
    """Market Movers 키워드 생성"""
    service = KeywordGenerationService()
    movers = MarketMover.objects.filter(mover_type=mover_type, date=date)

    for mover in movers:
        # 1. 컨텍스트 수집 (뉴스, 가격 등)
        context = collect_context(mover.symbol)

        # 2. LLM 호출 (Gemini)
        keywords = service.generate(mover.symbol, context)

        # 3. DB 저장
        StockKeyword.objects.create(
            symbol=mover.symbol,
            date=date,
            keywords=keywords
        )
```

### 현재 문제점

| 문제 | 영향 |
|------|------|
| LLM 호출 순차 실행 | 60개 종목 × 6초 = 6분 소요 |
| Celery Worker 메모리 | LLM 응답 누적으로 메모리 증가 |
| Rate Limit 관리 어려움 | Gemini 15 RPM 제한 |
| 단일 실패점 | 중간 에러 시 전체 재시작 필요 |

---

## 목표 아키텍처 (Lambda)

```
┌─────────────────────────────────────────────────────────────┐
│              Market Movers Worker Lambda                     │
│                  (지표 계산 완료 후)                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        SQS Queue                             │
│                   keyword-generation-queue                   │
│                                                             │
│  메시지 예시:                                                │
│  {                                                          │
│    "symbol": "AAPL",                                        │
│    "company_name": "Apple Inc.",                            │
│    "sector": "Technology",                                  │
│    "mover_type": "gainers",                                 │
│    "change_percent": 5.23,                                  │
│    "date": "2026-01-26"                                     │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  keyword-generator-lambda                    │
│                                                             │
│  동시성 제한: 3 (Gemini 15 RPM 고려)                         │
│                                                             │
│  처리 흐름:                                                  │
│  1. 컨텍스트 수집 (뉴스 헤드라인, 가격 변동)                   │
│  2. 프롬프트 생성                                            │
│  3. Gemini API 호출                                         │
│  4. 응답 파싱 및 검증                                        │
│  5. PostgreSQL 저장                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Lambda 함수 설계

### 1. Keyword Generator Lambda

```python
# infra/lambda/keyword_generator/handler.py

import json
import os
import time
from datetime import datetime
import google.generativeai as genai
import psycopg2

# Gemini 설정
genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-2.0-flash')

# Rate Limit: 15 RPM = 4초 간격
RATE_LIMIT_DELAY = 4.0

def handler(event, context):
    """
    종목별 AI 키워드 생성
    트리거: SQS (keyword-generation-queue)
    동시성: 3 (Reserved Concurrency)
    """
    conn = get_db_connection()
    results = []

    try:
        for record in event['Records']:
            message = json.loads(record['body'])
            symbol = message['symbol']

            try:
                # 1. 컨텍스트 수집
                context = collect_context(conn, message)

                # 2. 프롬프트 생성
                prompt = build_prompt(message, context)

                # 3. Gemini API 호출
                start_time = time.time()
                response = model.generate_content(
                    prompt,
                    generation_config={
                        'max_output_tokens': 1200,
                        'temperature': 0.3
                    }
                )
                generation_time = int((time.time() - start_time) * 1000)

                # 4. 응답 파싱
                keywords = parse_keywords(response.text)

                # 5. DB 저장
                save_keywords(conn, {
                    'symbol': symbol,
                    'date': message['date'],
                    'company_name': message.get('company_name', ''),
                    'keywords': keywords,
                    'llm_model': 'gemini-2.0-flash',
                    'generation_time_ms': generation_time,
                    'prompt_tokens': response.usage_metadata.prompt_token_count,
                    'completion_tokens': response.usage_metadata.candidates_token_count
                })

                results.append({
                    'symbol': symbol,
                    'status': 'success',
                    'keywords': keywords,
                    'generation_time_ms': generation_time
                })

                # Rate Limit 대기
                time.sleep(RATE_LIMIT_DELAY)

            except Exception as e:
                # 폴백 키워드 사용
                fallback = get_fallback_keywords(message.get('mover_type', 'gainers'))
                save_keywords(conn, {
                    'symbol': symbol,
                    'date': message['date'],
                    'company_name': message.get('company_name', ''),
                    'keywords': fallback,
                    'llm_model': 'fallback',
                    'generation_time_ms': 0,
                    'error_message': str(e)
                })

                results.append({
                    'symbol': symbol,
                    'status': 'fallback',
                    'error': str(e),
                    'keywords': fallback
                })

        conn.commit()
        return {'statusCode': 200, 'results': results}

    finally:
        conn.close()


def collect_context(conn, message: dict) -> dict:
    """종목 컨텍스트 수집"""
    symbol = message['symbol']

    # 최근 뉴스 헤드라인
    news_query = """
        SELECT title, published_at
        FROM news_newsarticle na
        JOIN news_newsentity ne ON na.id = ne.news_id
        WHERE ne.symbol = %s
        ORDER BY published_at DESC
        LIMIT 5
    """
    with conn.cursor() as cur:
        cur.execute(news_query, (symbol,))
        news = [{'title': row[0], 'date': row[1].isoformat()} for row in cur.fetchall()]

    # 최근 가격 변동
    price_query = """
        SELECT date, close_price, volume
        FROM stocks_dailyprice dp
        JOIN stocks_stock s ON dp.stock_id = s.id
        WHERE s.symbol = %s
        ORDER BY date DESC
        LIMIT 5
    """
    with conn.cursor() as cur:
        cur.execute(price_query, (symbol,))
        prices = [{'date': str(row[0]), 'close': float(row[1]), 'volume': row[2]}
                  for row in cur.fetchall()]

    return {
        'news_headlines': news,
        'price_history': prices,
        'sector': message.get('sector', ''),
        'change_percent': message.get('change_percent', 0)
    }


def build_prompt(message: dict, context: dict) -> str:
    """LLM 프롬프트 생성"""
    return f"""당신은 주식 시장 분석가입니다.
다음 종목의 오늘 주가 움직임을 설명하는 핵심 키워드 3개를 생성해주세요.

## 종목 정보
- 심볼: {message['symbol']}
- 회사명: {message.get('company_name', '')}
- 섹터: {context.get('sector', '')}
- 오늘 변동률: {context.get('change_percent', 0):.2f}%
- 유형: {message.get('mover_type', '')}

## 최근 뉴스
{chr(10).join([f"- {n['title']}" for n in context.get('news_headlines', [])])}

## 규칙
1. 정확히 3개 키워드만 반환
2. 각 키워드는 15자 이내
3. 한국어로 작성
4. JSON 배열 형식으로 반환

## 예시 출력
["AI 수요 증가", "실적 호조", "목표가 상향"]

## 출력"""


def parse_keywords(response_text: str) -> list:
    """LLM 응답에서 키워드 추출"""
    import re

    # JSON 배열 찾기
    match = re.search(r'\[.*?\]', response_text, re.DOTALL)
    if match:
        try:
            keywords = json.loads(match.group())
            if isinstance(keywords, list) and len(keywords) >= 2:
                return keywords[:5]  # 최대 5개
        except json.JSONDecodeError:
            pass

    # JSON 파싱 실패 시 따옴표 내용 추출
    pattern = r'"([^"]+)"'
    matches = re.findall(pattern, response_text)
    if len(matches) >= 2:
        return matches[:5]

    # 최종 폴백
    return ["분석 중", "데이터 수집", "모니터링"]


def get_fallback_keywords(mover_type: str) -> list:
    """폴백 키워드"""
    fallbacks = {
        'gainers': ["급등", "거래량 증가", "모멘텀"],
        'losers': ["급락", "매도 압력", "조정"],
        'actives': ["거래량 급증", "변동성", "투자자 관심"],
    }
    return fallbacks.get(mover_type, ["분석 중", "데이터 수집", "모니터링"])


def save_keywords(conn, data: dict):
    """키워드 DB 저장"""
    query = """
        INSERT INTO serverless_stockkeyword
        (symbol, date, company_name, keywords, status, llm_model,
         generation_time_ms, prompt_tokens, completion_tokens, error_message,
         created_at, expires_at)
        VALUES (%s, %s, %s, %s, 'completed', %s, %s, %s, %s, %s, NOW(), NOW() + INTERVAL '7 days')
        ON CONFLICT (symbol, date)
        DO UPDATE SET
            keywords = EXCLUDED.keywords,
            status = 'completed',
            llm_model = EXCLUDED.llm_model,
            generation_time_ms = EXCLUDED.generation_time_ms,
            updated_at = NOW()
    """
    with conn.cursor() as cur:
        cur.execute(query, (
            data['symbol'], data['date'], data['company_name'],
            json.dumps(data['keywords']), data.get('llm_model', 'gemini-2.0-flash'),
            data.get('generation_time_ms', 0),
            data.get('prompt_tokens', 0), data.get('completion_tokens', 0),
            data.get('error_message', '')
        ))
```

---

## Terraform 구성

```hcl
# infra/terraform/keywords_lambda.tf

# Lambda 함수
resource "aws_lambda_function" "keyword_generator" {
  filename         = data.archive_file.keyword_generator.output_path
  function_name    = "keyword-generator"
  role            = aws_iam_role.lambda_role.arn
  handler         = "handler.handler"
  runtime         = "python3.11"
  timeout         = 120  # 2분 (여러 종목 처리)
  memory_size     = 512  # LLM 응답 처리

  # 동시성 제한 (Gemini 15 RPM 고려)
  reserved_concurrent_executions = 3

  environment {
    variables = {
      GEMINI_API_KEY = data.aws_secretsmanager_secret_version.gemini.secret_string
      DB_HOST        = var.db_host
      DB_NAME        = var.db_name
      DB_USER        = var.db_user
      DB_PASSWORD    = data.aws_secretsmanager_secret_version.db.secret_string
    }
  }

  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  layers = [
    aws_lambda_layer_version.google_genai.arn
  ]
}

# Lambda Layer (google-generativeai)
resource "aws_lambda_layer_version" "google_genai" {
  filename            = "layers/google_genai_layer.zip"
  layer_name          = "google-generativeai"
  compatible_runtimes = ["python3.11"]
}

# SQS 큐
resource "aws_sqs_queue" "keyword_queue" {
  name                       = "keyword-generation-queue"
  visibility_timeout_seconds = 180  # Lambda timeout × 1.5
  message_retention_seconds  = 86400

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.keyword_dlq.arn
    maxReceiveCount     = 2
  })
}

# SQS -> Lambda 트리거
resource "aws_lambda_event_source_mapping" "keyword_trigger" {
  event_source_arn = aws_sqs_queue.keyword_queue.arn
  function_name    = aws_lambda_function.keyword_generator.arn
  batch_size       = 3  # Rate Limit 고려
}
```

---

## Rate Limit 관리

### Gemini API 제한

| 티어 | RPM | RPD | 대응 |
|------|-----|-----|------|
| **Free** | 15 | 1,500 | 4초 간격, 동시성 3 |
| **Pay-as-you-go** | 360 | 제한 없음 | 동시성 증가 가능 |

### Lambda 동시성 설정

```
Gemini Free: 15 RPM
├── Lambda 동시성: 3
├── 메시지당 처리 시간: ~5초
├── 분당 처리량: 3 × (60/5) = 36개
└── 실제 분당 호출: ~12개 (Rate Limit 대기 포함)
```

### SQS 배치 설정

```python
# 배치 크기: 3 (동시성과 일치)
# 가시성 타임아웃: 180초 (Lambda timeout × 1.5)
# 재시도: 2회 후 DLQ
```

---

## 비용 분석

### Lambda 비용

| 항목 | 계산 | 비용 |
|------|------|------|
| 실행 횟수 | 60종목 × 30일 = 1,800회 | $0.0004 |
| 실행 시간 | 1,800회 × 10초 × 512MB | $0.15 |
| **Lambda 총합** | | **~$0.16/월** |

### Gemini API 비용 (Pay-as-you-go)

| 항목 | 계산 | 비용 |
|------|------|------|
| Input | 1,800회 × 500 tokens × $0.000125 | $0.11 |
| Output | 1,800회 × 100 tokens × $0.000375 | $0.07 |
| **Gemini 총합** | | **~$0.18/월** |

### 총 비용

| 항목 | 비용 |
|------|------|
| Lambda | $0.16 |
| Gemini API | $0.18 |
| SQS | $0.01 |
| **총합** | **~$0.35/월** |

---

## 에러 처리 전략

### 1. Gemini API 에러

```python
RETRY_ERRORS = [
    'RESOURCE_EXHAUSTED',  # Rate Limit
    'UNAVAILABLE',         # 서비스 일시 불가
    'DEADLINE_EXCEEDED',   # 타임아웃
]

def call_gemini_with_retry(prompt: str, max_retries: int = 3) -> str:
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            if any(err in str(e) for err in RETRY_ERRORS):
                wait_time = 2 ** attempt * 5  # 지수 백오프: 5, 10, 20초
                time.sleep(wait_time)
            else:
                raise
    raise Exception("Max retries exceeded")
```

### 2. JSON 파싱 에러

```python
def safe_parse_keywords(response_text: str) -> list:
    """안전한 키워드 파싱"""
    try:
        # 1차: JSON 배열 파싱
        keywords = parse_json_array(response_text)
        if keywords:
            return keywords

        # 2차: 따옴표 내용 추출
        keywords = extract_quoted_strings(response_text)
        if keywords:
            return keywords

        # 3차: 폴백
        return ["분석 완료", "데이터 확인", "추가 분석 필요"]

    except Exception:
        return ["분석 중", "데이터 수집", "모니터링"]
```

### 3. DLQ 처리

```python
# infra/lambda/keyword_dlq_processor/handler.py

def handler(event, context):
    """DLQ 메시지 처리"""
    for record in event['Records']:
        message = json.loads(record['body'])

        # 폴백 키워드로 저장
        save_fallback_keywords(
            symbol=message['symbol'],
            date=message['date'],
            mover_type=message.get('mover_type', 'unknown'),
            error='DLQ processed'
        )

        # 알림 전송
        send_alert(f"Keyword generation failed for {message['symbol']}")
```

---

## 모니터링

### CloudWatch 메트릭

```python
# 커스텀 메트릭 발행
cloudwatch = boto3.client('cloudwatch')

def publish_metrics(symbol: str, success: bool, generation_time: int):
    cloudwatch.put_metric_data(
        Namespace='StockVis/Keywords',
        MetricData=[
            {
                'MetricName': 'GenerationSuccess',
                'Value': 1 if success else 0,
                'Unit': 'Count',
                'Dimensions': [{'Name': 'Symbol', 'Value': symbol}]
            },
            {
                'MetricName': 'GenerationTime',
                'Value': generation_time,
                'Unit': 'Milliseconds'
            }
        ]
    )
```

### 대시보드

- 성공률 (Success Rate)
- 평균 생성 시간 (Avg Generation Time)
- 폴백 사용률 (Fallback Rate)
- DLQ 메시지 수

---

## 버전 히스토리

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 0.1 | 2026-01-26 | 초안 작성 |
