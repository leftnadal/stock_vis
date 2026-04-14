# Chain Sight 마켓 뷰 — 전체 PR 프롬프트

> **프로젝트**: Stock-Vis Chain Sight 마켓 뷰 (`/chainsight`)  
> **설계서**: `chainsight_seed_node_design.md` (v2.1), `chainsight_api_design.md` (v2.1), `chainsight_ui_ux_design.md` (v2.2)  
> **총 PR**: 7개 (BE 4 + FE 3)  
> **공통 규칙**: 실제 코드베이스의 필드명/모델명이 이 문서와 다르면, **기존 코드 기준으로 맞출 것.** bulk_update 사용 시 `save()` 오버라이드 미작동 주의.

---

## PR 의존성 그래프

```
PR-1 스키마 마이그레이션 (완료)
 ├─→ PR-2 시드 선정 Task
 │    └─→ PR-4 API 4종 (seeds/ 는 PR-2 결과 의존)
 │         ├─→ PR-5 FE: 상태 + 섹터바 + 그래프
 │         │    └─→ PR-6 FE: 트레일 + 관계 카드
 │         └─→ PR-7 FE: 체인 스토리 피드
 └─→ PR-3 Neo4j Sync 개선
```

---

# PR-2: 시드 선정 Celery Task

> **브랜치**: `feat/chainsight-seed-selection-task`  
> **앱**: `chainsight`  
> **선행**: PR-1 (스키마 마이그레이션)

## 목표

Phase 1 시드 선정 로직을 Celery task로 구현한다. 매일 12:00 UTC 실행, 결과를 Redis에 캐싱하여 `seeds/` API가 읽는다.

### 공통 원칙

> ⚠️ **기준일**: `date.today()`를 직접 쓰지 말 것. **시장 기준일(market date)** 헬퍼를 도입하여 미국장 EOD 기준 날짜를 단일 함수로 정의한다. seeds cache key, signal build, fallback 전부 이 함수를 공통 사용할 것.

```python
# chainsight/utils.py
def get_market_date() -> date:
    """미국장 EOD 기준 시장 날짜 반환. 주말/공휴일이면 직전 거래일."""
    ...
```

> ⚠️ **N+1 방지**: 시드/섹터 요약 생성 시 symbol별 개별 `Stock.objects.get()` 반복을 금지한다. **한 번의 bulk query로 Stock 메타데이터를 map**으로 가져와 사용할 것.

```python
stock_map = {s.symbol: s for s in Stock.objects.filter(symbol__in=seed_symbols)}
```

## 작업 1: 시드 선정 함수

```python
# chainsight/services/seed_selection.py

MAX_SEED_NODES = 20
SEED_REASONS = [
    'price_top5', 'price_bottom5', 'volume_surge',
    'sector_outlier', 'relation_upgrade', 'relation_downgrade',
    'relation_new', 'comention_surge'
]
```

### 1-1. 시장 시그널 (B)

```python
def get_price_seeds(date):
    """수익률 상위/하위 2σ 이상치"""
    stats = Stock.objects.aggregate(
        avg=Avg('daily_return'), stddev=StdDev('daily_return')
    )
    upper = stats['avg'] + 2 * stats['stddev']
    lower = stats['avg'] - 2 * stats['stddev']

    top = Stock.objects.filter(daily_return__gte=upper).order_by('-daily_return')[:5]
    bottom = Stock.objects.filter(daily_return__lte=lower).order_by('daily_return')[:5]

    seeds = {}
    for s in top:
        seeds[s.symbol] = {'reasons': ['price_top5'], 'seed_type': 'price'}
    for s in bottom:
        seeds[s.symbol] = {'reasons': ['price_bottom5'], 'seed_type': 'price'}
    return seeds


def get_volume_seeds(date):
    """거래량 / SMA20 >= 2.0"""
    # Stock 모델에 volume, volume_sma20 필드가 있다고 가정.
    # 없으면 EOD 데이터에서 계산하여 annotate.
    qs = Stock.objects.filter(volume__gte=F('volume_sma20') * 2.0)
    return {
        s.symbol: {'reasons': ['volume_surge'], 'seed_type': 'volume'}
        for s in qs
    }


def get_sector_outlier_seeds(date):
    """섹터 평균 대비 ±2σ"""
    # 섹터별 avg/stddev 계산 → 해당 섹터 내 이상치 추출
    # sector_outlier reason 부여
    ...
```

> ⚠️ `daily_return`, `volume`, `volume_sma20` 필드가 Stock 모델에 없을 수 있음. 실제 모델 구조에 맞게 EOD 데이터 테이블에서 JOIN하거나 annotate로 처리할 것. 핵심은 로직이지 필드명이 아님.

### 1-2. 관계 변화 (A)

```python
def get_relation_change_seeds(date):
    """RelationConfidence 상태 전이"""
    yesterday = date - timedelta(days=1)
    changed = RelationConfidence.objects.filter(
        last_observed_at__gte=yesterday
    ).exclude(
        previous_status=F('relation_status')
    ).exclude(
        previous_status=''  # 신규 생성은 전이 아님
    )

    seeds = {}
    for rc in changed:
        for symbol in [rc.symbol_a, rc.symbol_b]:
            if symbol not in seeds:
                seeds[symbol] = {'reasons': [], 'seed_type': 'relation'}
            # 상태 상승이면 upgrade, 하강이면 downgrade
            status_order = ['hidden', 'weak', 'probable', 'confirmed']
            old_idx = status_order.index(rc.previous_status) if rc.previous_status in status_order else -1
            new_idx = status_order.index(rc.relation_status) if rc.relation_status in status_order else -1
            reason = 'relation_upgrade' if new_idx > old_idx else 'relation_downgrade'
            if reason not in seeds[symbol]['reasons']:
                seeds[symbol]['reasons'].append(reason)
    return seeds


def get_comention_surge_seeds(date):
    """CoMention 7일 평균 대비 2배 급증"""
    # CoMentionEdge 모델에서 date=today, count >= count_7d_avg * 2.0
    # 관련 symbol 양쪽 모두 시드 후보
    ...
```

### 1-3. 합산 및 랭킹

