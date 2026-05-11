# CS-6-3: Summary path 생성

> **작업 번호**: CS-6-3
> **목표**: 5+ 노드의 긴 경로를 3~4개 landmark로 압축한 summary_path 생성 로직 구현. Watch 시점 + Recheck 시점에 사용.
> **예상 소요**: 1~2일
> **선행 조건**: CS-6-1 (SavedPath 모델), CS-3-3 (GDS 결과 → Neo4j 속성)
> **산출물**:
> - `chainsight/services/path_service.py`에 `generate_summary_path()` 추가
> - `compute_landmark_score()` 헬퍼
> - WatchlistViewSet.create()에서 호출

---

## 배경

Path Watchlist 카드는 좁은 공간에 경로를 보여줘야 한다. `NVDA → TSM → ASML → AMAT → LRCX → KLAC → MU` 같은 7개 노드를 전부 표시하면 가독성이 떨어진다. 대신 landmark 역할을 하는 3~4개 노드만 골라 `NVDA → TSM → AMAT (+4)` 형태로 압축한다.

**선정 기준**: 경로 내에서 "대표성"이 높은 노드. PageRank (전체 그래프에서의 중요도), betweenness (다리 역할), bridge_score (경로 안에서의 위치적 중요도), 섹터 대표성 등을 종합.

---

## 규칙

```
if len(path_nodes) <= 4:
    summary_path = path_nodes  # 그대로

if len(path_nodes) >= 5:
    summary_path = 시작 노드 + landmark 2~3개 + 끝 노드
    # 중간 노드(path_nodes[1:-1])에서 landmark_score 상위 N개 선택
    # 순서는 원본 경로 순서 유지
```

**시작/끝 노드는 항상 포함**. 이유: 사용자 의도(A에서 시작해서 B로 간 경로)를 잃지 않기 위함.

**중간 landmark 수**:
- 5~6 노드: landmark 1개 (총 3개 표시)
- 7~8 노드: landmark 2개 (총 4개 표시)
- 9~10 노드: landmark 2개 (총 4개 표시, +N 표시로 압축도 전달)

---

## landmark_score 공식

```
landmark_score(node, path) =
    w1 × pagerank_rank      (전체 그래프 중요도, 0~1 normalize)
  + w2 × betweenness_rank   (다리 역할, 0~1 normalize)
  + w3 × bridge_score       (경로 안 위치적 중요도, 0~1)
  + w4 × sector_uniqueness  (경로 내 섹터 다양성 기여도, 0~1)

가중치 (MVP):
  w1 = 0.25 (pagerank)
  w2 = 0.20 (betweenness)
  w3 = 0.30 (bridge)     ← 경로 내 기여가 가장 중요
  w4 = 0.25 (sector)

⚠️ centrality null fallback:
  pagerank/betweenness가 null(GDS 미실행 상태)이면 그 가중치를 bridge_score에 재분배.
  즉 w3 = 0.30 + 0.25 + 0.20 = 0.75, w4 = 0.25.
```

### bridge_score 계산

경로 `A → B → C → D → E`에서 B, C, D의 bridge 중요도:
- **위치 가중치**: 경로 중앙에 가까울수록 높음. 총 N개 노드 중 i번째 중간 노드라면 `1 - |i - (N-1)/2| / ((N-1)/2)`
- **연결도 가중치**: 이 노드의 degree (Neo4j에서 count(neighbors))를 0~1 정규화

```python
bridge_score(node, path) = 0.5 × position_weight + 0.5 × degree_weight
```

### sector_uniqueness

경로에서 섹터 다양성을 높이는 노드일수록 우선. 예: 경로가 `Tech → Tech → Tech → Healthcare → Tech`이면, Healthcare 노드의 sector_uniqueness = 1.0. 같은 섹터가 반복되는 노드는 점수 낮음.

```python
sector_uniqueness(node, path) = 1 / count(path에서 해당 섹터 등장 횟수)
```

---

## 구현

