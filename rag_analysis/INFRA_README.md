# RAG Analysis - Infrastructure Components

## Overview

RAG Analysis 앱의 인프라 컴포넌트 구현 완료:
- Neo4j 그래프 데이터베이스 연결 (Lazy Singleton)
- Redis 캐시 서비스
- Celery 비동기 태스크
- Django Signal 기반 자동 동기화

## Critical Feature: Neo4j Graceful Degradation

**Neo4j가 꺼져 있어도 Django 서버는 정상 작동합니다.**

```python
# neo4j_driver.py
driver = get_neo4j_driver()  # Returns None if connection fails
if driver is None:
    # App continues without graph features
    return fallback_data
```

Django는 시작되며, 단순히 그래프 관련 기능이 비활성화될 뿐입니다.

---

## File Structure

```
rag_analysis/
├── services/
│   ├── neo4j_driver.py         # Lazy connection singleton
│   ├── neo4j_service.py        # Neo4jServiceLite (queries)
│   ├── cache.py                # Redis cache service
│   └── __init__.py             # Service exports
├── tasks.py                    # Celery tasks
├── signals.py                  # Stock model sync signals
├── apps.py                     # Signal registration
├── management/
│   └── commands/
│       └── seed_neo4j_graph.py # Graph seeding command
└── INFRA_README.md             # This file
```

---

## Components

### 1. Neo4j Driver (neo4j_driver.py)

**Lazy Singleton Pattern**
- 첫 호출 시 연결 시도
- 연결 실패 시 None 반환 (앱은 계속 실행)
- Django shutdown 시 자동 종료

```python
from rag_analysis.services import get_neo4j_driver

driver = get_neo4j_driver()
if driver:
    # Use Neo4j
else:
    # Fallback logic
```

### 2. Neo4j Service (neo4j_service.py)

**Graph Query Service**

Features:
- Supply chain relationships
- Competitor discovery
- Sector peer analysis
- Health check

```python
from rag_analysis.services import get_neo4j_service

service = get_neo4j_service()

# Get stock relationships
relationships = service.get_stock_relationships('AAPL')
# Returns:
# {
#     'symbol': 'AAPL',
#     'supply_chain': [...],
#     'competitors': [...],
#     'sector_peers': [...],
#     '_meta': {'source': 'neo4j' | 'fallback'}
# }

# Health check
health = service.health_check()
# Returns:
# {
#     'status': 'healthy' | 'degraded' | 'unavailable',
#     'connected': True/False,
#     'node_count': int,
#     'relationship_count': int
# }
```

### 3. Cache Service (cache.py)

**Redis-based Caching**

```python
from rag_analysis.services import get_cache_service

cache = get_cache_service()

# Graph context
context = cache.get_graph_context('AAPL')
cache.set_graph_context('AAPL', data)

# LLM responses (6시간 TTL)
response = cache.get_llm_response(prompt, model='default')
cache.set_llm_response(prompt, response)

# Invalidate
cache.invalidate_graph('AAPL')
cache.invalidate_analysis('AAPL')
```

**Cache Keys**:
- `rag:graph:{SYMBOL}` - Graph context (1h TTL)
- `rag:llm:{MODEL}:{HASH}` - LLM responses (6h TTL)
- `rag:context:{SYMBOL}` - Analysis context (30m TTL)

### 4. Celery Tasks (tasks.py)

**Async Background Tasks**

```python
from rag_analysis.tasks import (
    sync_stock_to_neo4j,
    delete_stock_from_neo4j,
    batch_sync_stocks_to_neo4j,
    invalidate_graph_cache,
    health_check_neo4j
)

# Single stock sync
result = sync_stock_to_neo4j.delay('AAPL', 'Apple Inc.', 'Technology')

# Batch sync
stocks = [
    {'symbol': 'AAPL', 'name': 'Apple Inc.', 'sector': 'Technology'},
    {'symbol': 'MSFT', 'name': 'Microsoft Corp.', 'sector': 'Technology'},
]
result = batch_sync_stocks_to_neo4j.delay(stocks)

# Health check (for Celery Beat)
result = health_check_neo4j.delay()
```

**Task Features**:
- Idempotent (MERGE queries)
- Retry with exponential backoff
- Neo4j unavailable → 'skipped' status
- Batch processing with memory management (100개 단위)

### 5. Django Signals (signals.py)

**Automatic Neo4j Sync**

```python
# Stock 모델 저장 시 자동 동기화
stock = Stock.objects.create(
    symbol='AAPL',
    stock_name='Apple Inc.',
    sector='Technology'
)
# → sync_stock_to_neo4j.delay('AAPL', ...) 자동 호출

# Stock 모델 삭제 시 Neo4j에서도 삭제
stock.delete()
# → delete_stock_from_neo4j.delay('AAPL') 자동 호출
```

**Signal Handlers**:
- `stock_saved_handler` - Stock 저장/수정 시
- `stock_deleted_handler` - Stock 삭제 시

---

## Management Commands

### seed_neo4j_graph

Neo4j 그래프를 Stock 모델 데이터로 초기화