```python
def select_seeds(date):
    """전체 시드 소스 합산 → 상위 MAX_SEED_NODES 선정"""
    all_sources = [
        get_price_seeds(date),
        get_volume_seeds(date),
        get_sector_outlier_seeds(date),
        get_relation_change_seeds(date),
        get_comention_surge_seeds(date),
    ]

    # symbol별 reasons 합산 + signal_count 계산
    merged = {}
    for source in all_sources:
        for symbol, info in source.items():
            if symbol not in merged:
                merged[symbol] = {'reasons': [], 'seed_type': info['seed_type']}
            merged[symbol]['reasons'].extend(info['reasons'])
            # seed_type 우선순위: price > volume > relation > comention
            # 여러 소스에 걸치면 가장 강한 타입 유지

    # signal_count = len(reasons), 중복 제거
    for symbol, info in merged.items():
        info['reasons'] = list(set(info['reasons']))
        info['signal_count'] = len(info['reasons'])

    # signal_count DESC 정렬 → 상위 MAX_SEED_NODES
    ranked = sorted(merged.items(), key=lambda x: x[1]['signal_count'], reverse=True)
    return dict(ranked[:MAX_SEED_NODES])
```

### 1-4. seed_type 우선순위

하나의 종목이 여러 소스에 걸칠 때 대표 `seed_type` 결정:

```python
SEED_TYPE_PRIORITY = {'price': 0, 'volume': 1, 'relation': 2, 'comention': 3}

def resolve_seed_type(reasons):
    types = set()
    for r in reasons:
        if r.startswith('price'): types.add('price')
        elif r == 'volume_surge': types.add('volume')
        elif r.startswith('relation') or r == 'relation_new': types.add('relation')
        elif r == 'comention_surge': types.add('comention')
    return min(types, key=lambda t: SEED_TYPE_PRIORITY[t]) if types else 'price'
```

## 작업 2: 섹터 요약 생성

```python
def build_sector_summary(seeds, date):
    """seeds dict → sector_summary 리스트"""
    # bulk query (N+1 방지)
    stock_map = {s.symbol: s for s in Stock.objects.filter(symbol__in=seeds.keys())}

    sector_map = {}
    for symbol, info in seeds.items():
        stock = stock_map.get(symbol)
        if not stock:
            continue
        sector = stock.sector
        if sector not in sector_map:
            sector_map[sector] = {
                'sector': sector,
                'sector_display': sector,
                'pct_change': 0.0,  # 섹터 평균 수익률 — 별도 계산
                'seed_count': 0,
                'heat_total': 0.0,  # Phase 2에서 사용
                'top_seed': None,
            }
        sector_map[sector]['seed_count'] += 1
        # top_seed: signal_count 최대인 종목
        if (sector_map[sector]['top_seed'] is None or
                info['signal_count'] > seeds.get(sector_map[sector]['top_seed'], {}).get('signal_count', 0)):
            sector_map[sector]['top_seed'] = symbol

    # 섹터 평균 수익률 계산
    for sector, summary in sector_map.items():
        avg = Stock.objects.filter(sector=sector).aggregate(avg=Avg('daily_return'))
        summary['pct_change'] = round(avg['avg'] or 0.0, 2)

    # Phase 1 정렬: seed_count DESC
    return sorted(sector_map.values(), key=lambda x: x['seed_count'], reverse=True)
```

## 작업 3: Redis 캐싱

```python
def cache_seed_result(date, sector_summary, seeds_list):
    """시드 결과를 Redis에 캐싱"""
    cache_key = f'chainsight:seeds:{date}'
    payload = {
        'date': str(date),
        'total_seeds': len(seeds_list),
        'sector_summary': sector_summary,
        'seeds': seeds_list,
    }
    cache.set(cache_key, json.dumps(payload), timeout=86400)  # 다음 시드 계산까지
```

## 작업 4: Celery Task

```python
# chainsight/tasks.py

@shared_task(name='chainsight-seed-selection')
def run_seed_selection():
    """매일 12:00 UTC — Phase 1 시드 선정"""
    today = get_market_date()

    seeds = select_seeds(today)

    if not seeds:
        # 시드 부족 시: 전일 시드 유지
        prev_key = f'chainsight:seeds:{today - timedelta(days=1)}'
        prev = cache.get(prev_key)
        if prev:
            cache.set(f'chainsight:seeds:{today}', prev, timeout=86400)
            logger.warning(f'No seeds for {today}, carried over from previous market date')
        return

    # bulk query로 Stock 메타데이터 조회 (N+1 방지)
    seed_symbols = list(seeds.keys())
    stock_map = {s.symbol: s for s in Stock.objects.filter(symbol__in=seed_symbols)}

    seeds_list = []
    for symbol, info in seeds.items():
        stock = stock_map.get(symbol)
        if not stock:
            continue
        seeds_list.append({
            'symbol': symbol,
            'name': stock.name,
            'sector': stock.sector,
            'industry': getattr(stock, 'industry', ''),
            'market_cap': getattr(stock, 'market_cap', 0),
            'daily_return': getattr(stock, 'daily_return', 0.0),
            'volume_ratio': getattr(stock, 'volume_ratio', 0.0),
            'seed_reasons': info['reasons'],
            'seed_type': resolve_seed_type(info['reasons']),
            'signal_count': info['signal_count'],
        })

    sector_summary = build_sector_summary(seeds, today)
    cache_seed_result(today, sector_summary, seeds_list)
    logger.info(f'Seed selection complete: {len(seeds_list)} seeds, {len(sector_summary)} sectors')
```

## 작업 5: Celery Beat 등록

```python
# settings.py 또는 celery beat config
'chainsight-seed-selection': {
    'task': 'chainsight-seed-selection',
    'schedule': crontab(hour=12, minute=0),
},
```

## 검증 체크리스트

```bash
# 1. task 단독 실행
python manage.py shell
>>> from chainsight.tasks import run_seed_selection
>>> run_seed_selection()

# 2. Redis 캐시 확인
>>> from django.core.cache import cache
>>> import json
>>> data = json.loads(cache.get(f'chainsight:seeds:{date.today()}'))
>>> assert data['total_seeds'] > 0
>>> assert len(data['sector_summary']) > 0
>>> assert all('seed_reasons' in s for s in data['seeds'])

# 3. 시드 부족 시 fallback 확인
# (Redis에서 오늘 키 삭제 후 빈 데이터로 실행)

# 4. seed_type 우선순위 확인
>>> from chainsight.services.seed_selection import resolve_seed_type
>>> assert resolve_seed_type(['price_top5', 'volume_surge']) == 'price'
>>> assert resolve_seed_type(['volume_surge', 'comention_surge']) == 'volume'
```

