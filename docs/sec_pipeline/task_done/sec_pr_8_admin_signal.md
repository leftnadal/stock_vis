# SEC-PR-8: Admin 큐 뷰 + post_save signal

> **완료일**: 2026-04-04

## 생성/수정된 파일

| 파일 | 변경 |
|------|------|
| `sec_pipeline/admin.py` | 8개 모델 Admin 등록 + UnmatchedCompanyQueueAdmin (list_editable, actions) |
| `sec_pipeline/signals.py` | on_unmatched_resolved post_save signal |
| `sec_pipeline/apps.py` | ready()에서 signals import |

## Admin 기능

### UnmatchedCompanyQueueAdmin
- `list_display`: raw_company_name, source_symbol, occurrence_count, cross_sector_flag, status, fuzzy_top1, resolved_ticker
- `list_editable`: status, resolved_ticker (인라인 수정)
- **Actions**: mark_not_public, mark_person, auto_resolve_top_candidate (≥90%)
- **cross_sector_flag**: source_sectors 2개+ → ⚠️ 배지 (동명이의 경고)

### Signal 동작
1. `status='matched'` + `resolved_ticker` 설정 시:
   - 같은 이름 + **같은 sector** evidence만 `target_company` 업데이트
   - `neo4j_dirty=True` 설정
   - `CompanyAlias` 등록 (sector별)
2. 다른 sector evidence에 **전파 금지** (원칙 준수)
3. Neo4j **직접 동기화 금지** (dirty flag만)

## 테스트 결과

```
"third parties" (GOOGL) → AAPL 테스트:
  - Before: 3 unmatched evidences
  - After: 0 unmatched, 3 matched
  - CompanyAlias: 2건 (E-Commerce, Technology sector)
  - Rolled back after verification
```

## 다음 PR

→ SEC-PR-9: sync_dirty_to_neo4j
