# News Feature Infrastructure Setup

Stock-Vis 뉴스 기능을 위한 3-Tier 저장소 인프라 구축 가이드

---

## 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────┐
│                    3-Tier Storage System                    │
└─────────────────────────────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
    PostgreSQL            Neo4j               Redis
  (영구 저장)          (관계 그래프)          (캐시)
         │                   │                   │
    ┌────────┐          ┌────────┐          ┌────────┐
    │ Stock  │          │ Stock  │          │ API    │
    │ Daily  │          │ News   │          │ Cache  │
    │ Weekly │          │ Entity │          │ Session│
    │ Finance│          │ Relation│         │ Temp   │
    └────────┘          └────────┘          └────────┘
```

**역할 분담**:
- **PostgreSQL**: 주식 데이터, 가격 정보, 재무제표 (영구 저장)
- **Neo4j**: Stock-News-Entity 관계 그래프 (복잡한 관계 쿼리)
- **Redis**: API 응답 캐시, Celery 메시지 브로커, 실시간 데이터

---

## 완료된 작업

### 1. Docker Compose 설정

**파일**: `docker/docker-compose.yml`

**추가된 서비스**:

```yaml
neo4j:
  image: neo4j:5-community
  ports:
    - "7474:7474"  # HTTP Browser
    - "7687:7687"  # Bolt Protocol
  volumes:
    - neo4j_data:/data
    - neo4j_logs:/logs
    - ../scripts:/scripts:ro
  environment:
    - NEO4J_PLUGINS=["apoc"]
    - NEO4J_dbms_memory_heap_max__size=2G
```

**주요 기능**:
- APOC 플러그인 활성화 (고급 그래프 알고리즘)
- 메모리 설정: Heap 2GB, Page Cache 512MB
- 헬스체크: 40초 start_period (초기화 시간 고려)
- 스크립트 마운트: `/scripts` 디렉토리 read-only 접근

### 2. Neo4j 초기화 스크립트

**파일**: `scripts/init-neo4j.cypher`

**생성되는 항목**:

**제약조건 (Constraints)**:
```cypher
CREATE CONSTRAINT stock_symbol_unique IF NOT EXISTS
FOR (s:Stock) REQUIRE s.symbol IS UNIQUE;

CREATE CONSTRAINT news_id_unique IF NOT EXISTS
FOR (n:News) REQUIRE n.news_id IS UNIQUE;

CREATE CONSTRAINT entity_name_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE e.name IS UNIQUE;
```

**인덱스 (Indexes)**:
- Stock: symbol, sector, industry
- News: published_at, source, sentiment_score
- Entity: type

**관계 타입 (정의)**:
- `Stock -[:MENTIONED_IN]-> News` - 뉴스 언급
- `Stock -[:RELATED_TO]-> Stock` - 종목 간 관계
- `News -[:REFERENCES]-> Entity` - 엔티티 참조
- `Entity -[:WORKS_FOR]-> Stock` - 인물-회사 관계

### 3. Django 설정

**파일**: `config/settings.py`

**추가된 설정**:

```python
# News API Keys
FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY', '')
MARKETAUX_API_KEY = os.getenv('MARKETAUX_API_KEY', '')

# News Rate Limits
NEWS_RATE_LIMITS = {
    'finnhub': {
        'per_minute': 60,
        'wait_seconds': 1,
    },
    'marketaux': {
        'per_day': 100,
        'articles_per_request': 3,
        'wait_seconds': 1,
    },
}

# News Cache TTL
NEWS_CACHE_TTL = {
    'stock_news': 3600,      # 1시간
    'trending': 300,         # 5분
    'sentiment': 900,        # 15분
    'entity': 1800,          # 30분
}

# Neo4j Configuration
NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USERNAME = os.getenv('NEO4J_USERNAME', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'password')
NEO4J_DATABASE = os.getenv('NEO4J_DATABASE', 'neo4j')

NEO4J_CONNECTION_POOL = {
    'max_connection_lifetime': 3600,
    'max_connection_pool_size': 50,
    'connection_acquisition_timeout': 60,
}
```

### 4. 환경 변수 문서화

**파일**: `.env.example`, `docs/ENVIRONMENT-VARIABLES.md`

**추가된 환경 변수**:

```bash
# News API Keys
FINNHUB_API_KEY="your_finnhub_api_key_here"
MARKETAUX_API_KEY="your_marketaux_api_key_here"

# Neo4j (로컬 개발)
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j

# Neo4j Aura (클라우드 - 선택)
NEO4J_USE_AURA=True
NEO4J_URI=neo4j+s://your_instance.databases.neo4j.io

# News API 우선순위
NEWS_PRIMARY_PROVIDER=finnhub
NEWS_FALLBACK_PROVIDER=marketaux
```

### 5. 검증 스크립트

**파일**: `scripts/validate-infrastructure.sh`

**검증 항목**:
1. 환경 변수 확인
2. Docker 서비스 확인
3. Neo4j 초기화 스크립트 확인
4. Django 설정 검증
5. 문서 확인

---

## 실행 가이드

### 1. 환경 설정

```bash
# 1. .env 파일 생성
cp .env.example .env