## 범위 밖

- Heat Score 계산 (Phase 2 task) — 별도 PR
- signals/ 체인 생성 로직 — PR-4에서 구현
- 시드 선정 결과의 Neo4j 시드 마킹 — PR-3 범위

---

# PR-3: Neo4j Sync 개선

> **브랜치**: `feat/chainsight-neo4j-dirty-sync`  
> **앱**: `chainsight`  
> **선행**: PR-1 (스키마 마이그레이션)

## 목표

`neo4j_dirty` 플래그 기반 Neo4j 동기화 패턴으로 전환한다. 기존 sync 로직이 있다면 dirty 기반으로 교체.

## 작업 1: Sync Service

```python
# chainsight/services/neo4j_sync.py

from django.utils import timezone
from neo4j import GraphDatabase
from chainsight.models import RelationConfidence

def sync_dirty_relations():
    """neo4j_dirty=True인 RelationConfidence를 Neo4j에 동기화"""
    dirty_qs = RelationConfidence.objects.filter(neo4j_dirty=True)
    count = dirty_qs.count()
    if count == 0:
        return 0

    driver = GraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD))

    synced_pks = []
    try:
        with driver.session() as session:
            for rc in dirty_qs.iterator(chunk_size=100):
                # confirmed/probable만 엣지 생성, hidden/weak/stale는 엣지 삭제
                if rc.relation_status in ('confirmed', 'probable'):
                    _upsert_edge(session, rc)
                else:
                    _delete_edge(session, rc)
                synced_pks.append(rc.pk)
    finally:
        driver.close()

    # ⚠️ 반드시 queryset.update() 사용 — save() 호출 금지 (dirty가 다시 True로 덮어씌워짐)
    if synced_pks:
        RelationConfidence.objects.filter(pk__in=synced_pks).update(
            neo4j_dirty=False,
            neo4j_synced_at=timezone.now()
        )

    return len(synced_pks)


def _upsert_edge(session, rc):
    """Neo4j에 관계 엣지 upsert (apoc.create.relationship 사용)"""
    session.run("""
        MATCH (a:Stock {ticker: $symbol_a})
        MATCH (b:Stock {ticker: $symbol_b})
        CALL apoc.merge.relationship(a, $rel_type, {}, {
            truth_score: $truth_score,
            market_score: $market_score,
            status: $status,
            evidence_tier_best: $evidence_tier_best,
            relation_category: $relation_category
        }, b) YIELD rel
        RETURN rel
    """, symbol_a=rc.symbol_a, symbol_b=rc.symbol_b,
         rel_type=rc.relation_type,
         truth_score=rc.truth_score, market_score=rc.market_score,
         status=rc.relation_status,
         evidence_tier_best=rc.evidence_tier_best,
         relation_category=rc.relation_category)


def _delete_edge(session, rc):
    """Neo4j에서 관계 엣지 삭제"""
    session.run("""
        MATCH (a:Stock {ticker: $symbol_a})-[r]->(b:Stock {ticker: $symbol_b})
        WHERE type(r) = $rel_type
        DELETE r
    """, symbol_a=rc.symbol_a, symbol_b=rc.symbol_b, rel_type=rc.relation_type)
```

> ⚠️ `apoc.merge.relationship` 사용 전 APOC 플러그인 설치 확인. 없으면 `MERGE` + `SET`으로 대체.

> ⚠️ **저장 규약 우선**: 위 Cypher 예시는 개념 예시임. 실제 프로젝트의 relation 저장 전략(undirected canonicalized / directed single edge)에 맞춰 구현할 것. undirected 관계(`PEER_OF`, `COMPETES_WITH`, `CO_MENTIONED`, `PRICE_CORRELATED`)는 `symbol_a < symbol_b` 정규화 기준으로 한 방향만 저장되므로, delete/upsert 시 정규화된 방향만 처리하면 됨. 저장 규약과 예시 Cypher가 불일치하면 **저장 규약을 우선**한다.

## 작업 2: Celery Task

```python
@shared_task(name='chainsight-neo4j-sync')
def run_neo4j_sync():
    """neo4j_dirty=True 레코드를 Neo4j에 동기화"""
    count = sync_dirty_relations()
    logger.info(f'Neo4j sync complete: {count} relations synced')
    return count
```

## 작업 3: Celery Beat 등록

```python
'chainsight-neo4j-sync': {
    'task': 'chainsight-neo4j-sync',
    'schedule': crontab(hour=4, minute=30, day_of_week=0),  # 매주 일요일 04:30
},
```

> 시드 선정(12:00) 전에 실행되어야 graph 데이터가 최신. 주간이면 충분하지만, 필요시 일간으로 조정.

## 작업 4: CompanyChainProfile 동일 패턴 적용 검토

CompanyChainProfile에도 `synced_to_neo4j` → `neo4j_dirty` 교체가 필요하다면 이 PR에서 함께 처리. 동일한 3-step 마이그레이션 패턴.

## 검증 체크리스트

```bash
# 1. dirty 레코드 생성 확인
python manage.py shell
>>> rc = RelationConfidence.objects.first()
>>> rc.relation_status = 'confirmed'
>>> rc.save()
>>> rc.refresh_from_db()
>>> assert rc.neo4j_dirty == True

# 2. sync 실행
>>> from chainsight.services.neo4j_sync import sync_dirty_relations
>>> count = sync_dirty_relations()
>>> print(f'Synced: {count}')

# 3. sync 후 dirty=False 확인
>>> rc.refresh_from_db()
>>> assert rc.neo4j_dirty == False
>>> assert rc.neo4j_synced_at is not None

# 4. Neo4j에서 엣지 확인
# MATCH (a:Stock)-[r]->(b:Stock) WHERE a.ticker = '{symbol}' RETURN r
```

## 범위 밖

- 시드 노드 마킹 (Neo4j 노드에 `is_seed` 속성 세팅) — seeds API에서 동적 처리
- Graph Data Science (PageRank, Louvain) — Phase 2+ 별도 PR

---

# PR-4: 마켓 뷰 API 4종

> **브랜치**: `feat/chainsight-market-view-api`  
> **앱**: `chainsight`  
> **선행**: PR-2 (시드 선정 task — seeds/ API의 데이터 소스)

## 목표

