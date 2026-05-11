# Chain Sight 마켓 뷰 — 브라우저 테스트 리포트

> **테스트일**: 2026-04-11
> **환경**: localhost:3000 (Next.js) + localhost:8000 (Django)

## 사전 준비: 시드 데이터 수동 생성

테스트 시 `/chainsight/seeds/` API가 빈 응답(`total_seeds: 0`)을 반환함.

### 원인

시드 선정 task(`chainsight-seed-selection`)는 **Celery Beat 스케줄러에만 등록**되어 있고 (매일 13:00 UTC), 앱 시작 시 자동 실행되지 않는다. Celery worker + beat가 실행 중이어야 스케줄대로 동작하며, 로컬 개발 환경에서 worker/beat를 띄우지 않았거나 등록 시점 이후 아직 스케줄 시각이 도래하지 않았으면 데이터가 비어 있다.

### 해결

Django shell에서 수동 실행:
```python
from chainsight.tasks.seed_tasks import run_seed_selection
run_seed_selection()  # → 16개 시드 생성
```

### 향후 개선 방안

- `python manage.py chainsight_seed_selection` 관리 커맨드 추가 고려
- 또는 seeds API에서 캐시 미스 시 on-demand 시드 계산 fallback 추가 고려
- 현재는 Celery Beat 자동 실행이 유일한 트리거 (worker + beat 모두 실행 필수)

---

## 테스트 결과

### 1. 페이지 진입 (`/chainsight`)

| 항목 | 결과 |
|------|------|
| 섹터 바 렌더 | ✅ 6개 섹터 (Technology -3.11%, Energy +0%, Consumer Cyclical +0%, Financial Services +0%, Real Estate +0%, Consumer Defensive +0%) |
| seed_count DESC 정렬 | ✅ Technology(10) 가 맨 앞 |
| 그래프 empty state | ✅ "섹터를 선택하세요" |
| 관계 카드 empty state | ✅ "섹터를 선택하면 대표 시드 카드가 표시됩니다" |
| 체인 스토리 empty state | ✅ "체인 시그널이 없습니다" |
| Header Chain Sight 네비 | ✅ 데스크톱/모바일 모두 표시 |

### 2. 섹터 선택 (Technology 클릭)

| 항목 | 결과 |
|------|------|
| 섹터 바 선택 상태 | ✅ 파란 보더 + 파란 배경 |
| overview graph 렌더 | ✅ 12개 노드 (ADSK, ANET, ADBE, ACN, AMAT, APH, CDW, AKAM, BR, ADI, DAY 등) |
| 시드 노드 시각 구분 | ✅ AKAM 빨간 보더 (price 시드) |
| 트레일 | ✅ "Tech" 노드 표시 |
| pre-focus 시드 카드 | ✅ 10개 카드 (AKAM, FICO, NOW, SMCI, COHR, SATS, PANW, CDNS, PLTR, GDDY) |
| seed_type badge | ✅ price(빨강), volume(초록) 정상 구분 |
| 시드 사유 텍스트 | ✅ "거래량 급증, 수익률 하위 이상치", "수익률 상위 이상치", "섹터 이상치" 등 |
| daily_return 표시 | ✅ -16.66%, +8.79% 등 |
| volume_ratio 표시 | ✅ Vol 2.7x, Vol 3.0x 등 |

### 3. 중심 이동 (AKAM "여기서 탐색" 클릭)

| 항목 | 결과 |
|------|------|
| 그래프 중심 이동 | ✅ AKAM 큰 중심 노드 (price 빨간 보더) |
| 이웃 노드 표시 | ✅ GDDY, FFIV, SWKS, VRSN, GEN (5개) |
| cross_edges | ✅ 이웃 간 연결선 표시 |
| 트레일 확장 | ✅ "Tech ── AKAM" |
| focused 관계 카드 | ✅ RELATED (5) 그룹 헤더 + 카드 5장 |
| 카드 내 관계 설명 | ✅ "관련 종목" (RELATED_TO 템플릿) |
| 카드 내 why now | ✅ "섹터 이상치" (GDDY), "관계 기반 탐색 후보" (FFIV 등) |
| 카드 내 신뢰도 | ✅ "신뢰도 60" |
| CTA 3종 | ✅ "여기서 탐색", "가설", "Deep" |

### 4. 2차 중심 이동 (GDDY "여기서 탐색" 클릭)

| 항목 | 결과 |
|------|------|
| 그래프 GDDY 중심 | ✅ GDDY 큰 노드 + 이웃 5개 (CPAY, FFIV, VRSN, AKAM, GEN) |
| AKAM 히스토리 표시 | ✅ 반투명 노드 |
| 트레일 3단계 | ✅ "Tech ── AKAM ──RELATED_TO── GDDY" |
| 관계 라벨 | ✅ "RELATED_TO" 텍스트 표시 |
| 관계 카드 갱신 | ✅ GDDY의 RELATED (5) 카드 |