# 2. API 키 설정 (.env 파일 편집)
# FINNHUB_API_KEY="your_key_here"
# MARKETAUX_API_KEY="your_key_here"

# 3. 인프라 검증
bash scripts/validate-infrastructure.sh
```

### 2. Neo4j 서비스 시작

```bash
# 1. Neo4j 단독 실행
cd docker
docker-compose up -d neo4j

# 2. 로그 확인 (초기화 완료 대기)
docker-compose logs -f neo4j

# 3. 헬스체크 확인
docker-compose ps neo4j
```

**예상 출력**:
```
NAME              STATUS              PORTS
stockvis-neo4j    Up (healthy)        0.0.0.0:7474->7474/tcp
                                      0.0.0.0:7687->7687/tcp
```

### 3. Neo4j 초기화

```bash
# 1. 초기화 스크립트 실행
cat scripts/init-neo4j.cypher | \
  docker exec -i stockvis-neo4j \
  cypher-shell -u neo4j -p password

# 2. Neo4j Browser 접속
open http://localhost:7474

# 3. 제약조건 확인
# Neo4j Browser에서 실행:
SHOW CONSTRAINTS;

# 4. 인덱스 확인
SHOW INDEXES;
```

### 4. Python 의존성 설치

```bash
# Neo4j Python Driver 설치
poetry add neo4j

# 또는 pip
pip install neo4j
```

### 5. 전체 스택 실행

```bash
# 모든 서비스 실행
cd docker
docker-compose up -d

# 서비스 상태 확인
docker-compose ps
```

**예상 출력**:
```
NAME                  STATUS              PORTS
stockvis-db           Up (healthy)        5432/tcp
stockvis-redis        Up (healthy)        6379/tcp
stockvis-neo4j        Up (healthy)        7474/tcp, 7687/tcp
stockvis-backend      Up                  8000/tcp
stockvis-celery-worker Up
stockvis-celery-beat  Up
stockvis-frontend     Up                  3000/tcp
```

---

## API 키 발급 가이드

### Finnhub API

1. **회원가입**: https://finnhub.io/register
2. **대시보드**: https://finnhub.io/dashboard
3. **API Key 복사**: Dashboard에서 확인
4. **무료 티어**: 60 calls/min

**주요 기능**:
- 실시간 뉴스
- 감성 분석 (Sentiment Score)
- 회사 뉴스, 시장 뉴스

### Marketaux API

1. **회원가입**: https://www.marketaux.com/register
2. **대시보드**: https://www.marketaux.com/account/dashboard
3. **API Key 복사**: Dashboard에서 확인
4. **무료 티어**: 100 calls/day

**주요 기능**:
- 종합 뉴스 (더 상세한 내용)
- 엔티티 추출 (Entities)
- 다국어 지원

---

## 다음 단계 (Phase 2)

### 1. News Django 앱 생성

```bash
python manage.py startapp news
```

**예상 구조**:
```
news/
├── models.py           # NewsArticle, NewsSource, Entity
├── serializers.py      # NewsSerializer, EntitySerializer
├── views.py            # NewsViewSet, TrendingNewsView
├── tasks.py            # Celery 뉴스 수집 태스크
├── neo4j_client.py     # Neo4j 연결 관리
└── graph_queries.py    # Cypher 쿼리 모음
```

### 2. Neo4j Client 구현

```python
# news/neo4j_client.py
from neo4j import GraphDatabase
from django.conf import settings

class Neo4jClient:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
        )

    def create_stock_news_relation(self, symbol, news_id, relevance):
        with self.driver.session() as session:
            session.run("""
                MATCH (s:Stock {symbol: $symbol})
                MATCH (n:News {news_id: $news_id})
                MERGE (s)-[:MENTIONED_IN {
                    relevance_score: $relevance,
                    created_at: datetime()
                }]->(n)
            """, symbol=symbol, news_id=news_id, relevance=relevance)
```

### 3. Finnhub/Marketaux Client 구현

```python
# API_request/finnhub_client.py
import requests
from django.conf import settings

class FinnhubClient:
    BASE_URL = "https://finnhub.io/api/v1"

    def get_company_news(self, symbol, from_date, to_date):
        params = {
            'symbol': symbol,
            'from': from_date,
            'to': to_date,
            'token': settings.FINNHUB_API_KEY
        }
        response = requests.get(f"{self.BASE_URL}/company-news", params=params)
        response.raise_for_status()
        return response.json()
```

### 4. Celery 뉴스 수집 태스크

```python
# news/tasks.py
from celery import shared_task
from .clients import FinnhubClient, MarketauxClient

@shared_task(rate_limit='60/m')  # Finnhub: 60 calls/min
def collect_stock_news(symbol):
    client = FinnhubClient()
    news_data = client.get_company_news(symbol, from_date, to_date)

    for article in news_data:
        # PostgreSQL에 저장
        NewsArticle.objects.update_or_create(...)

        # Neo4j에 관계 생성
        neo4j_client.create_stock_news_relation(...)
