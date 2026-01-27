# 뉴스 자동 수집 시스템 계획

## 개요

사용자가 모니터링을 원하는 종목과 주요 종목에 대해 뉴스를 자동으로 수집하는 AWS Lambda 기반 시스템입니다.

---

## 핵심 원칙

> **"사용자가 보지 않는 종목은 수집하지 않는다"**

전체 시장의 모든 종목(수천 개)을 수집하는 것은 비효율적입니다.
사용자가 실제로 관심을 가지고 모니터링하는 종목만 수집합니다.

---

## 수집 대상 종목

### 1. 사용자 모니터링 종목 (User-Driven)

사용자가 명시적으로 "뉴스 모니터링"을 활성화한 종목만 수집합니다.

| 출처 | 모니터링 조건 | 예시 |
|------|-------------|------|
| **Watchlist** | `auto_news_sync = True` | 관심종목에서 체크 |
| **Portfolio** | `news_monitoring = True` | 보유종목 설정 |
| **Strategy Room** | `alert_on_news = True` | 전략 알림 설정 |

### 2. 시스템 자동 수집 종목 (System-Driven)

시장 전체 흐름 파악을 위해 주요 종목은 자동 수집합니다.

| 카테고리 | 수집 기준 | 예상 종목 수 |
|----------|----------|-------------|
| **섹터별 Top 20** | 시가총액 기준 | 11 섹터 × 20 = 220개 |
| **인덱스 구성종목** | S&P 500, NASDAQ 100 | 500 + 100 = 600개 |
| **Market Movers** | 당일 급등/급락/거래량 | 60개 (20×3) |

**중복 제거 후 예상 총합: ~500-700개 종목**

---

## 데이터베이스 스키마 변경

### 1. WatchlistItem 모델 수정

```python
# users/models.py

class WatchlistItem(models.Model):
    watchlist = models.ForeignKey(Watchlist, ...)
    stock = models.ForeignKey(Stock, ...)

    # 기존 필드
    target_entry_price = models.DecimalField(...)
    notes = models.TextField(...)
    position_order = models.IntegerField(...)

    # 신규 필드 추가
    auto_news_sync = models.BooleanField(
        default=False,
        help_text="뉴스 자동 수집 활성화"
    )
    news_sync_frequency = models.CharField(
        max_length=20,
        choices=[
            ('realtime', '실시간'),  # 1시간마다
            ('daily', '매일'),       # 1일 1회
            ('weekly', '주간'),      # 1주 1회
        ],
        default='daily'
    )
    last_news_sync_at = models.DateTimeField(null=True, blank=True)
```

### 2. 시스템 수집 대상 테이블

```python
# news/models.py

class NewsCollectionTarget(models.Model):
    """시스템 자동 수집 대상 종목"""

    stock = models.OneToOneField(Stock, on_delete=models.CASCADE)

    # 수집 이유
    collection_reason = models.CharField(
        max_length=50,
        choices=[
            ('sector_top', '섹터 Top 20'),
            ('index_member', '인덱스 구성종목'),
            ('market_mover', 'Market Mover'),
            ('user_requested', '사용자 요청'),
        ]
    )

    # 수집 설정
    priority = models.IntegerField(default=0)  # 높을수록 우선
    sync_frequency = models.CharField(max_length=20, default='daily')

    # 상태
    is_active = models.BooleanField(default=True)
    last_sync_at = models.DateTimeField(null=True)
    next_sync_at = models.DateTimeField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['is_active', 'next_sync_at']),
            models.Index(fields=['collection_reason']),
        ]
```

---

## Lambda 함수 설계

### 1. 스케줄러 Lambda (Orchestrator)

```
┌─────────────────────────────────────────────────────────┐
│                  news-sync-scheduler                     │
│                                                         │
│  트리거: EventBridge (매 시간 정각)                       │
│                                                         │
│  역할:                                                   │
│  1. 수집 대상 종목 조회 (DB)                              │
│  2. 종목별 SQS 메시지 발행                                │
│  3. 배치 크기 조절 (Rate Limit 고려)                      │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                     SQS Queue                            │
│                 news-collection-queue                    │
│                                                         │
│  메시지 예시:                                            │
│  {                                                      │
│    "symbol": "AAPL",                                    │
│    "days": 1,                                           │
│    "priority": "high",                                  │
│    "source": "watchlist"                                │
│  }                                                      │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  news-sync-worker                        │
│                                                         │
│  트리거: SQS (배치 크기: 10)                              │
│                                                         │
│  역할:                                                   │
│  1. Finnhub/Marketaux API 호출                          │
│  2. 뉴스 데이터 파싱 및 중복 제거                          │
│  3. PostgreSQL에 저장                                    │
│  4. 수집 상태 업데이트                                    │
└─────────────────────────────────────────────────────────┘
```

### 2. 스케줄러 Lambda 코드

