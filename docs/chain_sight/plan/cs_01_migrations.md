# CS-0-1: Django Migrations 실행 + 검증

> **작업 번호**: CS-0-1
> **목표**: chainsight/ 앱의 12개 테이블이 PostgreSQL에 정상 존재하는지 최종 확인
> **예상 소요**: 30분
> **선행 조건**: CS-0-0 완료 (레거시 정리 + RelationConfidence v2.1 마이그레이션)
> **산출물**: `docs/chain_sight/task_done/CS-0-1_migrations.md`

---

## 배경

CS-0-0 3단계에서 `makemigrations` + `migrate`를 이미 실행했다.
이 작업은 **최종 검증 + 기록**에 집중한다.

---

## 실행 절차

### 1. showmigrations 확인

```bash
python manage.py showmigrations chainsight
```

**기대 결과**: 모든 마이그레이션이 `[X]` 상태

```
chainsight
 [X] 0001_initial
 [X] 0002_...
 [X] ...
```

⚠️ `[ ]` (미적용)이 있으면:

```bash
python manage.py migrate chainsight
```

### 2. 테이블 존재 확인 (PostgreSQL 직접)

```bash
python manage.py dbshell
```

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_name LIKE 'chainsight_%'
ORDER BY table_name;
```

**기대 결과**: 12개 테이블

```
chainsight_capital_dna
chainsight_chain_profile
chainsight_co_mention_edge
chainsight_event_reaction
chainsight_growth_stage
chainsight_insider_signal
chainsight_narrative_tag
chainsight_news_event
chainsight_price_co_movement
chainsight_relation_confidence
chainsight_revenue_structure
chainsight_sensitivity_profile
```

### 3. RelationConfidence v2.1 필드 확인

v2.1 스키마가 정확히 반영되었는지 컬럼 수준으로 확인한다.

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'chainsight_relation_confidence'
ORDER BY ordinal_position;
```

**필수 확인 필드** (v2.1에서 추가/변경된 것):

| 컬럼                       | 타입                        | 확인 |
| -------------------------- | --------------------------- | ---- |
| relation_category          | varchar                     | □    |
| canonical_direction        | varchar                     | □    |
| relation_status            | varchar                     | □    |
| truth_score                | double precision            | □    |
| market_score               | double precision (nullable) | □    |
| investment_relevance       | double precision (nullable) | □    |
| evidence_tier_best         | integer                     | □    |
| evidence_count_total       | integer                     | □    |
| evidence_count_independent | integer                     | □    |
| evidence_sources           | jsonb                       | □    |
| has_peer_source            | boolean                     | □    |
| has_industry_source        | boolean                     | □    |
| has_supply_chain_source    | boolean                     | □    |
| has_news_source            | boolean                     | □    |
| has_price_source           | boolean                     | □    |
| has_etf_source             | boolean                     | □    |
| has_llm_source             | boolean                     | □    |
| relation_basis_summary     | text                        | □    |
| first_observed_at          | timestamp                   | □    |
| last_observed_at           | timestamp                   | □    |
| last_verified_at           | timestamp (nullable)        | □    |
| stale_threshold_days       | integer                     | □    |
| synced_to_neo4j            | boolean                     | □    |
| score_version              | varchar                     | □    |

### 4. 인덱스 + unique constraint 확인

```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'chainsight_relation_confidence';
```

**필수 확인**:

- `unique_together`: (symbol_a, symbol_b, relation_type) ✅
- `index`: relation_status, relation_type, synced_to_neo4j ✅

### 5. CompanyChainProfile 동기화 필드 확인

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'chainsight_chain_profile'
  AND column_name IN ('neo4j_synced', 'neo4j_synced_at');
```

**기대**: 두 필드 모두 존재

### 6. normalize_pair 유틸 존재 확인

```bash
python -c "from chainsight.utils import normalize_pair; print(normalize_pair('TSLA', 'AAPL'))"
```

**기대 결과**: `('AAPL', 'TSLA')` — 사전순 정규화 확인

---

## 완료 기준 체크리스트

```
□ showmigrations chainsight → 전부 [X]
□ 12개 테이블 존재 확인
□ RelationConfidence v2.1 필드 24개 확인
□ 인덱스 + unique constraint 확인
□ CompanyChainProfile neo4j_synced/neo4j_synced_at 존재
□ normalize_pair 함수 정상 작동
```

---

## 완료 기록 작성

`docs/chain_sight/task_done/CS-0-1_migrations.md` 작성:

```markdown
# CS-0-1: Django Migrations 실행 + 검증

> **완료일**: 2026-04-XX
> **소요 시간**: XX분

## 변경된 파일

- (CS-0-0에서 이미 변경됨, 이 작업에서는 검증만 수행)

## 테이블 현황

- chainsight/ 테이블: 12개 전부 확인
- RelationConfidence v2.1 필드: 전부 확인

## 발견된 이슈

- (있으면 기록)

## 다음 작업 연결

- CS-0-2: Neo4j 연결 레이어 구현
```

---

## 다음 작업

→ **CS-0-2**: Neo4j 연결 레이어 구현 (`chainsight/graph/repository.py`)

**END OF DOCUMENT**
