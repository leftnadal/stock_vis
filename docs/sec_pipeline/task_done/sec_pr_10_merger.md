# SEC-PR-10: 관계 병합 + 미매칭 큐 처리

> **완료일**: 2026-04-04

## 생성된 파일

| 파일 | 역할 |
|------|------|
| `sec_pipeline/merger.py` | merge_relationship, calculate_edge_dqs |
| `sec_pipeline/management/commands/process_unmatched_queue.py` | fuzzy ≥ 0.90 자동 매칭 command |

## 병합 규칙

- **primary_type**: RELATIONSHIP_SPECIFICITY 점수가 높은 쪽 선택 (SUPPLIES_TO > CUSTOMER_OF > ...)
- **confidence**: bounded boosting (`existing + (1-existing) * new * 0.3`, 최대 0.99)
- **relation_facets**: evidence 텍스트 최대 5개 보존

## DQS (Data Quality Score)

| 키 | 노출 | 설명 |
|----|------|------|
| `_sufficiency` | 내부 | evidence 개수 기반 (3개 → 1.0) |
| `_diversity` | 내부 | source 종류 기반 (3종 → 1.0) |
| `_reliability` | 내부 | 평균 source reliability |
| `_dqs_total` | 내부 | 가중 합계 |
| `source_count` | **API** | evidence 개수 |
| `source_types` | **API** | source 종류 목록 |

## process_unmatched_queue 결과

```
Pending: 60
Auto-matched (≥0.90): 0
Below threshold: 55
No candidates: 5
```

→ 비미국 주식 위주로 DB에 없어서 자동 매칭 불가. Admin 수동 처리 필요.

## Phase 1.5 완료 상태

| PR | 상태 | 핵심 산출물 |
|----|------|-----------|
| SEC-PR-7 | ✅ | TickerMatcher 3단계 매칭 |
| SEC-PR-8 | ✅ | Admin 큐 뷰 + post_save signal |
| SEC-PR-9 | ✅ | sync_dirty_to_neo4j (2건 동기화) |
| SEC-PR-10 | ✅ | 관계 병합 + 미매칭 큐 command |

→ **Phase 1.5 완료. Phase 2 (Track B + 서비스 레이어) 착수 가능.**