마켓 뷰 UI를 구동하는 4개 API 엔드포인트 구현. 설계서 `chainsight_api_design.md` v2.1 FINAL 기준.

## 공통

```python
# chainsight/urls.py — 기존 urlpatterns에 마켓 뷰 추가
urlpatterns = [
    # 마켓 뷰
    path('seeds/', views.SeedListView.as_view()),
    path('sector/<str:sector>/graph/', views.SectorGraphView.as_view()),
    path('<str:symbol>/neighbors/', views.NeighborGraphView.as_view()),
    path('signals/', views.SignalFeedView.as_view()),
    # Deep dive workspace (기존 유지)
    path('<str:symbol>/graph/', views.ChainSightGraphView.as_view()),
    path('<str:symbol>/suggestions/', views.ChainSightSuggestionView.as_view()),
    path('trace/', views.ChainSightTraceView.as_view()),
]
```

> ⚠️ URL 순서 주의: `<str:symbol>/neighbors/`가 `<str:symbol>/graph/`보다 앞에 오면 안 됨. `seeds/`, `sector/`, `signals/` 고정 경로를 먼저 배치하고, `<str:symbol>/` 동적 경로를 뒤에 배치.

## 작업 1: GET /seeds/

```python
# chainsight/views.py

class SeedListView(APIView):
    """
    오늘의 시드 전체 + 섹터 요약.
    Redis 캐시에서 읽기 전용.
    """
    def get(self, request):
        today = date.today()
        cache_key = f'chainsight:seeds:{today}'
        cached = cache.get(cache_key)

        if cached:
            return Response(json.loads(cached))

        # 캐시 미스 시: 전일 fallback
        yesterday = today - timedelta(days=1)
        cached = cache.get(f'chainsight:seeds:{yesterday}')
        if cached:
            return Response(json.loads(cached))

        return Response({'date': str(today), 'total_seeds': 0, 'sector_summary': [], 'seeds': []})
```

**응답 스키마**: `chainsight_api_design.md` §2 참조. `sector_summary[]`, `seeds[]` 구조 그대로.

## 작업 2: GET /sector/{sector}/graph/

```python
class SectorGraphView(APIView):
    """
    섹터 overview graph — 탐색 시작점 선택용 구조 파악.
    Neo4j에서 해당 섹터 Stock 노드 + 관계 조회.
    """
    def get(self, request, sector):
        limit = int(request.query_params.get('limit', 12))

        cache_key = f'chainsight:sector_graph:{sector}:{date.today()}:{limit}'
        cached = cache.get(cache_key)
        if cached:
            return Response(json.loads(cached))

        # 오늘의 시드 목록 (is_seed 판단용)
        seeds_data = self._get_today_seeds()

        # Neo4j 쿼리: 섹터 내 market cap 상위 노드 + 관계
        nodes, edges = self._query_sector_graph(sector, limit, seeds_data)

        response = {
            'sector': sector,
            'node_count': len(nodes),
            'edge_count': len(edges),
            'nodes': nodes,
            'edges': edges,
        }

        cache.set(cache_key, json.dumps(response), timeout=3600)  # 1시간
        return Response(response)

    def _query_sector_graph(self, sector, limit, seeds_data):
        """Neo4j에서 섹터 내 주요 종목 + 관계 조회"""
        # 1. market_cap 상위 limit개 노드
        # 2. 해당 노드 간 관계 (confirmed + probable)
        # 3. node_size: xl(상위10%) / lg(10~30%) / md(30~60%) / sm(나머지)
        # 4. is_seed, seed_type, seed_reasons: seeds_data에서 매칭
        ...
```

**nodes[] 스키마**: symbol, name, sector, industry, market_cap, daily_return, volume_ratio, is_seed, seed_type, seed_reasons, node_size.

**edges[] 스키마**: source, target, type, relation_category(truth/market), truth_score(market은 null), market_score, status.

**node_size 계산**: market_cap 기준 percentile — xl(상위10%), lg(10~30%), md(30~60%), sm(나머지).

**엣지 굵기 규칙**: 프론트에서 `truth_score != null ? scale(truth_score) : 1`.

## 작업 3: GET /{symbol}/neighbors/

```python
class NeighborGraphView(APIView):
    """
    마켓 뷰 탐색 핵심 API.
    중심 이동 + 관계 카드 패널 렌더 데이터.
    < 200ms (p95) 목표.
    """
    def get(self, request, symbol):
        limit = int(request.query_params.get('limit', 8))
        rel_types = request.query_params.get('rel_types', 'all')
        min_truth_score = int(request.query_params.get('min_truth_score', 35))

        cache_key = f'chainsight:neighbors:{symbol}:{date.today()}:{limit}:{rel_types}'
        cached = cache.get(cache_key)
        if cached:
            return Response(json.loads(cached))

        seeds_data = self._get_today_seeds()

        center = self._build_center(symbol, seeds_data)
        if not center:
            return Response({'error': f'Stock {symbol} not found'}, status=404)

        neighbors, cross_edges, total = self._query_neighbors(
            symbol, limit, rel_types, min_truth_score, seeds_data
        )

        response = {
            'center': center,
            'neighbors': neighbors,
            'cross_edges': cross_edges,
            'total_neighbor_count': total,
            'returned_count': len(neighbors),
            'truncated': total > len(neighbors),
        }

        cache.set(cache_key, json.dumps(response), timeout=1800)  # 30분
        return Response(response)
```

### Neo4j 쿼리

```cypher
MATCH (center:Stock {ticker: $symbol})-[r]->(neighbor:Stock)
WHERE type(r) IN $rel_types
  AND r.status IN ['confirmed', 'probable']
  AND (r.truth_score >= $min_truth_score OR r.truth_score IS NULL)
RETURN neighbor.ticker, type(r), r.truth_score, r.market_score,
       r.status, r.evidence_tier_best, 'outbound' as direction
UNION
MATCH (neighbor:Stock)-[r]->(center:Stock {ticker: $symbol})
WHERE type(r) IN $rel_types
  AND r.status IN ['confirmed', 'probable']
  AND (r.truth_score >= $min_truth_score OR r.truth_score IS NULL)
RETURN neighbor.ticker, type(r), r.truth_score, r.market_score,
       r.status, r.evidence_tier_best, 'inbound' as direction
```

> `rel_types=all`이면 WHERE 절의 type(r) 필터 제거.

### display_type 파생

