# CS-0-1: Django Migrations 검증

> **작업 번호**: CS-0-1
> **목표**: chainsight/ 12개 테이블 존재 확인 + RelationConfidence v2.1 필드 검증
> **예상 소요**: 30분
> **선행 조건**: CS-0-0 완료
> **산출물**: `task_done/CS-0-1_migrations.md`

---

## 실행

```bash
python manage.py showmigrations chainsight  # 전부 [X]
```

```sql
-- 12개 테이블 확인
SELECT table_name FROM information_schema.tables
WHERE table_name LIKE 'chainsight_%' ORDER BY table_name;

-- RelationConfidence v2.1 컬럼 확인
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'chainsight_relation_confidence'
ORDER BY ordinal_position;

-- 인덱스 + unique constraint
SELECT indexname, indexdef FROM pg_indexes
WHERE tablename = 'chainsight_relation_confidence';

-- ChainProfile 동기화 필드
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'chainsight_chain_profile'
  AND column_name IN ('neo4j_synced', 'neo4j_synced_at');
```

```bash
# normalize_pair 동작 확인
python -c "from chainsight.utils import normalize_pair; print(normalize_pair('TSLA', 'AAPL'))"
# → ('AAPL', 'TSLA')
```

---

## 완료 기준

```
□ showmigrations 전부 [X]
□ 12개 테이블 존재
□ RelationConfidence v2.1 필드 24개 확인
□ unique_together (symbol_a, symbol_b, relation_type) 확인
□ neo4j_synced / neo4j_synced_at 존재
□ normalize_pair 정상
```

→ **다음**: cs_02

**END OF DOCUMENT**