```

### 5. GraphQL API (선택)

뉴스 그래프 쿼리를 위해 GraphQL 도입 고려:

```graphql
query GetStockNews($symbol: String!) {
  stock(symbol: $symbol) {
    symbol
    news(limit: 10) {
      headline
      publishedAt
      sentiment
      entities {
        name
        type
      }
    }
    relatedStocks {
      symbol
      relationReason
    }
  }
}
```

---

## 모니터링

### Neo4j Browser

```bash
# 접속
open http://localhost:7474

# 로그인
Username: neo4j
Password: password
```

**유용한 쿼리**:

```cypher
// 전체 노드 개수
MATCH (n) RETURN labels(n) AS NodeType, count(n) AS Count;

// 최근 뉴스 10개
MATCH (n:News)
RETURN n.news_id, n.headline, n.published_at
ORDER BY n.published_at DESC
LIMIT 10;

// 특정 종목 뉴스 관계
MATCH (s:Stock {symbol: 'AAPL'})-[r:MENTIONED_IN]->(n:News)
RETURN s.symbol, n.headline, r.relevance_score
ORDER BY r.created_at DESC
LIMIT 10;

// 관련 종목 찾기
MATCH (s1:Stock {symbol: 'AAPL'})-[:RELATED_TO]->(s2:Stock)
RETURN s1.symbol, s2.symbol, count(*) AS connections;
```

### Redis CLI

```bash
# Redis 연결
docker exec -it stockvis-redis redis-cli

# 뉴스 캐시 확인
KEYS news:*

# 캐시 TTL 확인
TTL news:stock:AAPL

# 캐시 내용 확인
GET news:stock:AAPL
```

---

## 트러블슈팅

### Neo4j 연결 실패

```bash
# Neo4j 로그 확인
docker-compose logs neo4j

# 컨테이너 재시작
docker-compose restart neo4j

# 볼륨 초기화 (데이터 삭제 주의!)
docker-compose down -v
docker-compose up -d neo4j
```

### 메모리 부족

**증상**: Neo4j가 OOM으로 종료됨

**해결**:
```yaml
# docker-compose.yml 수정
environment:
  - NEO4J_dbms_memory_heap_max__size=1G  # 2G → 1G로 감소
  - NEO4J_dbms_memory_pagecache_size=256M
```

### API Rate Limit 초과

**증상**: 429 Too Many Requests

**해결**:
```python
# config/settings.py 수정
NEWS_RATE_LIMITS = {
    'finnhub': {
        'per_minute': 30,  # 60 → 30으로 감소
        'wait_seconds': 2,  # 1 → 2로 증가
    },
}
```

---

## 성능 최적화

### Neo4j 쿼리 최적화

```cypher
// 인덱스 활용 (symbol 검색)
MATCH (s:Stock {symbol: 'AAPL'})  // 인덱스 사용
RETURN s;

// 비효율적 쿼리 (전체 스캔)
MATCH (s:Stock)
WHERE s.name CONTAINS 'Apple'  // 인덱스 미사용
RETURN s;
```

### Redis 캐싱 전략

```python
# 종목별 뉴스 캐싱
cache_key = f"news:stock:{symbol}"
cached_news = cache.get(cache_key)

if not cached_news:
    news = NewsArticle.objects.filter(stock__symbol=symbol)[:10]
    cache.set(cache_key, news, timeout=settings.NEWS_CACHE_TTL['stock_news'])
else:
    news = cached_news
```

---

## 보안 고려사항

1. **API 키 관리**:
   - `.env` 파일은 Git에 커밋 금지
   - 프로덕션에서는 환경 변수 또는 Secret Manager 사용

2. **Neo4j 비밀번호**:
   - 기본 비밀번호 변경 필수
   - 강력한 비밀번호 사용 (16자 이상)

3. **CORS 설정**:
   - 프로덕션에서는 특정 도메인만 허용
   - `CORS_ALLOW_ALL_ORIGINS = False`

4. **Rate Limiting**:
   - Django REST Framework throttling 설정
   - API 엔드포인트별 제한 설정

---

## 리소스

### 공식 문서
- **Neo4j**: https://neo4j.com/docs/
- **Finnhub**: https://finnhub.io/docs/api
- **Marketaux**: https://www.marketaux.com/documentation

### 학습 자료
- **Neo4j Graph Academy**: https://graphacademy.neo4j.com/
- **Cypher Query Language**: https://neo4j.com/docs/cypher-manual/current/

---

## 완료 체크리스트

- [x] Docker Compose Neo4j 서비스 추가
- [x] Neo4j 초기화 스크립트 작성
- [x] Django 설정 추가 (NEWS, NEO4J)
- [x] 환경 변수 문서화
- [x] 검증 스크립트 작성
- [ ] Neo4j Python Driver 설치
- [ ] News Django 앱 생성
- [ ] Finnhub/Marketaux Client 구현
- [ ] Neo4j Client 구현
- [ ] Celery 뉴스 수집 태스크 구현
- [ ] API 엔드포인트 구현
- [ ] Frontend 뉴스 컴포넌트 구현

---

**작성일**: 2025-12-08
**작성자**: @infra
**버전**: 1.0.0