```python
# chainsight/services/path_service.py (이어서 추가)

from typing import List, Dict, Optional
from django.conf import settings
from chainsight.graph.repository import Neo4jGraphRepository
from stocks.models import Stock


def generate_summary_path(path_nodes: List[str]) -> List[str]:
    """
    5+ 노드 경로를 3~4개 landmark로 압축.
    4개 이하는 그대로 반환.

    Args:
        path_nodes: ["NVDA", "TSM", "ASML", "AMAT", "LRCX", "KLAC", "MU"]

    Returns:
        ["NVDA", "AMAT", "MU"] 등 압축된 landmark 배열
    """
    if len(path_nodes) <= 4:
        return list(path_nodes)

    # 중간 노드만 대상
    middle = path_nodes[1:-1]

    # landmark 수 결정
    total = len(path_nodes)
    if total <= 6:
        k = 1
    else:
        k = 2

    # 각 중간 노드의 landmark_score 계산
    scores = compute_landmark_scores(middle, path_nodes)

    # 상위 k개 선택 (원본 순서 유지)
    top_k_indices = sorted(
        range(len(middle)),
        key=lambda i: scores[i],
        reverse=True,
    )[:k]
    top_k_indices.sort()  # 원본 순서 복원

    selected_middle = [middle[i] for i in top_k_indices]

    return [path_nodes[0]] + selected_middle + [path_nodes[-1]]


def compute_landmark_scores(middle_nodes: List[str],
                             full_path: List[str]) -> List[float]:
    """
    중간 노드들의 landmark_score를 계산.

    Returns:
        len(middle_nodes) 길이의 score 리스트 (0~1)
    """
    if not middle_nodes:
        return []

    # 1. Neo4j에서 중심성 조회 (GDS 결과) - middle_nodes만 대상
    #    시작/끝 노드는 summary_path에 항상 포함되므로 landmark 선정에서 제외
    centrality = _fetch_centrality(middle_nodes)

    # 2. 각 노드 메트릭 계산
    # pagerank, betweenness는 None일 수 있음 (GDS 미실행)
    pagerank_valid = any(
        centrality[n].get('pagerank') is not None for n in middle_nodes
    )
    betweenness_valid = any(
        centrality[n].get('betweenness') is not None for n in middle_nodes
    )

    # 가중치
    if pagerank_valid and betweenness_valid:
        w = {'pagerank': 0.25, 'betweenness': 0.20, 'bridge': 0.30, 'sector': 0.25}
    elif pagerank_valid and not betweenness_valid:
        # betweenness 가중치를 bridge에 재분배
        w = {'pagerank': 0.25, 'betweenness': 0.0, 'bridge': 0.50, 'sector': 0.25}
    elif not pagerank_valid and betweenness_valid:
        w = {'pagerank': 0.0, 'betweenness': 0.20, 'bridge': 0.55, 'sector': 0.25}
    else:
        # 둘 다 null → bridge로 전부 재분배
        w = {'pagerank': 0.0, 'betweenness': 0.0, 'bridge': 0.75, 'sector': 0.25}

    # 3. pagerank/betweenness rank (0~1 normalize)
    pagerank_ranks = _normalize_rank(
        {n: centrality[n].get('pagerank') or 0 for n in middle_nodes}
    )
    betweenness_ranks = _normalize_rank(
        {n: centrality[n].get('betweenness') or 0 for n in middle_nodes}
    )

    # 4. bridge_score
    bridge_scores = _compute_bridge_scores(middle_nodes, full_path, centrality)

    # 5. sector_uniqueness
    sector_scores = _compute_sector_uniqueness(middle_nodes, full_path)

    # 6. 가중합
    scores = []
    for i, node in enumerate(middle_nodes):
        s = (
            w['pagerank'] * pagerank_ranks.get(node, 0)
            + w['betweenness'] * betweenness_ranks.get(node, 0)
            + w['bridge'] * bridge_scores[i]
            + w['sector'] * sector_scores[i]
        )
        scores.append(s)

    return scores


def _fetch_centrality(tickers: List[str]) -> Dict[str, Dict]:
    """Neo4j에서 pagerank_score, betweenness_score, degree 조회."""
    repo = Neo4jGraphRepository(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD,
    )

    rows = repo.run_query(
        """
        UNWIND $tickers AS t
        MATCH (s:Stock {ticker: t})
        OPTIONAL MATCH (s)-[r]-(other:Stock)
        RETURN s.ticker AS ticker,
               s.pagerank_score AS pagerank,
               s.betweenness_score AS betweenness,
               count(DISTINCT other) AS degree
        """,
        {'tickers': tickers}
    )

    return {
        row['ticker']: {
            'pagerank': row['pagerank'],
            'betweenness': row['betweenness'],
            'degree': row['degree'],
        }
        for row in rows
    }


def _normalize_rank(values: Dict[str, float]) -> Dict[str, float]:
    """값들을 0~1 percentile rank로 변환."""
    if not values:
        return {}
    sorted_items = sorted(values.items(), key=lambda x: x[1])
    n = len(sorted_items)
    return {
        ticker: (i / (n - 1)) if n > 1 else 1.0
        for i, (ticker, _) in enumerate(sorted_items)
    }


def _compute_bridge_scores(middle: List[str], full_path: List[str],
                            centrality: Dict[str, Dict]) -> List[float]:
    """
    bridge_score = 0.5 × position_weight + 0.5 × degree_weight
    """
    scores = []
    total_middle = len(middle)

    # degree normalize
    degrees = {n: centrality[n].get('degree', 0) for n in middle}
    max_degree = max(degrees.values()) if degrees else 1
    if max_degree == 0:
        max_degree = 1

    for i, node in enumerate(middle):
        # position_weight: 중앙에 가까울수록 1
        if total_middle == 1:
            position_weight = 1.0
        else:
            center = (total_middle - 1) / 2
            position_weight = 1.0 - abs(i - center) / center

        # degree_weight
        degree_weight = degrees[node] / max_degree

        scores.append(0.5 * position_weight + 0.5 * degree_weight)

    return scores


def _compute_sector_uniqueness(middle: List[str],
                                full_path: List[str]) -> List[float]:
    """경로 내 섹터 다양성 기여도."""
    from collections import Counter

    stocks = Stock.objects.filter(ticker__in=full_path).values_list('ticker', 'sector')
    sector_map = dict(stocks)

    # 경로 전체의 섹터 분포
    path_sectors = [sector_map.get(t) for t in full_path if sector_map.get(t)]
    sector_counts = Counter(path_sectors)

    scores = []
    for node in middle:
        sector = sector_map.get(node)
        if sector is None:
            scores.append(0.5)  # 섹터 모름 → 중립
        else:
            count = sector_counts[sector]
            scores.append(1.0 / count)  # 흔한 섹터일수록 낮은 점수

    return scores
```

