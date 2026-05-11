# 데이터 품질 3대 이슈 수정 보고서

> **완료일**: 2026-04-13
> **브랜치**: `data_structure_remodeling_V1`

## Issue 1: 섹터 수익률 전부 +0% → DailyPrice 기반 계산

### 원인
- Stock.change_percent가 532개 중 24개만 존재 (on-demand 동기화만 구현)
- EOD 배치(sync_sp500_eod_prices)는 DailyPrice만 갱신, Stock 모델은 미갱신

### 수정
- **`stocks/tasks.py`**: `update_sp500_change_percent` Celery task 추가
  - DailyPrice 최신 2일에서 change_percent 일괄 계산 (API 호출 0건)
  - `real_time_price`, `volume`도 함께 업데이트
  - bulk query 2회 (prev_map + today_data) → N+1 없음
- **`config/celery.py`**: Beat 등록 (매일 18:30 EST, EOD sync 직후)

### 결과
- 500/503 종목 change_percent 채워짐
- 섹터 수익률: Technology -1.11%, Healthcare -1.17%, Financial Services -1.37% 등 실제 값 표시

---

## Issue 2: 관계 타입 다양화 (PEER_OF only → 다양한 타입)

### 원인 A
`update_relation_confidence()`가 co_mention/price 데이터를 PEER_OF 점수 보조로만 사용, CO_MENTIONED/PRICE_CORRELATED 관계 자체를 미생성

### 원인 B
`sync_relations_to_neo4j()`가 Neo4j 엣지 라벨을 RELATED_TO로 하드코딩

### 수정

**Step 2A — `chainsight/tasks/relation_tasks.py`**: `update_relation_confidence()` 수정
- 소스별 분리 생성: peer/industry→PEER_OF(truth), co_mention→CO_MENTIONED(market), price→PRICE_CORRELATED(market)
- 독립 점수 기준:
  - CO_MENTIONED: count ≥10=confirmed(85), ≥5=probable(60), ≥2=weak(35)
  - PRICE_CORRELATED: corr ≥0.8=confirmed(85), ≥0.6=probable(60), ≥0.5=weak(35)

**Step 2B — `chainsight/tasks/sync_tasks.py`**: `sync_relations_to_neo4j()` → dirty sync 위임
- 기존 RELATED_TO 하드코딩 로직 제거
- `chainsight/services/neo4j_sync.py`의 `sync_dirty_relations()` 호출 (동적 타입 지원)
- 1회성 레거시 RELATED_TO 엣지 정리 (캐시 플래그로 중복 방지)

**Step 2D — `chainsight/services/neo4j_sync.py`**: market weak 관계 동기화 허용
- `relation_category='market'` + `status='weak'`도 Neo4j에 upsert

**Step 2E — 카테고리 추가**:
- `chainsight/api/views.py`: PRICE_CORRELATED → `price_correlation` 카테고리
- `frontend/components/chainsight/ChainStoryFeed.tsx`: `price_correlation: '가격 상관'`

### 결과
- Neo4j 엣지 타입: PEER_OF(12,178), PRICE_CORRELATED(1,162), CO_MENTIONED(169), RELATED_TO(0)
- Chain Story: "동종 네트워크" + "가격 상관" 카테고리 표시
- RelationConfidence: PEER_OF(9,345), CO_MENTIONED(193), PRICE_CORRELATED(1,162)

---

## Issue 3: trigger_summary 한글 번역

### 원인
API에서 seed_reasons 코드를 그대로 join하여 반환

### 수정
- **`chainsight/api/views.py`**: 모듈 레벨 `REASON_LABELS` dict 추가
- `_build_chain_signals`에서 `REASON_LABELS.get(r, r)` 적용

### 결과
- 이전: `price_bottom5, volume_surge, sector_outlier`
- 이후: "섹터 이상치, 거래량 급증, 수익률 하위 이상치"

---

## 수정된 파일 총 목록

| 파일 | 변경 내용 |
|------|----------|
| `stocks/tasks.py` | `update_sp500_change_percent` task 추가 |
| `config/celery.py` | Beat 등록 (update-sp500-change-percent) |
| `chainsight/tasks/relation_tasks.py` | `update_relation_confidence` → 소스별 관계 타입 분리 |
| `chainsight/tasks/sync_tasks.py` | `sync_relations_to_neo4j` → dirty sync 위임 + 레거시 정리 |
| `chainsight/services/neo4j_sync.py` | market weak 관계 동기화 허용 |
| `chainsight/api/views.py` | REASON_LABELS + trigger_summary 번역 + PRICE_CORRELATED 카테고리 |
| `frontend/components/chainsight/ChainStoryFeed.tsx` | price_correlation 카테고리 라벨 |

## Celery Beat 타임라인 (최종)

```
18:00 EST  sync-sp500-eod-prices (DailyPrice 갱신)
18:30 EST  update-sp500-change-percent (DailyPrice → Stock.change_percent, 신규)
11:00 EST  chainsight-relation-confidence (CO_MENTIONED/PRICE_CORRELATED 추가 생성, 수정됨)
12:30 EST  chainsight-sync-relations-neo4j (dirty sync 위임, 수정됨)
13:00 UTC  chainsight-seed-selection (최신 change_percent 활용)
```