```python
@staticmethod
def _derive_display_type(rel_type, direction):
    if rel_type == 'SUPPLIES_TO' and direction == 'outbound':
        return 'CUSTOMER_OF'
    return rel_type
```

### neighbors[] 정렬

1. `is_seed = true` 우선
2. `(truth_score ?? market_score ?? 0)` DESC
3. `market_cap` DESC

### cross_edges

이웃 노드 간 관계. 그래프 렌더링용. `neighbors` 결과의 symbol 집합으로 2차 쿼리.

```cypher
MATCH (a:Stock)-[r]->(b:Stock)
WHERE a.ticker IN $neighbor_symbols
  AND b.ticker IN $neighbor_symbols
  AND r.status IN ['confirmed', 'probable']
RETURN a.ticker, b.ticker, type(r), r.truth_score
```

## 작업 4: GET /signals/

```python
class SignalFeedView(APIView):
    """
    글로벌 chain flow + 새 chain 추천.
    현재 탐색 상태와 무관한 global feed.
    """
    def get(self, request):
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 5))
        sector = request.query_params.get('sector', None)

        cache_key = f'chainsight:signals:{date.today()}:{page}:{sector}'
        cached = cache.get(cache_key)
        if cached:
            return Response(json.loads(cached))

        chains = self._build_chain_signals(page, page_size, sector)

        response = {
            'date': str(date.today()),
            'page': page,
            'page_size': page_size,
            'total_count': chains['total'],
            'has_next': chains['has_next'],
            'chains': chains['items'],
        }

        cache.set(cache_key, json.dumps(response), timeout=3600)
        return Response(response)
```

### 체인 구성 로직

```python
def _build_chain_signals(self, page, page_size, sector):
    """
    시드 노드 간 Neo4j 경로 탐색 → 체인 구성.

    Phase 1 로직:
    1. 오늘 시드 목록에서 같은 섹터/industry 시드 페어 추출
    2. Neo4j shortestPath로 경로 탐색
    3. 경로 내 truth_score 평균 → total_confidence
    4. strength 판정: strong(>=70) / moderate(40~69) / weak(<40)
    5. trigger_summary: 시드 reason 기반 자동 생성
    """
    ...
```

### 체인 구성 규칙 (반드시 준수)

| 규칙                      | 값                                                                                          |
| ------------------------- | ------------------------------------------------------------------------------------------- |
| **max hop**               | 3 (노드 4개까지)                                                                            |
| **동일 노드 반복**        | 금지                                                                                        |
| **관계 타입 우선순위**    | truth 관계 우선. market 관계는 truth 경로가 없을 때만 보조 허용                             |
| **total_confidence 계산** | 경로 내 `truth_score ?? market_score` 값들의 **최솟값 보정 평균**: `mean * 0.7 + min * 0.3` |
| **동일 시작/끝 조합**     | 중복 제거 (첫 발견 체인만 유지)                                                             |
| **내부 후보 생성**        | `page_size * 3`개 후보 생성 → `total_confidence DESC` 정렬 → 상위 잘라서 페이지네이션       |
| **최소 confidence**       | `total_confidence < 30`인 체인은 제외                                                       |

````

**chains[] 스키마**: `chainsight_api_design.md` §5 참조. **추가 필드**: 각 chain에 `root_sector` (첫 노드의 섹터) 포함할 것. FE에서 섹터 추론 없이 바로 사용.

**chain.id 형식**: `chain_{date}_{seq:03d}` (예: `chain_20260409_001`)

## 작업 5: 에러 응답

| 코드 | 상황 | 응답 |
|---|---|---|
| 400 | 잘못된 파라미터 (limit < 1, sector 형식 등) | `{"error": "Invalid parameter: ..."}` |
| 404 | 종목/섹터 없음 | `{"error": "Stock XXXX not found"}` |
| 503 | Neo4j 불가 | `{"error": "Graph service unavailable"}` |

Neo4j 연결 실패 시 503으로 graceful degradation. seeds/ API는 Neo4j 불필요 (Redis 전용).

## 검증 체크리스트

```bash
# 1. seeds API (PR-2 task 실행 후)
curl localhost:8000/api/v1/chainsight/seeds/ | jq '.total_seeds'
# 기대: > 0

# 2. sector graph
curl localhost:8000/api/v1/chainsight/sector/Technology/graph/?limit=10 | jq '.node_count'

# 3. neighbors (핵심 — 200ms 이내)
time curl localhost:8000/api/v1/chainsight/NVDA/neighbors/?limit=8 | jq '.returned_count'
# 응답시간 200ms 이내 확인

# 4. neighbors display_type 파생 확인
curl ... | jq '.neighbors[] | select(.relation.type == "SUPPLIES_TO" and .relation.direction == "outbound") | .relation.display_type'
# 기대: "CUSTOMER_OF"

# 5. signals
curl localhost:8000/api/v1/chainsight/signals/?page=1 | jq '.chains | length'

# 6. 에러 케이스
curl localhost:8000/api/v1/chainsight/INVALID_SYMBOL/neighbors/
# 기대: 404
````

## 범위 밖

- Serializer 클래스 분리 — 이 PR에서는 View 내에서 직접 dict 구성. 안정화 후 분리 가능.
- 2차 필드 확장 (`relation_summary`, `why_now`, `insight_summary`) — Future enhancement
- signals 체인의 LLM 기반 title/summary 생성 — Future enhancement

---

# PR-5: 탐색 상태 + 섹터 바 + 그래프 캔버스

> **브랜치**: `feat/chainsight-market-view-core-ui`  
> **선행**: PR-4 (API 4종)

## 목표

마켓 뷰 페이지 골격 + 공유 탐색 상태 + ① 섹터 바 + ② 그래프 캔버스 구현.

## 작업 1: 공유 탐색 상태

```typescript
// hooks/useExplorationState.ts

interface TrailNode {
	symbol: string;
	type: "sector" | "stock";
	depth: number;
	relation_from_prev?: string;
	seed_type?: "price" | "volume" | "relation" | null;
}

interface ExplorationState {
	selectedSector: string | null;
	centerSymbol: string | null;
	trail: TrailNode[];
	historyNodes: string[]; // 좌측 히스토리 (최근 3개)
	currentNeighbors: Neighbor[];
	selectedRelationGroup: string | null;
	highlightedChain: string | null;
}