---

## WatchlistViewSet 연계

CS-6-2의 create()에서 TODO로 남겼던 부분을 채운다:

```python
# chainsight/views/watchlist_views.py (수정)

from chainsight.services.path_service import (
    build_edge_snapshot,
    build_path_signature,
    build_initial_why_now,
    generate_summary_path,  # ← 추가
)

class WatchlistViewSet(viewsets.ModelViewSet):
    def create(self, request, *args, **kwargs):
        # ... (기존 validation)

        path_nodes = validated['path_nodes']
        edge_snapshot = build_edge_snapshot(path_nodes)
        path_signature = build_path_signature(path_nodes, edge_snapshot)
        why_now = build_initial_why_now(path_nodes, edge_snapshot)

        # 변경: summary_path 생성
        summary_path = generate_summary_path(path_nodes)

        # ... (saved_path.create)
```

---

## Recheck 연계 (선택)

Recheck에서 path_nodes는 변하지 않으므로 summary_path도 원칙적으로 변경 없음. 단, GDS 결과가 업데이트되어 landmark 선정이 바뀔 수 있다. 이 경우:

**옵션 A (간단)**: Recheck 시 summary_path는 재계산하지 않음. 초기 생성 시점의 landmark 유지.

**옵션 B (정확)**: Recheck 시 summary_path도 재계산. 사용자에게는 "landmark가 바뀌었다"가 추가 정보가 될 수 있음.

