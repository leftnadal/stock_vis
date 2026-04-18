# CS-0-3: Neo4j 온톨로지 스키마 초기화

> **작업 번호**: CS-0-3
> **로드맵 버전**: v1.4 (변경 없음)
> **목표**: constraint/index 생성 확인
> **예상 소요**: 1시간
> **선행 조건**: CS-0-2 완료
> **산출물**: `chainsight/graph/schema.py` + management command

---

## 생성할 제약 조건 + 인덱스 (로드맵 정의 — 2개 카테고리)

### Constraints (4개)
```cypher
CREATE CONSTRAINT stock_ticker IF NOT EXISTS FOR (s:Stock) REQUIRE s.ticker IS UNIQUE;
CREATE CONSTRAINT sector_name IF NOT EXISTS FOR (s:Sector) REQUIRE s.name IS UNIQUE;
CREATE CONSTRAINT industry_name IF NOT EXISTS FOR (i:Industry) REQUIRE i.name IS UNIQUE;
CREATE CONSTRAINT theme_name IF NOT EXISTS FOR (t:Theme) REQUIRE t.name IS UNIQUE;
```

### Indexes (2개)
```cypher
CREATE INDEX stock_sector IF NOT EXISTS FOR (s:Stock) ON (s.sector);
CREATE INDEX stock_community IF NOT EXISTS FOR (s:Stock) ON (s.community_id);
```

⚠️ 로드맵 정의 이외의 인덱스를 추가하지 않는다. 필요 시 로드맵 먼저 수정.

## Management Command

```bash
python manage.py init_neo4j_schema
# → 6개 생성 확인
```

## 완료 기준

```
□ constraint 4개 생성
□ index 2개 생성
□ 중복 실행 시 에러 없음 (IF NOT EXISTS)
★ M0 달성: "레거시 정리됨, Neo4j 연결됨, 테이블 있음"
```

→ **다음**: cs_11 (Phase 1 시작)

**END OF DOCUMENT**
