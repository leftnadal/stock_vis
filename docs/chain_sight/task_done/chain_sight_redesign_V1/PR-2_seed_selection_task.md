# PR-2: 시드 선정 Celery Task

> **완료일**: 2026-04-10
> **브랜치**: `data_structure_remodeling_V1`

## 목표

Phase 1 시드 선정 로직을 Celery task로 구현. 매일 실행, 결과를 Redis에 캐싱하여 `seeds/` API가 읽는다.

## 생성된 파일

| 파일 | 역할 |
|------|------|
| `chainsight/services/__init__.py` | 서비스 패키지 re-export (기존 import 호환 유지) |
| `chainsight/services/neo4j_loader.py` | 기존 `services.py`를 패키지 내부로 이동 |
| `chainsight/services/seed_selection.py` | 시드 선정 서비스 (5개 소스 + 합산 + 캐싱) |
| `chainsight/tasks/seed_tasks.py` | `run_seed_selection` Celery task |

## 수정된 파일

| 파일 | 변경 |
|------|------|
| `chainsight/utils.py` | `get_market_date()` 유틸리티 추가 (주말→직전 금요일) |
| `config/celery.py` | `chainsight-seed-selection` beat 등록 (매일 13:00 UTC) |

## 시드 소스 5개

| # | 함수 | 시드 사유 | 데이터 소스 |
|---|------|----------|------------|
| 1 | `get_price_seeds()` | `price_top5`, `price_bottom5` | DailyPrice (전일 대비 수익률 ±2σ) |
| 2 | `get_volume_seeds()` | `volume_surge` | DailyPrice (거래량/SMA20 ≥ 2.0, raw SQL) |
| 3 | `get_sector_outlier_seeds()` | `sector_outlier` | Stock.change_percent (섹터 내 ±2σ) |
| 4 | `get_relation_change_seeds()` | `relation_upgrade`, `relation_downgrade` | RelationConfidence.previous_status |
| 5 | `get_comention_surge_seeds()` | `comention_surge` | CoMentionEdge (7일 내 count ≥ 5) |

## 핵심 로직

- **합산 랭킹**: 모든 소스 merge → `signal_count` DESC → 상위 20개
- **seed_type 우선순위**: `price > volume > relation > comention`
- **섹터 요약**: bulk query로 N+1 방지, `seed_count` DESC 정렬
- **Redis 캐싱**: `chainsight:seeds:{date}` 키, TTL 24시간
- **fallback**: 시드 부족 시 전일 캐시 carry-over

## 아키텍처

```
services.py (단일 파일) → services/ (패키지)
├── __init__.py       # re-export (기존 import 호환)
├── neo4j_loader.py   # 기존 services.py 이동
└── seed_selection.py # 새 서비스
```