### 5. 트레일 undo (AKAM 노드 탭)

| 항목 | 결과 |
|------|------|
| 트레일 복원 | ✅ "Tech ── AKAM" (GDDY 제거) |
| 그래프 복원 | ✅ AKAM 중심으로 복귀 |
| 관계 카드 복원 | ✅ AKAM의 RELATED (5) 카드 |

### 6. 딥링크 (`/chainsight?focus=SMCI`)

| 항목 | 결과 |
|------|------|
| 섹터 자동 선택 | ✅ Technology (SMCI의 섹터) |
| 중심 자동 설정 | ✅ SMCI 큰 중심 노드 |
| 이웃 로드 | ✅ 8개 (STX, KEYS, HPQ, DELL, WDC, HPE, TER, NTAP) |
| 트레일 자동 생성 | ✅ "Tech ── SMCI" |
| 관계 카드 | ✅ RELATED (8) 카드 |

---

## 테스트 중 발견 및 수정한 이슈

### 핫픽스 1: RelationCardPanel fallback 그룹 추가

**문제**: Neo4j에 저장된 관계 타입이 `RELATED_TO`인데, `RELATION_GROUPS`에 해당 타입이 없어 focused 상태에서 "관계 데이터가 없습니다" 표시됨.

**수정**: `RelationCardPanel.tsx`에 fallback 그룹 추가:
```typescript
// 추가된 그룹
{ key: 'related', label: 'Related', types: ['RELATED_TO', 'HAS_THEME', 'HELD_BY_SAME_FUND'] }

// 추가된 템플릿
RELATED_TO: '관련 종목',
HAS_THEME: '테마 공유',
HELD_BY_SAME_FUND: '동일 펀드 보유',
```

### 핫픽스 2: Neo4j 관계 타입이 모두 RELATED_TO로 표시되는 문제

**원인**: Neo4j에 두 종류의 엣지가 공존함:

| 엣지 라벨 | 생성 경로 | `r.relation_type` 속성 | `r.status` 속성 |
|-----------|----------|----------------------|----------------|
| `PEER_OF` | `load_peers_to_neo4j` (초기 peer 로딩) | 없음 | 없음 |
| `RELATED_TO` | `sync_relations_to_neo4j` (관계 동기화) | `PEER_OF` 등 실제 값 | `confirmed`/`probable` |

API의 `r.status IN ['confirmed', 'probable']` 필터가 속성 없는 `PEER_OF` 엣지를 걸러내고, `RELATED_TO` 엣지만 반환. 이때 `type(r)`은 항상 `RELATED_TO`.

**수정**: `chainsight/api/views.py`의 모든 Neo4j 쿼리(4곳)에서 `type(r)` → `COALESCE(r.relation_type, type(r))` 변경:
```cypher
-- 변경 전
RETURN ... type(r) AS type ...

-- 변경 후
RETURN ... COALESCE(r.relation_type, type(r)) AS type ...
```

- SectorGraphView: 섹터 overview 엣지 쿼리
- NeighborGraphView: 이웃 조회 쿼리 + cross_edges 쿼리
- SignalFeedView: shortestPath 체인 경로 쿼리
- rel_types 필터도 `type(r) IN` → `r.relation_type IN` 으로 변경

**결과**: `RELATED (8)` + `RELATED_TO` 배지 → **`PEERS (8)`** + **`Peer`** 배지 + **"동종 비교 대상"** 으로 정상 표시.

---

## 데이터 품질 이슈 (Chain Sight 범위 밖)

### Stock change_percent 대부분 None

- 전체 532개 종목 중 **24개만** `change_percent`가 존재 (나머지 508개 = None → 0% 표시)
- Stock 모델 docstring에 "Alpha Vantage" 언급은 **레거시 주석** — 실제 코드(`FMPProcessor`, `StockSyncService`)는 FMP 기반
- **원인**: Stock 기본 정보(quote) 동기화 배치가 전체 종목에 대해 정기 실행되지 않고 있음
- **영향**: 관계 카드의 수익률이 대부분 0%, "관계 기반 탐색 후보" fallback 텍스트 표시
- **해결**: Stock 데이터 파이프라인의 전체 종목 quote 동기화 스케줄 점검 필요 (별도 이슈)

---

## 미테스트 항목 (데이터 부족)

| 항목 | 사유 |
|------|------|
| 섹터 재탭 → reset | 수동 확인 가능하나 생략 |
| 체인 스토리 피드 렌더 | signals API가 Neo4j shortestPath 의존, 현재 경로 데이터 부족으로 "체인 시그널이 없습니다" |
| 체인 카드 클릭 → 새 session | 위와 동일 |
| 무한 스크롤 | 위와 동일 |
| truth 관계 엣지 굵기 차등 | 현재 PEER_OF만 존재, SUPPLIES_TO/COMPETES_WITH 등 다양한 관계 타입 필요 |
| 시드 bounce 애니메이션 | 범위 밖 (후속 작업) |