```bash
# 기본 실행
python manage.py seed_neo4j_graph

# 옵션
python manage.py seed_neo4j_graph --clear  # 기존 데이터 삭제 후 시작
python manage.py seed_neo4j_graph --limit 100  # 100개만 처리
python manage.py seed_neo4j_graph --create-examples  # 예시 관계 생성
```

**실행 단계**:
1. 인덱스 생성 (Stock.symbol, Sector.name)
2. Stock 노드 생성 (100개 단위 배치)
3. Sector 노드 및 BELONGS_TO 관계 생성
4. 예시 관계 생성 (SUPPLIES, COMPETES_WITH)

**예시 관계**:
- NVDA → TSLA (supplies chips, strength: 0.75)
- AAPL ↔ MSFT (competes, overlap: 0.70)
- NVDA ↔ AMD (competes, overlap: 0.85)

---

## Environment Variables

`.env` 파일에 설정:

```bash
# Neo4j Aura (클라우드)
NEO4J_URI=neo4j+s://328caeb4.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j

# 로컬 개발 (Docker)
# NEO4J_URI=bolt://localhost:7687
# NEO4J_USERNAME=neo4j
# NEO4J_PASSWORD=password
```

`config/settings.py`에 이미 설정됨:
```python
NEO4J_CONNECTION_POOL = {
    'max_connection_lifetime': 3600,
    'max_connection_pool_size': 50,
    'connection_acquisition_timeout': 60,
}
```

---

## Testing

### 1. Django 서버 시작 (Neo4j 없이)

```bash
python manage.py check
# System check identified no issues (0 silenced).
```

Neo4j 연결 실패 시:
```
Neo4j connection failed: Cannot resolve address 328caeb4.databases.neo4j.io:7687
Application will continue without Neo4j graph features
```

서버는 정상 시작됩니다!

### 2. 서비스 Import 테스트

```bash
python manage.py shell
```

```python
from rag_analysis.services import get_neo4j_service, get_cache_service

# Neo4j service
service = get_neo4j_service()
health = service.health_check()
# {'status': 'unavailable', 'connected': False, ...}

# Cache service
cache = get_cache_service()
cache.set_graph_context('AAPL', {'test': 'data'})
```

### 3. 태스크 Import 테스트

```python
from rag_analysis.tasks import sync_stock_to_neo4j

# Task name
print(sync_stock_to_neo4j.name)
# 'rag_analysis.tasks.sync_stock_to_neo4j'
```

### 4. 시그널 테스트

```python
from stocks.models import Stock

# Stock 생성 → 자동으로 Neo4j 동기화 태스크 큐에 추가
stock = Stock.objects.create(symbol='TEST', stock_name='Test Inc.')
# Log: "Stock created: TEST - Neo4j sync queued"
```

---

## Celery Beat 스케줄 (Optional)

`config/celery.py`에 추가:

```python
from celery.schedules import crontab

app.conf.beat_schedule = {
    'neo4j-health-check': {
        'task': 'rag_analysis.tasks.health_check_neo4j',
        'schedule': crontab(minute='*/5'),  # 5분마다
    },
}
```

---

## Architecture Diagram

```
Django App
    │
    ├── Stock Model
    │      │
    │      └── post_save/delete signal
    │             │
    │             └── Celery Tasks (async)
    │                    │
    │                    └── Neo4j Service
    │                           │
    │                           └── Neo4j Driver (lazy)
    │                                  │
    │                                  └── Neo4j Aura Cloud
    │
    └── Cache Service → Redis
```

---

## Troubleshooting

### 1. Neo4j 연결 실패

**증상**: "Neo4j connection failed"

**해결**:
- `.env` 파일에 NEO4J_URI, NEO4J_PASSWORD 확인
- Neo4j Aura 인스턴스 상태 확인
- 방화벽/네트워크 설정 확인

**중요**: 앱은 계속 작동하므로 급한 버그 아님

### 2. 태스크가 실행되지 않음

**증상**: Stock 생성해도 Neo4j에 반영 안 됨

**확인**:
```bash
# Celery worker 실행 중인지 확인
celery -A config worker -l info

# Task queue 확인
python manage.py shell
from celery.result import AsyncResult
result = AsyncResult('task_id')
print(result.status)
```

### 3. 캐시가 동작하지 않음

**증상**: 캐시 설정해도 계속 쿼리 실행됨

**확인**:
```bash
# Redis 실행 중인지 확인
redis-cli ping
# PONG

# Django settings에서 CACHES 설정 확인
python manage.py shell
from django.core.cache import cache
cache.set('test', 'value')
print(cache.get('test'))
```

---

## Next Steps

1. **@rag-llm**: LLM 서비스 구현 (llm_service.py, context.py, pipeline.py)
2. **@backend**: API 엔드포인트 추가 (Neo4j 관계 조회)
3. **@qa-architect**: 통합 테스트 작성

---

## Notes

- Neo4j 연결은 **lazy initialization** (첫 사용 시 연결)
- 모든 태스크는 **idempotent** (중복 실행 안전)
- 캐시 TTL은 데이터 특성에 맞게 설정됨
- Signal handler는 **비동기** (Django 트랜잭션 블로킹 없음)

---

**구현 완료 by @infra**
2025-12-15