```python
# infra/lambda/news_scheduler/handler.py

import json
import boto3
from datetime import datetime, timedelta
import psycopg2

sqs = boto3.client('sqs')
QUEUE_URL = os.environ['NEWS_QUEUE_URL']

def handler(event, context):
    """
    매 시간 실행되어 수집 대상 종목을 SQS에 발행
    """
    conn = get_db_connection()

    try:
        # 1. 사용자 모니터링 종목 조회
        user_symbols = get_user_monitoring_symbols(conn)

        # 2. 시스템 자동 수집 종목 조회
        system_symbols = get_system_collection_symbols(conn)

        # 3. 중복 제거 및 우선순위 정렬
        all_symbols = merge_and_prioritize(user_symbols, system_symbols)

        # 4. SQS 메시지 발행 (배치)
        messages_sent = 0
        for batch in chunk_list(all_symbols, 10):
            entries = [
                {
                    'Id': str(i),
                    'MessageBody': json.dumps({
                        'symbol': item['symbol'],
                        'days': 1,
                        'priority': item['priority'],
                        'source': item['source']
                    })
                }
                for i, item in enumerate(batch)
            ]
            sqs.send_message_batch(QueueUrl=QUEUE_URL, Entries=entries)
            messages_sent += len(entries)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'scheduled': messages_sent,
                'user_symbols': len(user_symbols),
                'system_symbols': len(system_symbols)
            })
        }
    finally:
        conn.close()


def get_user_monitoring_symbols(conn):
    """사용자가 모니터링 활성화한 종목 조회"""
    query = """
        SELECT DISTINCT s.symbol, 'user' as source, 10 as priority
        FROM users_watchlistitem wi
        JOIN stocks_stock s ON wi.stock_id = s.id
        WHERE wi.auto_news_sync = TRUE
          AND (wi.last_news_sync_at IS NULL
               OR wi.last_news_sync_at < NOW() - INTERVAL '1 hour')
    """
    with conn.cursor() as cur:
        cur.execute(query)
        return [{'symbol': row[0], 'source': row[1], 'priority': row[2]}
                for row in cur.fetchall()]


def get_system_collection_symbols(conn):
    """시스템 자동 수집 대상 종목 조회"""
    query = """
        SELECT s.symbol, nct.collection_reason as source, nct.priority
        FROM news_newscollectiontarget nct
        JOIN stocks_stock s ON nct.stock_id = s.id
        WHERE nct.is_active = TRUE
          AND (nct.next_sync_at IS NULL OR nct.next_sync_at <= NOW())
        ORDER BY nct.priority DESC
        LIMIT 500
    """
    with conn.cursor() as cur:
        cur.execute(query)
        return [{'symbol': row[0], 'source': row[1], 'priority': row[2]}
                for row in cur.fetchall()]
```

### 3. Worker Lambda 코드

```python
# infra/lambda/news_worker/handler.py

import json
import os
import httpx
from datetime import datetime, timedelta
import psycopg2

FINNHUB_API_KEY = os.environ['FINNHUB_API_KEY']
MARKETAUX_API_KEY = os.environ['MARKETAUX_API_KEY']

def handler(event, context):
    """
    SQS 메시지를 받아 뉴스 수집 실행
    """
    conn = get_db_connection()
    results = []

    try:
        for record in event['Records']:
            message = json.loads(record['body'])
            symbol = message['symbol']
            days = message.get('days', 1)

            try:
                # 1. Finnhub에서 뉴스 수집
                finnhub_news = fetch_finnhub_news(symbol, days)

                # 2. Marketaux에서 뉴스 수집 (Rate Limit 고려)
                marketaux_news = fetch_marketaux_news(symbol, days)

                # 3. 중복 제거
                all_news = deduplicate_news(finnhub_news + marketaux_news)

                # 4. DB 저장
                saved = save_news_to_db(conn, symbol, all_news)

                # 5. 수집 상태 업데이트
                update_sync_status(conn, symbol)

                results.append({
                    'symbol': symbol,
                    'status': 'success',
                    'fetched': len(all_news),
                    'saved': saved
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


def fetch_finnhub_news(symbol: str, days: int) -> list:
    """Finnhub API에서 뉴스 수집"""
    to_date = datetime.now()
    from_date = to_date - timedelta(days=days)

    url = "https://finnhub.io/api/v1/company-news"
    params = {
        'symbol': symbol,
        'from': from_date.strftime('%Y-%m-%d'),
        'to': to_date.strftime('%Y-%m-%d'),
        'token': FINNHUB_API_KEY
    }

    response = httpx.get(url, params=params, timeout=10)
    response.raise_for_status()

    return [
        {
            'url': item['url'],
            'title': item['headline'],
            'summary': item['summary'],
            'source': item['source'],
            'published_at': datetime.fromtimestamp(item['datetime']),
            'image_url': item.get('image', ''),
            'provider': 'finnhub'
        }
        for item in response.json()
    ]
```

---

## 실행 스케줄

### EventBridge Rules

| Rule | Schedule | Lambda | 설명 |
|------|----------|--------|------|
| `news-scheduler-hourly` | `rate(1 hour)` | news-sync-scheduler | 매시간 수집 대상 확인 |
| `news-targets-daily` | `cron(0 6 * * ? *)` | news-update-targets | 매일 06:00 수집 대상 갱신 |