// Zustand 또는 useReducer로 구현.
// 핵심 action:
// - selectSector(sector) → ② overview graph + ④ pre-focus + ③ trail 초기화
// - selectNode(symbol) → ② 중심 이동 + ③ 트레일 확장 + ④ focused
// - undoToTrailNode(depth) → 해당 시점 복원 (②③④ + 히스토리)
// - startChainExploration(symbol) → trail 리셋 + 새 exploration session
// - initializeFocusExploration(sector, symbol) → ?focus= 딥링크 전용. sector+center를 원자적 설정
// - reset() → 전체 초기화
```

**상태 전이 규칙 (설계서 기준)**:

| 동작                  | centerSymbol        | trail                              | historyNodes                |
| --------------------- | ------------------- | ---------------------------------- | --------------------------- |
| selectSector          | null                | `[{type:'sector', symbol:sector}]` | []                          |
| selectNode            | symbol              | push 새 노드                       | unshift 이전 center (max 3) |
| undoToTrailNode       | trail[depth].symbol | trail.slice(0, depth+1)            | 복원                        |
| startChainExploration | chain[0]            | 리셋 → `[sector, chain[0]]`        | []                          |

## 작업 2: API 훅

```typescript
// hooks/useSeedData.ts
// React Query: GET /api/v1/chainsight/seeds/
// staleTime: 30분
// 페이지 진입 시 1회 호출. 전체 seeds global preload.

// hooks/useSectorGraph.ts
// React Query: GET /api/v1/chainsight/sector/{sector}/graph/?limit=12
// staleTime: 30분
// enabled: !!selectedSector

// hooks/useNeighbors.ts
// React Query: GET /api/v1/chainsight/{symbol}/neighbors/?limit=8
// staleTime: 5분
// enabled: !!centerSymbol
```

## 작업 3: 페이지 골격

```typescript
// app/chainsight/page.tsx

export default function ChainSightPage() {
  // URL param: ?focus=NVDA → 자동 섹터 선택 + 중심 설정
  const searchParams = useSearchParams();
  const focusSymbol = searchParams.get('focus');

  const { data: seedData } = useSeedData();
  const state = useExplorationState();

  // ?focus=NVDA 처리: 전용 초기화 액션 사용
  // selectSector() + selectNode()를 직렬 호출하면 상태 전이 순서가 꼬일 수 있으므로,
  // 전용 액션으로 sector 설정 + center 설정 + trail 초기화를 원자적으로 처리한다.
  useEffect(() => {
    if (focusSymbol && seedData) {
      const stock = seedData.seeds.find(s => s.symbol === focusSymbol);
      if (stock) {
        state.initializeFocusExploration(stock.sector, focusSymbol);
      }
    }
  }, [focusSymbol, seedData]);

  return (
    <>
      <SectorBar />
      <MarketGraphCanvas />
      <ExplorationTrail />     {/* PR-6 */}
      <RelationCardPanel />    {/* PR-6 */}
      <ChainStoryFeed />       {/* PR-7 */}
    </>
  );
}
```

## 작업 4: ① 섹터 버튼 바

```typescript
// components/chainsight/SectorBar.tsx

// 데이터: seedData.sector_summary
// 레이아웃: 가로 스크롤 flex
// 버튼: 섹터명 + pct_change (상승=#A32D2D, 하락=#185FA5)
// 선택 상태: info 배경 + info 보더
// 정렬: Phase 1 = seed_count DESC
// 탭 → state.selectSector(sector)
// 재탭 → state.reset()
```

## 작업 5: ② 그래프 캔버스

```typescript
// components/chainsight/MarketGraphCanvas.tsx

// 라이브러리: D3 force 또는 react-force-graph (기존 Deep dive와 동일)
// 성능 제약: 동시 노드 20 / 엣지 40 / bounce 3 / 중심이동 300ms / 초기렌더 500ms
```

### 데이터 소스 분기

| 상태                            | 데이터                   | 렌더           |
| ------------------------------- | ------------------------ | -------------- |
| selectedSector && !centerSymbol | `useSectorGraph(sector)` | overview graph |
| centerSymbol                    | `useNeighbors(symbol)`   | center + 이웃  |

### 노드 디자인

| 조건            | 배경                 | 보더             |
| --------------- | -------------------- | ---------------- |
| 기본            | background-secondary | border-secondary |
| 시드 (price)    | #FCEBEB              | #E24B4A          |
| 시드 (volume)   | #E1F5EE              | #1D9E75          |
| 시드 (relation) | #E6F1FB              | #378ADD          |
| 중심 노드       | 해당 색상            | 2.5px 보더       |
| 히스토리        | tertiary             | opacity 0.3~0.5  |

### 엣지 디자인

**Truth 관계** (truth_score 비례 굵기):

| 타입          | 색상    | 스타일     | 굵기  |
| ------------- | ------- | ---------- | ----- |
| SUPPLIES_TO   | #5DCAA5 | 실선       | 2~3px |
| COMPETES_WITH | #F0997B | 실선       | 2px   |
| PEER_OF       | #85B7EB | 점선 (4,3) | 1.5px |

**Market 관계** (truth_score=null, 고정 1px):

| 타입             | 색상    | 스타일     |
| ---------------- | ------- | ---------- |
| CO_MENTIONED     | #AFA9EC | 점선 (2,4) |
| PRICE_CORRELATED | #D3D1C7 | 점선 (3,3) |

### 전환 애니메이션

| 동작                | 애니메이션                          |
| ------------------- | ----------------------------------- |
| 이전 중심 → 왼쪽    | translateX(-) + opacity 0.45, 300ms |
| 새 중심 → 중앙      | 300ms ease-out + 크기 확대          |
| 새 이웃 → 페이드 인 | opacity 0→1, 300ms delay 100ms      |
| 시드 노드           | bounce (시드만)                     |

### 좌측 히스토리

그래프 캔버스 **내부**에서 최근 1~3 step 노드를 흐려진 상태(opacity 0.3~0.5)로 유지. 클릭 시 해당 시점으로 undo.

### 노드 클릭

**항상 in-place 중심 이동.** Deep dive workspace 자동 이동 없음.

```typescript
onNodeClick={(symbol) => state.selectNode(symbol)}
// → useNeighbors(symbol) 트리거
// → ②③④ + 히스토리 동시 갱신
```

## 작업 6: 메인 내비게이션

메인 내비에 Chain Sight 독립 탑레벨 추가.

```
[Dashboard] [Chain Sight*] [Screening] [Thesis]
```

## 작업 7: 종목 상세 연결 변경

```typescript
// app/stocks/[symbol]/page.tsx
// Chain Sight 탭 제거 → 딥링크 추가
// "Chain Sight에서 보기" 버튼 → /chainsight?focus={symbol}
```

## 검증 체크리스트

```
1. /chainsight 진입 → 빈 캔버스 + "섹터를 선택하세요" 안내
2. 섹터 탭 → overview graph 렌더 (500ms 이내)
3. 섹터 재탭 → 전체 리셋
4. 노드 클릭 → 중심 이동 애니메이션 (300ms)
5. 좌측 히스토리 최대 3개 표시
6. ?focus=NVDA → 자동 섹터 선택 + NVDA 중심
7. 시드 노드 bounce 애니메이션
8. 엣지 굵기: truth 관계 score 비례, market 관계 1px 고정
```

## 범위 밖

- ExplorationTrail, RelationCardPanel → PR-6
- ChainStoryFeed → PR-7
- 모바일 대응 — Future consideration

---

# PR-6: 트레일 + 관계 카드 패널

> **브랜치**: `feat/chainsight-trail-and-cards`  
> **선행**: PR-5 (탐색 상태 + 그래프)

## 목표

③ 탐색 트레일 + ④ 관계 카드 패널 (pre-focus/focused 분기) 구현.

## 작업 1: ③ 탐색 트레일

```typescript
// components/chainsight/ExplorationTrail.tsx

