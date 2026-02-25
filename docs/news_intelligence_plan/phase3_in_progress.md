# Phase 3: Neo4j 통합 + API (✅ 완료)

## 기간
Week 5-6

## 목표
LLM 심층 분석 결과를 Neo4j에 동기화하여 뉴스 이벤트 그래프를 구축하고,
API 엔드포인트를 통해 프론트엔드에 영향도 맵을 제공합니다.

## 구현 내용

### 1. Neo4j 동기화 서비스 — `news/services/news_neo4j_sync.py`

**NewsNeo4jSyncService** 클래스:

**노드 생성**:
- `create_news_event_node()`: NewsEvent 노드 MERGE
  - 속성: article_id, title, source, importance_score, tier, published_at

**관계 생성 (4종류)**:
- `create_direct_impact()`: NewsEvent → Stock (DIRECTLY_IMPACTS)
  - 속성: direction, confidence, reason, expires_at
- `create_indirect_impact()`: NewsEvent → Stock (INDIRECTLY_IMPACTS)
  - 속성: direction, confidence, reason, chain_logic, expires_at
- `create_opportunity()`: NewsEvent → Stock (CREATES_OPPORTUNITY)
  - 속성: thesis, timeframe, confidence, expires_at
- `create_sector_ripple()`: NewsEvent → Sector (AFFECTS_SECTOR)
  - 속성: direction, reason, expires_at

**동기화 작업**:
- `sync_article(article)`: 단일 기사 LLM 분석 결과 → Neo4j 동기화
- `sync_batch(max_articles)`: 미동기화 기사 배치 처리 (기존 이벤트 ID 확인 후 스킵)

**관계 강화 (Reinforcement)**:
- `reinforce_relationships(symbol, days)`: 같은 종목 같은 방향 뉴스 3건+ → confidence +10%

**정리 (Cleanup)**:
- `cleanup_expired_relationships()`: TTL 만료 관계 삭제 + 고립 노드 정리

**조회 (Query)**:
- `get_news_events_for_symbol(symbol, days, limit)`: 종목별 뉴스 이벤트
- `get_impact_map(days, limit)`: 전체 영향도 맵 (시각화용)
- `get_symbol_impact_summary(symbol, days)`: 종목 영향 요약 (bullish/bearish 카운트)

### 2. 관계 생명주기 (TTL)
| 관계 타입 | TTL |
|-----------|-----|
| DIRECTLY_IMPACTS | 30일 |
| INDIRECTLY_IMPACTS | 21일 |
| CREATES_OPPORTUNITY | 14일 |
| AFFECTS_SECTOR | 21일 |

### 3. Sector Ripple 가드레일
- 최대 2-hop 전파
- 노드당 최대 20개 관계
- 14일 TTL

### 4. API 엔드포인트 — `news/api/views.py`
- `GET /api/v1/news/news-events/?symbol=NVDA&days=7`
  - 종목 관련 뉴스 이벤트 + 영향 관계 + 요약 정보
  - days 최대 30일 제한, 5분 캐시
- `GET /api/v1/news/news-events/impact-map/?days=7`
  - 전체 영향도 맵 (nodes + edges + stats)
  - 시각화용, 5분 캐시

### 5. Celery 태스크 — `news/tasks.py`
- `sync_news_to_neo4j`: 매 2시간 (08:45~18:45, 평일), max 100건
- `cleanup_expired_news_relationships`: 매일 04:00 EST

### 6. Celery Beat 스케줄 — `config/celery.py`
- `sync-news-to-neo4j`: LLM 분석 완료 15분 후 (분류 :15, 분석 :30, 동기화 :45)
- `cleanup-expired-news-relationships`: 새벽 4시 정리

### 7. 서비스 등록 — `news/services/__init__.py`
- `NewsNeo4jSyncService` 추가

### 8. Graceful Fallback
- Neo4j 미연결 시 빈 결과 반환 (서비스 중단 없음)
- `is_available()` 체크 후 모든 메서드에서 fallback 처리

## 테스트 — `tests/news/test_news_neo4j_sync.py`
- **66개 테스트** 전체 통과
- 테스트 범위:
  - Availability (2개)
  - NewsEvent Node Creation (5개)
  - Direct Impact (5개)
  - Indirect Impact (3개)
  - Opportunity (2개)
  - Sector Ripple (3개)
  - Sync Article (7개)
  - Sync Batch (3개)
  - Existing Event IDs (4개)
  - Reinforcement (5개)
  - Cleanup (3개)
  - News Events Query (5개)
  - Impact Map (4개)
  - Symbol Impact Summary (5개)
  - TTL Configuration (2개)
  - Celery Tasks (4개)
  - API Endpoints (4개)

## 검증 결과
- 66개 신규 테스트 통과
- 전체 뉴스 테스트 429개 통과 (기존 363 + 신규 66)
- API 엔드포인트 정상 응답:
  - `/api/v1/news/news-events/?symbol=NVDA` → 200 (빈 이벤트, Neo4j 미연결)
  - `/api/v1/news/news-events/impact-map/` → 200 (빈 맵, Neo4j 미연결)
