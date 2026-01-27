// ============================================================
// Stock-Vis Neo4j Initialization Script
// ============================================================
//
// Purpose: News 기능을 위한 Neo4j 그래프 데이터베이스 초기화
// Architecture: 3-Tier Storage System
//   - PostgreSQL: 영구 저장 (Stock, DailyPrice, etc.)
//   - Neo4j: 관계 그래프 (Stock-News-Entity 관계)
//   - Redis: 캐시 (API 응답, 실시간 데이터)
//
// Usage:
//   1. Neo4j Browser에서 실행: http://localhost:7474
//   2. cypher-shell 실행:
//      cat scripts/init-neo4j.cypher | cypher-shell -u neo4j -p password
//
// ============================================================

// ============================================================
// 1. 기존 제약조건/인덱스 정리 (재실행 시)
// ============================================================

// Stock 제약조건 제거 (존재하는 경우)
DROP CONSTRAINT stock_symbol_unique IF EXISTS;

// News 제약조건 제거 (존재하는 경우)
DROP CONSTRAINT news_id_unique IF EXISTS;

// Entity 제약조건 제거 (존재하는 경우)
DROP CONSTRAINT entity_name_unique IF EXISTS;

// ============================================================
// 2. 노드 제약조건 (Constraints)
// ============================================================

// Stock 노드: symbol은 unique key (PostgreSQL Stock.symbol과 동일)
CREATE CONSTRAINT stock_symbol_unique IF NOT EXISTS
FOR (s:Stock) REQUIRE s.symbol IS UNIQUE;

// News 노드: news_id는 unique key (Finnhub/Marketaux API ID)
CREATE CONSTRAINT news_id_unique IF NOT EXISTS
FOR (n:News) REQUIRE n.news_id IS UNIQUE;

// Entity 노드: name은 unique key (회사명, 인물명, 지역명 등)
CREATE CONSTRAINT entity_name_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE e.name IS UNIQUE;

// ============================================================
// 3. 인덱스 (Indexes)
// ============================================================

// Stock 노드 인덱스
CREATE INDEX stock_symbol_idx IF NOT EXISTS FOR (s:Stock) ON (s.symbol);
CREATE INDEX stock_sector_idx IF NOT EXISTS FOR (s:Stock) ON (s.sector);
CREATE INDEX stock_industry_idx IF NOT EXISTS FOR (s:Stock) ON (s.industry);

// News 노드 인덱스
CREATE INDEX news_published_at_idx IF NOT EXISTS FOR (n:News) ON (n.published_at);
CREATE INDEX news_source_idx IF NOT EXISTS FOR (n:News) ON (n.source);
CREATE INDEX news_sentiment_idx IF NOT EXISTS FOR (n:News) ON (n.sentiment_score);

// Entity 노드 인덱스
CREATE INDEX entity_type_idx IF NOT EXISTS FOR (e:Entity) ON (e.type);

// ============================================================
// 4. 관계 타입 정의 (주석으로만 기록)
// ============================================================

// Stock -[:MENTIONED_IN]-> News
//   - relevance_score: 0.0 ~ 1.0 (뉴스와 종목 연관도)
//   - position: "positive" | "neutral" | "negative" (뉴스 내 종목 언급 맥락)
//
// 예시:
// MATCH (s:Stock {symbol: 'AAPL'}), (n:News {news_id: '12345'})
// CREATE (s)-[:MENTIONED_IN {relevance_score: 0.85, position: 'positive'}]->(n)

// Stock -[:RELATED_TO]-> Stock
//   - reason: "same_sector" | "supply_chain" | "competitor" | "merger"
//   - strength: 0.0 ~ 1.0 (관계 강도)
//
// 예시:
// MATCH (s1:Stock {symbol: 'AAPL'}), (s2:Stock {symbol: 'MSFT'})
// CREATE (s1)-[:RELATED_TO {reason: 'competitor', strength: 0.7}]->(s2)

// News -[:REFERENCES]-> Entity
//   - count: Integer (뉴스 내 엔티티 언급 횟수)
//
// 예시:
// MATCH (n:News {news_id: '12345'}), (e:Entity {name: 'Tim Cook'})
// CREATE (n)-[:REFERENCES {count: 3}]->(e)

// Entity -[:WORKS_FOR]-> Stock
//   - role: String (CEO, CFO, Board Member, etc.)
//   - start_date: Date
//
// 예시:
// MATCH (e:Entity {name: 'Tim Cook'}), (s:Stock {symbol: 'AAPL'})
// CREATE (e)-[:WORKS_FOR {role: 'CEO', start_date: date('2011-08-24')}]->(s)

// ============================================================
// 5. 초기 데이터 예시 (Optional - 테스트용)
// ============================================================

// 예시 Stock 노드 생성 (실제로는 Django에서 동기화)
// CREATE (:Stock {
//   symbol: 'AAPL',
//   name: 'Apple Inc.',
//   sector: 'Technology',
//   industry: 'Consumer Electronics',
//   last_synced_at: datetime()
// });

// ============================================================
// 6. 유틸리티 쿼리 (관리용 - 실행하지 않음)
// ============================================================

// 전체 노드 개수 확인
// MATCH (n) RETURN labels(n) AS NodeType, count(n) AS Count;

// 전체 관계 개수 확인
// MATCH ()-[r]->() RETURN type(r) AS RelationType, count(r) AS Count;

// Stock 노드와 연결된 News 개수 확인
// MATCH (s:Stock)-[:MENTIONED_IN]->(n:News)
// RETURN s.symbol, count(n) AS NewsCount
// ORDER BY NewsCount DESC
// LIMIT 10;

// 특정 기간 뉴스 조회
// MATCH (n:News)
// WHERE n.published_at >= datetime('2025-01-01T00:00:00')
//   AND n.published_at <= datetime('2025-12-31T23:59:59')
// RETURN n.news_id, n.headline, n.published_at
// ORDER BY n.published_at DESC
// LIMIT 20;

// 긍정적 뉴스만 조회
// MATCH (s:Stock)-[r:MENTIONED_IN]->(n:News)
// WHERE r.position = 'positive' AND n.sentiment_score > 0.5
// RETURN s.symbol, n.headline, n.sentiment_score
// ORDER BY n.sentiment_score DESC
// LIMIT 10;

// ============================================================
// 초기화 완료
// ============================================================
//
// 다음 단계:
// 1. Django에서 neo4j driver 설치: pip install neo4j
// 2. config/settings.py에 NEO4J 설정 추가
// 3. news 앱 생성 및 Neo4j 연동 로직 구현
//
// ============================================================