// 위치: 그래프 바로 아래
// 높이: 60px
// 노드 크기: 과거 r=12, 현재 r=18
// 노드 간격: 120px
// 엣지 라벨: 관계 타입 텍스트
// 자동 스크롤: 새 노드 추가 시 오른쪽 끝, 300ms

// 구조:
// [← 스크롤] ○Tech ──peer── ○AAPL ──supply── ●NVDA [스크롤 →]
//             depth 0        depth 1           depth 2 (current)
```

### TrailNode 렌더

```typescript
interface TrailNodeProps {
	node: TrailNode;
	isCurrent: boolean;
	onClick: () => void; // → state.undoToTrailNode(depth)
}

// 과거 노드: ○ (빈 원), 작은 크기
// 현재 노드: ● (채운 원), 큰 크기
// 엣지 라벨: relation_from_prev 텍스트 (PEER_OF → "peer", SUPPLIES_TO → "supply" 등)
```

### 인터랙션

| 동작           | 결과                                               |
| -------------- | -------------------------------------------------- |
| 트레일 노드 탭 | 해당 시점으로 undo — ②③④ + 좌측 히스토리 모두 복원 |
| 좌우 스와이프  | 경로 탐색 (가로 스크롤)                            |

## 작업 2: ④ 관계 카드 패널

```typescript
// components/chainsight/RelationCardPanel.tsx

// 위치: ③ 트레일 아래, ⑤ 체인 스토리 피드 위
// 두 가지 상태:
//   centerSymbol == null → <SeedCardList /> (pre-focus)
//   centerSymbol != null → <RelationCardGroups /> (focused)
```

### 페이지 진입 시 (centerSymbol == null, selectedSector == null)

```typescript
// empty state 표시
<EmptyState message="섹터를 선택하면 대표 시드 카드가 표시됩니다" />
```

### Pre-focus: 대표 시드 카드

```typescript
// components/chainsight/SeedCard.tsx

// 데이터: seedData.seeds.filter(s => s.sector === selectedSector)
// 카드 구성:
//   - symbol + name + seed_type badge
//   - 시드 사유 (seed_reasons 기반 프론트 템플릿)
//   - daily_return + volume_ratio
//   - CTA: "여기서 탐색" → state.selectNode(symbol)
```

### Focused: 관계 카드

```typescript
// components/chainsight/RelationCard.tsx

// 데이터: useNeighbors(centerSymbol).neighbors
// display_type 기준 그룹핑:
```

| 그룹             | display_type                          |
| ---------------- | ------------------------------------- |
| **Supply Chain** | SUPPLIES_TO, CUSTOMER_OF (badge 구분) |
| **Competitors**  | COMPETES_WITH                         |
| **Peers**        | PEER_OF                               |
| **Co-mentioned** | CO_MENTIONED, PRICE_CORRELATED        |

### 카드 1장 구성

| 영역   | 내용                                              |
| ------ | ------------------------------------------------- |
| 상단   | symbol + name                                     |
| 관계   | display_type badge + 관계 설명 한 줄 (1차 템플릿) |
| 시그널 | why now (seed_reasons 기반) + signal badge        |
| 메타   | confidence (truth_score ?? market_score)          |
| CTA    | **여기서 탐색** / **가설 생성** / **Deep dive**   |

### 1차 템플릿 규칙 (관계 설명)

```typescript
const RELATION_TEMPLATES: Record<string, string> = {
	SUPPLIES_TO: "공급망 상류/하류 연결",
	CUSTOMER_OF: "공급망 상류/하류 연결",
	COMPETES_WITH: "직접 경쟁 관계",
	PEER_OF: "동종 비교 대상",
	CO_MENTIONED: "최근 시장/뉴스에서 동시 해석",
	PRICE_CORRELATED: "가격 움직임 유사",
};