**MVP는 옵션 A 채택**. 이유: GDS는 주 1회 실행이라 landmark가 자주 바뀌지 않고, 카드 요약이 흔들리면 오히려 사용자 혼란. 수동 재계산은 Django management command로 별도 제공:

```python
# chainsight/management/commands/regenerate_summary_paths.py

from django.core.management.base import BaseCommand
from chainsight.models import SavedPath
from chainsight.services.path_service import generate_summary_path


class Command(BaseCommand):
    help = 'Regenerate summary_path for all SavedPath (run after GDS rerun).'

    def handle(self, *args, **options):
        count = 0
        for path in SavedPath.objects.all():
            new_summary = generate_summary_path(path.path_nodes)
            if new_summary != path.summary_path:
                path.summary_path = new_summary
                path.save(update_fields=['summary_path', 'updated_at'])
                count += 1
        self.stdout.write(f'Regenerated {count} summary_paths.')
```

---

## 테스트

```python
# chainsight/tests/test_summary_path.py

import pytest
from chainsight.services.path_service import (
    generate_summary_path,
    compute_landmark_scores,
    _normalize_rank,
    _compute_bridge_scores,
    _compute_sector_uniqueness,
)


def test_short_path_unchanged():
    """4개 이하 경로는 그대로."""
    assert generate_summary_path(['A', 'B']) == ['A', 'B']
    assert generate_summary_path(['A', 'B', 'C']) == ['A', 'B', 'C']
    assert generate_summary_path(['A', 'B', 'C', 'D']) == ['A', 'B', 'C', 'D']


def test_long_path_compressed(mocker):
    """5+ 경로는 압축."""
    mocker.patch(
        'chainsight.services.path_service._fetch_centrality',
        return_value={
            'A': {'pagerank': None, 'betweenness': None, 'degree': 5},
            'B': {'pagerank': None, 'betweenness': None, 'degree': 10},
            'C': {'pagerank': None, 'betweenness': None, 'degree': 15},  # 중앙 + 고차수
            'D': {'pagerank': None, 'betweenness': None, 'degree': 8},
            'E': {'pagerank': None, 'betweenness': None, 'degree': 6},
            'F': {'pagerank': None, 'betweenness': None, 'degree': 7},
            'G': {'pagerank': None, 'betweenness': None, 'degree': 4},
        }
    )
    mocker.patch(
        'stocks.models.Stock.objects.filter',
        return_value=mocker.MagicMock(values_list=lambda *a, **k: [
            ('A', 'Tech'), ('B', 'Tech'), ('C', 'Tech'),
            ('D', 'Finance'), ('E', 'Tech'), ('F', 'Tech'), ('G', 'Tech'),
        ])
    )

    path = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
    summary = generate_summary_path(path)

    # 시작/끝 포함 필수
    assert summary[0] == 'A'
    assert summary[-1] == 'G'
    # 총 4개 (시작 + landmark 2 + 끝)
    assert len(summary) == 4


def test_normalize_rank():
    result = _normalize_rank({'A': 10, 'B': 20, 'C': 30})
    assert result['A'] == 0.0
    assert result['B'] == 0.5
    assert result['C'] == 1.0


def test_normalize_rank_single():
    result = _normalize_rank({'A': 5})
    assert result['A'] == 1.0


def test_bridge_score_center_highest():
    """중앙 노드의 position_weight가 최고"""
    centrality = {
        'A': {'degree': 10}, 'B': {'degree': 10},
        'C': {'degree': 10}, 'D': {'degree': 10}, 'E': {'degree': 10},
    }
    scores = _compute_bridge_scores(
        middle=['B', 'C', 'D'],
        full_path=['A', 'B', 'C', 'D', 'E'],
        centrality=centrality,
    )
    # C가 가장 중앙
    assert scores[1] > scores[0]
    assert scores[1] > scores[2]


def test_sector_uniqueness_unique_sector_high():
    from unittest.mock import patch, MagicMock

    mock_qs = MagicMock()
    mock_qs.values_list.return_value = [
        ('A', 'Tech'), ('B', 'Tech'), ('C', 'Healthcare'),
        ('D', 'Tech'), ('E', 'Tech')
    ]
    with patch('stocks.models.Stock.objects.filter', return_value=mock_qs):
        scores = _compute_sector_uniqueness(
            middle=['B', 'C', 'D'],
            full_path=['A', 'B', 'C', 'D', 'E'],
        )
        # C(Healthcare)가 가장 unique → 1.0
        assert scores[1] == 1.0
        # B, D는 Tech 4개 중 하나 → 0.25
        assert scores[0] == pytest.approx(0.25)
        assert scores[2] == pytest.approx(0.25)


def test_null_centrality_fallback(mocker):
    """GDS 미실행 상태에서도 정상 동작"""
    mocker.patch(
        'chainsight.services.path_service._fetch_centrality',
        return_value={
            'A': {'pagerank': None, 'betweenness': None, 'degree': 3},
            'B': {'pagerank': None, 'betweenness': None, 'degree': 5},
            'C': {'pagerank': None, 'betweenness': None, 'degree': 8},
            'D': {'pagerank': None, 'betweenness': None, 'degree': 4},
            'E': {'pagerank': None, 'betweenness': None, 'degree': 3},
        }
    )
    mock_qs = mocker.MagicMock()
    mock_qs.values_list.return_value = [
        ('A', 'Tech'), ('B', 'Tech'), ('C', 'Tech'), ('D', 'Tech'), ('E', 'Tech')
    ]
    mocker.patch('stocks.models.Stock.objects.filter', return_value=mock_qs)

    summary = generate_summary_path(['A', 'B', 'C', 'D', 'E'])
    assert summary[0] == 'A'
    assert summary[-1] == 'E'
    assert len(summary) == 3  # 5 노드 → landmark 1개
```

