# PR-1 보완: RelationConfidence 스키마 필드 추가

> **완료일**: 2026-04-10
> **브랜치**: `data_structure_remodeling_V1`

## 목표

PR-2(시드 선정)와 PR-3(Neo4j dirty sync)의 선행 요건인 스키마 필드를 RelationConfidence 모델에 추가.

## 변경된 파일

| 파일 | 변경 |
|------|------|
| `chainsight/models/relation_discovery.py` | `neo4j_dirty`, `previous_status`, `neo4j_synced_at` 필드 추가 + `save()` 오버라이드 |
| `chainsight/migrations/0005_add_neo4j_dirty_previous_status.py` | 마이그레이션 자동 생성 |

## 추가된 필드

| 필드 | 타입 | 용도 |
|------|------|------|
| `previous_status` | CharField(12) | 직전 상태 보존. 시드 선정 시 relation_upgrade/downgrade 판단 |
| `neo4j_dirty` | BooleanField(default=True) | Neo4j 동기화 필요 플래그. save() 시 자동 True |
| `neo4j_synced_at` | DateTimeField(null) | 마지막 Neo4j 동기화 시각 |

## save() 오버라이드 동작

1. `pk`가 존재하면 DB에서 기존 `relation_status`를 조회
2. 상태가 변경되었으면 `previous_status`에 이전 값 보존
3. `neo4j_dirty = True` 자동 설정 (bulk_update에서는 미작동 — 수동 관리 필요)

## 검증

- 마이그레이션 적용 완료 (`python manage.py migrate chainsight`)
- 인덱스: `neo4j_dirty` 필드에 DB 인덱스 생성