// why now line: seed_reasons 우선 + daily_return/volume_ratio 보조
function buildWhyNow(neighbor: Neighbor): string {
	if (neighbor.seed_reasons?.length > 0) {
		// seed_reasons 코드 → 한글 매핑
		return neighbor.seed_reasons.map((r) => REASON_LABELS[r]).join(", ");
	}
	if (Math.abs(neighbor.daily_return) > 3)
		return `수익률 ${neighbor.daily_return > 0 ? "+" : ""}${neighbor.daily_return}%`;
	if (neighbor.volume_ratio > 2)
		return `거래량 ${neighbor.volume_ratio.toFixed(1)}배`;
	return "관계 기반 탐색 후보"; // fallback — 빈 문자열 대신 low-info 문구
}
```

### CTA 동작

| CTA         | 동작                                                         |
| ----------- | ------------------------------------------------------------ |
| 여기서 탐색 | `state.selectNode(symbol)` → ②③④ + 히스토리 동시 갱신        |
| 가설 생성   | `router.push('/thesis/new?symbol={symbol}&from=chainsight')` |
| Deep dive   | `router.push('/chainsight/{symbol}')`                        |

### 정렬

1. `is_seed = true` 우선
2. `(truth_score ?? market_score ?? 0)` DESC
3. `market_cap` DESC

## 검증 체크리스트

```
1. 페이지 진입 → ④ empty state ("섹터를 선택하면...")
2. 섹터 선택 → ③ trail에 ○{sector} 표시 + ④ 대표 시드 카드
3. 노드 클릭 → ③ 트레일 확장 + ④ 관계 카드 (focused)
4. 트레일 노드 탭 → undo (②③④ 동시 복원)
5. 관계 카드 그룹핑 (Supply Chain / Competitors / Peers / Co-mentioned)
6. CUSTOMER_OF badge 표시 (Supply Chain 그룹 내)
7. CTA "여기서 탐색" → 중심 이동
8. CTA "Deep dive" → /chainsight/[symbol] 이동
9. 카드 관계 설명 템플릿 정확한 문구
10. 가로 스크롤 + 자동 스크롤 (새 노드 추가 시)
```

## 범위 밖

- 2차 카드 설명 (API `relation_summary`, `why_now`, `insight_summary`) — BE API 확장 후
- LLM 기반 explanation — Future enhancement

---

# PR-7: 체인 스토리 피드

> **브랜치**: `feat/chainsight-chain-story-feed`  
> **선행**: PR-5 (탐색 상태)

## 목표

⑤ 체인 스토리 피드 구현. 마켓 뷰 하단의 글로벌 chain flow + discovery 영역.

## 작업 1: API 훅

```typescript
// hooks/useSignalFeed.ts
// React Query: GET /api/v1/chainsight/signals/?page={page}
// staleTime: 30분
// 무한 스크롤: has_next 기반 fetchNextPage
```

## 작업 2: ⑤ 체인 스토리 피드

```typescript
// components/chainsight/ChainStoryFeed.tsx

// 위치: ④ 관계 카드 패널 아래 (최하단)
// ④와의 구분: ④ = 로컬 (center 기준), ⑤ = 글로벌 (시장 전체)
// 무한 스크롤: 페이지네이션
```

## 작업 3: 체인 스토리 카드

```typescript
// components/chainsight/ChainStoryCard.tsx

// 카드 구성:
//   - title (체인 제목)
//   - category badge
//   - strength 표시: strong(>=70) / moderate(40~69) / weak(<40)
//     strong = 초록, moderate = 주황, weak = 회색
//   - path 시각화: 종목 아이콘 → 관계 화살표 → 종목 아이콘 (mini trail)
//   - trigger_summary
//   - total_confidence 수치
```

### 클릭 동작

체인 스토리 카드 클릭은 **새 exploration session 시작**. 기존 trail과 history 리셋.

```typescript
onChainCardClick={(chain) => {
  const firstSymbol = chain.path[0].symbol;
  const sector = chain.root_sector;  // API에서 제공 — FE 추론 불필요

  state.selectSector(sector);             // ① 섹터 바 자동 선택
  state.startChainExploration(firstSymbol); // trail 리셋 + 새 시작
  // → useNeighbors(firstSymbol) 트리거
  // → ② 그래프에 chain path highlight
  // → ③ 트레일: ○{sector} ── ●{firstSymbol}
  // → ④ 관계 카드 패널: focused state
}}
```

### chain path highlight

그래프 캔버스에 `highlightedChain` 상태로 chain path의 노드/엣지를 강조 표시. 강조 스타일:

```css
/* highlighted path */
.chain-highlight-node {
	stroke-width: 3px;
	filter: drop-shadow(0 0 4px currentColor);
}
.chain-highlight-edge {
	stroke-width: 3px;
	opacity: 1;
}
/* non-highlighted (dimmed) */
.chain-dim {
	opacity: 0.2;
}
```

## 검증 체크리스트

```
1. 페이지 하단에 체인 스토리 피드 렌더
2. 카드에 title, strength badge, mini path, trigger_summary 표시
3. strength 색상: strong=초록, moderate=주황, weak=회색
4. 카드 클릭 → 새 exploration session (trail 리셋 확인)
5. 카드 클릭 → 섹터 바 자동 선택
6. 카드 클릭 → 그래프에 chain path highlight
7. 무한 스크롤 (has_next=true일 때 다음 페이지 로드)
8. ④ 관계 카드와 독립적 동작 (글로벌 vs 로컬)
```

## 범위 밖

- 현재 트레일 해석 — Future enhancement
- chain path 전체를 트레일에 preload — Future enhancement
- 개인화된 chain 추천 — Phase 2+

---

# 부록: 전체 검증 E2E 시나리오

```
1. /chainsight 진입
   → ① 섹터 바 렌더 (seed_count 순 정렬)
   → ② 빈 캔버스 + 안내
   → ④ empty state ("섹터를 선택하면...")
   → ⑤ 체인 스토리 피드 로드

2. Technology 섹터 탭
   → ② overview graph (market cap 상위 노드 + 관계선)
   → ③ trail: ○Tech
   → ④ 대표 시드 카드 (Technology 시드 필터)

3. NVDA 노드 클릭 (그래프 또는 카드 "여기서 탐색")
   → ② 중심 이동 (NVDA 중앙, 300ms 애니메이션)
   → ③ trail: ○Tech ── ●NVDA
   → ④ 관계 카드 (Supply Chain / Competitors / Peers / Co-mentioned 그룹)
   → 좌측 히스토리: 없음 (첫 노드)

4. TSM 관계 카드 "여기서 탐색"
   → ② 중심 이동 (TSM 중앙, NVDA → 좌측 히스토리)
   → ③ trail: ○Tech ── ○NVDA ──supply── ●TSM
   → ④ TSM neighbors 관계 카드
   → 좌측 히스토리: NVDA (opacity 0.45)

5. ③ 트레일에서 ○NVDA 탭
   → undo: ② NVDA 중심 복원, ③ trail: ○Tech ── ●NVDA, ④ NVDA 관계 카드

6. ⑤ 체인 스토리 카드 클릭
   → 기존 탐색 리셋
   → 새 exploration session 시작
   → ② chain 첫 노드 중심 + path highlight
   → ③ trail: ○{sector} ── ●{첫노드}

7. /chainsight?focus=AAPL
   → 자동 섹터 선택 + AAPL 중심 + 관계 카드 focused
```