### 수집 빈도별 처리

| 빈도 | 대상 | 스케줄 |
|------|------|--------|
| **실시간** | VIP 사용자 Watchlist | 1시간마다 |
| **매일** | 일반 Watchlist, 시스템 종목 | 1일 1회 (06:00) |
| **주간** | 저우선순위 종목 | 주 1회 (월요일 06:00) |

---

## Rate Limit 관리

### 외부 API 제한

| API | Rate Limit | 대응 전략 |
|-----|------------|----------|
| **Finnhub** | 60/분 | SQS 배치 크기 조절 |
| **Marketaux** | 100/일 | 우선순위 높은 종목만 |

### SQS 설정

```python
# 배치 크기 및 지연 설정
SQS_BATCH_SIZE = 10  # 한 번에 10개 메시지 처리
SQS_VISIBILITY_TIMEOUT = 60  # 60초 내 처리
SQS_DELAY_SECONDS = 2  # 메시지 간 2초 지연

# Reserved Concurrency 설정
LAMBDA_RESERVED_CONCURRENCY = 5  # 최대 5개 동시 실행
# → 분당 최대 50개 종목 처리 (Finnhub 제한 내)
```

---

## 프론트엔드 UI 변경

### Watchlist 설정 UI

```typescript
// frontend/components/watchlist/WatchlistItemSettings.tsx

interface NewsMonitoringSettings {
  autoNewsSync: boolean;
  newsSyncFrequency: 'realtime' | 'daily' | 'weekly';
}

function WatchlistItemSettings({ item, onUpdate }) {
  return (
    <div className="space-y-4">
      {/* 뉴스 모니터링 토글 */}
      <div className="flex items-center justify-between">
        <div>
          <p className="font-medium">뉴스 자동 수집</p>
          <p className="text-sm text-gray-500">
            이 종목의 뉴스를 자동으로 수집합니다
          </p>
        </div>
        <Switch
          checked={item.autoNewsSync}
          onChange={(checked) => onUpdate({ autoNewsSync: checked })}
        />
      </div>

      {/* 수집 빈도 선택 */}
      {item.autoNewsSync && (
        <div>
          <label className="text-sm font-medium">수집 빈도</label>
          <Select
            value={item.newsSyncFrequency}
            onChange={(value) => onUpdate({ newsSyncFrequency: value })}
          >
            <Option value="daily">매일 (권장)</Option>
            <Option value="realtime">실시간 (1시간마다)</Option>
            <Option value="weekly">주간</Option>
          </Select>
        </div>
      )}

      {/* 마지막 수집 시간 */}
      {item.lastNewsSyncAt && (
        <p className="text-xs text-gray-400">
          마지막 수집: {formatRelativeTime(item.lastNewsSyncAt)}
        </p>
      )}
    </div>
  );
}
```

---

## 비용 추정

### 월간 예상 비용

| 항목 | 계산 | 비용 |
|------|------|------|
| **Lambda 실행** | 500종목 × 30일 × 2회/일 = 30,000회 | ~$0.60 |
| **Lambda 시간** | 30,000회 × 2초 × 128MB | ~$0.10 |
| **SQS** | 30,000 메시지 | ~$0.01 |
| **EventBridge** | 24회/일 × 30일 = 720회 | ~$0.001 |
| **CloudWatch** | 로그 1GB | ~$0.50 |
| **총합** | | **~$1.50/월** |

### 스케일 시 비용

| 종목 수 | Lambda | SQS | 총 비용 |
|---------|--------|-----|---------|
| 500 | $0.70 | $0.01 | ~$1.50 |
| 1,000 | $1.40 | $0.02 | ~$3.00 |
| 5,000 | $7.00 | $0.10 | ~$15.00 |

---

## 구현 로드맵

### Week 1: 인프라 구축
- [ ] Terraform 코드 작성
- [ ] Lambda 함수 기본 구조
- [ ] SQS 큐 설정
- [ ] EventBridge 스케줄 설정

### Week 2: 핵심 로직 구현
- [ ] 스케줄러 Lambda 구현
- [ ] Worker Lambda 구현
- [ ] DB 스키마 마이그레이션
- [ ] 뉴스 저장 로직

### Week 3: 프론트엔드 통합
- [ ] Watchlist 설정 UI
- [ ] 수집 상태 표시
- [ ] API 엔드포인트 추가

### Week 4: 테스트 및 배포
- [ ] 단위 테스트
- [ ] 통합 테스트
- [ ] 스테이징 배포
- [ ] 프로덕션 배포

---

## 관련 파일

### 신규 생성
- `infra/terraform/news_lambda.tf`
- `infra/lambda/news_scheduler/handler.py`
- `infra/lambda/news_worker/handler.py`
- `news/models.py` (NewsCollectionTarget 추가)

### 수정 필요
- `users/models.py` (WatchlistItem 필드 추가)
- `users/api/serializers.py`
- `frontend/components/watchlist/*`

---

## 버전 히스토리

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 0.1 | 2026-01-26 | 초안 작성 |
