# CS-0-3: Neo4j 온톨로지 스키마 초기화

> **작업 번호**: CS-0-3
> **목표**: constraint 4개 + index 2개 생성 + management command
> **예상 소요**: 1~2시간
> **선행 조건**: CS-0-2 완료
> **산출물**: `chainsight/graph/schema.py`, `management/commands/init_neo4j_schema.py`

---

## 스키마 정의 (로드맵 섹션 2.4 기준)

### Constraints (4개)

```cypher
CREATE CONSTRAINT stock_ticker IF NOT EXISTS FOR (s:Stock) REQUIRE s.ticker IS UNIQUE;
CREATE CONSTRAINT sector_name IF NOT EXISTS FOR (s:Sector) REQUIRE s.name IS UNIQUE;
CREATE CONSTRAINT industry_name IF NOT EXISTS FOR (i:Industry) REQUIRE i.name IS UNIQUE;
CREATE CONSTRAINT theme_name IF NOT EXISTS FOR (t:Theme) REQUIRE t.name IS UNIQUE;
```

### Indexes (2개 — 로드맵 정의분만)

```cypher
CREATE INDEX stock_sector IF NOT EXISTS FOR (s:Stock) ON (s.sector);
CREATE INDEX stock_community IF NOT EXISTS FOR (s:Stock) ON (s.community_id);
```

⚠️ **점검 결과 반영**: 이전 작업 지시서에서 `stock_market_cap`, `stock_industry` 인덱스를 추가했으나, 로드맵에 정의되지 않아 제거. 원칙 1("문서에 정의되지 않은 기능은 구현하지 않는다") 준수. 추후 필요 시 로드맵에 먼저 추가한다.

---

## 구현

### schema.py

`CONSTRAINTS` 리스트(4개) + `INDEXES` 리스트(2개) 정의.
`initialize_schema(repo)`: 모든 constraint+index 생성 (IF NOT EXISTS 멱등).
`verify_schema(repo)`: SHOW CONSTRAINTS/INDEXES로 대조.

### management command

```bash
python manage.py init_neo4j_schema --verify     # 적용 + 검증
python manage.py init_neo4j_schema --check       # 검증만
python manage.py init_neo4j_schema --reset       # 삭제 후 재적용
```

---

## 검증

```bash
python manage.py init_neo4j_schema --verify
# Constraints (4/4): ✅ stock_ticker, sector_name, industry_name, theme_name
# Indexes (2/2): ✅ stock_sector, stock_community
```

---

## 완료 기준 → Phase 0 완료 (M0)

```
□ constraint 4개 + index 2개 생성 확인
□ 멱등성 확인 (두 번 실행 오류 없음)
□ 유니크 constraint 동작 확인

★ M0 달성: "레거시 정리됨, Neo4j 연결됨, 테이블 있음"
```

→ **다음**: cs_11

**END OF DOCUMENT**