---

## 완료 기준

```
□ generate_summary_path() 함수 구현
□ 4개 이하는 path_nodes 그대로 반환
□ 5+ 노드는 landmark 압축 (5~6→3개, 7+→4개)
□ landmark 선정 시 시작/끝 노드 항상 포함
□ landmark 순서는 원본 경로 순서 유지
□ GDS null 상태 fallback 동작 (pagerank/betweenness 없으면 bridge+sector로 재분배)
□ CS-6-2 WatchlistViewSet.create()에서 호출되어 summary_path 저장
□ Neo4j 쿼리 1회로 중심성 일괄 조회
□ regenerate_summary_paths management command 작동
□ 7개 테스트 pass
```

---

## 주의사항

### landmark 선정이 무의미한 경우

경로가 짧거나(4개 이하) GDS와 섹터 정보가 모두 null이면 landmark 선정이 사실상 순수 bridge_score만으로 결정됨. 이때는 경로 중앙 노드가 선택되는데, 사용자 관점에서는 "왜 이 노드가 대표로 뽑혔지?"가 덜 직관적일 수 있음. CS-7-2 UI에서 summary_path에 `...` 같은 추가 시각 장치로 "중간 생략됨"을 분명히 해야 함.

### 성능

경로당 최대 10개 노드 중 중간 8개에 대해 Neo4j 쿼리 1회 + Python 계산. 전체 100ms 이내 예상. 대량 SavedPath 일괄 재계산은 management command에서 N+1 쿼리 발생 가능 — 필요 시 tickers 일괄 조회로 최적화.

### regenerate_summary_paths 주기

GDS 배치가 주 1회(CS-3-3)이므로, 이론적으로는 GDS 실행 직후 자동으로 regenerate 돌리는 게 맞음. 하지만 옵션 A(Recheck 시 재계산 안 함)를 채택했으므로 자동 실행 task는 만들지 않음. 필요 시 수동으로 돌리거나, 사용자가 Recheck 요청 시마다 lazy하게 재계산하는 방식으로 확장 가능 (v1.3).

### w1~w4 튜닝

MVP 가중치는 직관 기반. 사용자가 Watchlist에서 카드를 많이 클릭하는 경로 vs 무시하는 경로를 추적하면(PathAction 로그), 어떤 landmark 구성이 효과적인지 분석 가능. v1.3에서 A/B 테스트.

---

→ **다음**: CS-6-6 (Expand API)

**END OF DOCUMENT**
