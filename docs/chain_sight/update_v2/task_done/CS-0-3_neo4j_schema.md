# CS-0-3: Neo4j 온톨로지 스키마 초기화

> **완료일**: 2026-04-18
> **브랜치**: `tier1/code-quality-fixes`

## 수정 사항

`chainsight/graph/schema.py`에서 로드맵 외 인덱스 2개 제거:
- ~~`stock_market_cap`~~ — 로드맵 정의 외
- ~~`stock_industry`~~ — 로드맵 정의 외

## 검증 결과

### Constraints (4개) ✅

| # | 이름 | 대상 | 상태 |
|---|------|------|------|
| 1 | stock_ticker | Stock.ticker UNIQUE | ✅ |
| 2 | sector_name | Sector.name UNIQUE | ✅ |
| 3 | industry_name | Industry.name UNIQUE | ✅ |
| 4 | theme_name | Theme.name UNIQUE | ✅ |

### Indexes (2개) ✅

| # | 이름 | 대상 | 상태 |
|---|------|------|------|
| 1 | stock_sector | Stock.sector | ✅ |
| 2 | stock_community | Stock.community_id | ✅ |

### 멱등성 ✅

- 2회 연속 `python manage.py init_neo4j_schema` 실행 → 에러 없음 (IF NOT EXISTS)

## 완료 체크리스트

```
[x] constraint 4개 생성
[x] index 2개 생성
[x] 중복 실행 시 에러 없음 (IF NOT EXISTS)
★ M0 달성: "레거시 정리됨, Neo4j 연결됨, 테이블 있음"
```

→ **다음**: cs_11 (Phase 1 시작)
