# Scripts Directory

Stock-Vis 프로젝트 스크립트 모음

---

## Neo4j 초기화

### init-neo4j.cypher

**목적**: 뉴스 기능을 위한 Neo4j 그래프 데이터베이스 초기화

**실행 방법**:

```bash
# 1. Docker Compose로 Neo4j 실행
cd docker
docker-compose up -d neo4j

# 2. Neo4j 헬스체크 확인 (약 40초 소요)
docker-compose ps neo4j

# 3. 초기화 스크립트 실행
cat scripts/init-neo4j.cypher | docker exec -i stockvis-neo4j cypher-shell -u neo4j -p password

# 또는 Neo4j Browser에서 수동 실행
# http://localhost:7474 접속 후 init-neo4j.cypher 내용 복사/붙여넣기
```

**생성되는 항목**:

- **제약조건 (Constraints)**:
  - `Stock.symbol` UNIQUE
  - `News.news_id` UNIQUE
  - `Entity.name` UNIQUE

- **인덱스 (Indexes)**:
  - Stock: symbol, sector, industry
  - News: published_at, source, sentiment_score
  - Entity: type

- **관계 타입 (주석으로 정의)**:
  - `Stock -[:MENTIONED_IN]-> News`
  - `Stock -[:RELATED_TO]-> Stock`
  - `News -[:REFERENCES]-> Entity`
  - `Entity -[:WORKS_FOR]-> Stock`

**검증**:

```bash
# Neo4j Browser에서 실행
MATCH (n) RETURN labels(n) AS NodeType, count(n) AS Count;

# 제약조건 확인
SHOW CONSTRAINTS;

# 인덱스 확인
SHOW INDEXES;
```

---

## 향후 추가 예정 스크립트

### data-migration/

- PostgreSQL → Neo4j 데이터 동기화
- Stock 노드 초기 생성

### backup/

- Neo4j 데이터 백업/복원
- 정기 백업 스크립트

### monitoring/

- Neo4j 성능 모니터링
- 쿼리 분석

---

## 주의사항

- 모든 스크립트는 프로젝트 루트에서 실행해야 합니다
- Neo4j 비밀번호는 환경변수로 관리되어야 합니다
- 프로덕션 환경에서는 강력한 비밀번호를 사용하세요
