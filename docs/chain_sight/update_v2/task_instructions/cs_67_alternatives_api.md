# CS-6-7: Alternatives API

> **작업 번호**: CS-6-7
> **목표**: 경로 내 특정 노드를 동일 역할의 다른 노드로 대체할 수 있는 대안 후보 반환
> **예상 소요**: 1~2일
> **선행 조건**: CS-6-2, CS-3-2 (Neo4j 엣지 동기화)
> **산출물**:
> - `chainsight/services/alternatives_service.py`
> - WatchlistViewSet.alternatives() action 구현

---

## 배경

경로 `NVDA → TSM → AMAT → LRCX`에서 사용자가 "AMAT 대신 다른 반도체 장비 회사로 연결할 수는 없을까?"라고 탐구하고 싶을 때 사용한다.

**v1.4 변경**: PM v1.2 초안의 "Compare" 액션을 Alternatives로 다운스코프. path-level 비교(전체 경로를 다른 경로와 비교)는 MVP에서 제외. 노드 단위 대안만 제공.

**핵심 아이디어**: 대상 노드의 양옆 이웃(path에서 앞/뒤)과 동일한 관계 타입으로 연결된 다른 노드를 찾는다.

예시:
```
경로: NVDA → TSM → AMAT → LRCX
target = AMAT
양옆: TSM (앞), LRCX (뒤)
TSM—AMAT 관계: SUPPLIES_TO (TSM이 AMAT로부터 장비 공급)
AMAT—LRCX 관계: COMPETES_WITH
→ 대안: TSM과 SUPPLIES_TO 관계 + LRCX와 COMPETES_WITH 관계를 모두 가진 다른 노드
→ 예: KLAC, ACLS 등
```

---

## API 스펙

```
POST /api/chainsight/watchlist/{id}/alternatives/

Body:
  {
    "target_ticker": "AMAT",    // 필수: 대체 대상 노드
    "limit": 10                 // 기본: 10
  }

Response:
  {
    "target_ticker": "AMAT",
    "neighbor_constraints": {
      "before": {"ticker": "TSM", "relation_type": "SUPPLIES_TO"},
      "after": {"ticker": "LRCX", "relation_type": "COMPETES_WITH"}
    },
    "alternatives": [
      {
        "ticker": "KLAC",
        "name": "KLA Corporation",
        "sector": "Technology",
        "industry": "Semiconductors",
        "overlap_count": 2,            // 양옆 모두 매칭
        "relation_before": {
          "type": "SUPPLIES_TO",
          "truth_score": 80,
          "status": "probable"
        },
        "relation_after": {
          "type": "COMPETES_WITH",
          "truth_score": 60,
          "status": "probable"
        },
        "why_summary": "양옆 노드 모두와 같은 관계 유형 확인"
      },
      ...
    ],
    "total_found": 5
  }
```

---

## 구현

### 엣지 케이스 처리

**target이 경로 시작 노드**: before neighbor 없음. after만으로 매칭.
**target이 경로 끝 노드**: after neighbor 없음. before만으로 매칭.
**target이 중간 노드**: before + after 모두. 양쪽 모두 매칭되면 overlap=2, 한쪽만 매칭되면 overlap=1.

### Service

```python
# chainsight/services/alternatives_service.py

from typing import List, Dict, Optional
from django.conf import settings
from chainsight.graph.repository import Neo4jGraphRepository


def find_alternatives(
    path_nodes: List[str],
    target_ticker: str,
    limit: int = 10,
) -> Dict:
    """
    path_nodes 안의 target_ticker를 대체할 수 있는 대안 노드들을 찾는다.

    Args:
        path_nodes: ["NVDA", "TSM", "AMAT", "LRCX"]
        target_ticker: "AMAT"
        limit: 반환 최대 수

    Returns:
        {
            'target_ticker': str,
            'neighbor_constraints': {'before': {...}, 'after': {...}},
            'alternatives': [...],
            'total_found': int,
        }
    """
    if target_ticker not in path_nodes:
        raise ValueError(f'{target_ticker} not in path')

    idx = path_nodes.index(target_ticker)
    before = path_nodes[idx - 1] if idx > 0 else None
    after = path_nodes[idx + 1] if idx < len(path_nodes) - 1 else None

    if before is None and after is None:
        # 경로 하나짜리 노드 — 이론상 불가 (path_nodes 최소 2개)
        return {
            'target_ticker': target_ticker,
            'neighbor_constraints': {'before': None, 'after': None},
            'alternatives': [],
            'total_found': 0,
        }

    repo = Neo4jGraphRepository(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD,
    )

    # 양옆 관계 타입 조회
    before_rel = _fetch_relation(repo, before, target_ticker) if before else None
    after_rel = _fetch_relation(repo, target_ticker, after) if after else None

    # 대안 후보 검색
    alternatives = _query_alternatives(
        repo,
        target_ticker=target_ticker,
        before_ticker=before,
        before_rel_type=before_rel['rel_type'] if before_rel else None,
        after_ticker=after,
        after_rel_type=after_rel['rel_type'] if after_rel else None,
        excluded=path_nodes,
        limit=limit,
    )

    return {
        'target_ticker': target_ticker,
        'neighbor_constraints': {
            'before': (
                {'ticker': before, 'relation_type': before_rel['rel_type']}
                if before_rel else None
            ),
            'after': (
                {'ticker': after, 'relation_type': after_rel['rel_type']}
                if after_rel else None
            ),
        },
        'alternatives': alternatives,
        'total_found': len(alternatives),  # Cypher LIMIT 이후 카운트
    }


def _fetch_relation(repo, a: str, b: str) -> Optional[Dict]:
    """두 노드 간 primary 관계 조회."""
    rows = repo.run_query(
        """
        MATCH (a:Stock {ticker: $a})-[r]-(b:Stock {ticker: $b})
        WHERE r.status IN ['confirmed', 'probable']
           OR type(r) = 'PEER_OF'
        RETURN type(r) AS rel_type,
               r.truth_score AS truth_score,
               r.status AS status
        ORDER BY r.truth_score DESC NULLS LAST
        LIMIT 1
        """,
        {'a': a, 'b': b}
    )
    if rows:
        return rows[0]
    return None


def _query_alternatives(
    repo,
    target_ticker: str,
    before_ticker: Optional[str],
    before_rel_type: Optional[str],
    after_ticker: Optional[str],
    after_rel_type: Optional[str],
    excluded: List[str],
    limit: int,
) -> List[Dict]:
    """
    대안 후보 검색.

    전략:
    - 양쪽 이웃이 있으면: 양쪽 모두와 같은 관계 타입으로 연결된 노드 (overlap=2)
      + 한쪽만 연결된 노드 (overlap=1) 보조
    - 한쪽 이웃만 있으면: 그쪽과 같은 관계 타입으로 연결된 노드
    """

    if before_ticker and after_ticker:
        # 양쪽 모두
        return _query_both_sides(
            repo, target_ticker,
            before_ticker, before_rel_type,
            after_ticker, after_rel_type,
            excluded, limit,
        )
    elif before_ticker:
        return _query_one_side(
            repo, before_ticker, before_rel_type, 'before',
            excluded, limit,
        )
    elif after_ticker:
        return _query_one_side(
            repo, after_ticker, after_rel_type, 'after',
            excluded, limit,
        )
    return []


def _query_both_sides(repo, target, before, before_rel, after, after_rel,
                       excluded, limit):
    """양쪽 이웃 모두 고려."""
    # Cypher: before와 after 모두와 연결된 노드를 overlap=2로 표시,
    #         한쪽만 연결된 노드를 overlap=1로 표시, UNION
    rows = repo.run_query(
        """
        // overlap=2: 양쪽 모두
        MATCH (cand:Stock)-[r1]-(b:Stock {ticker: $before})
        WHERE type(r1) = $before_rel
          AND cand.ticker <> $target
          AND NOT cand.ticker IN $excluded
          AND (r1.status IN ['confirmed', 'probable'] OR type(r1) = 'PEER_OF')
        WITH cand, r1
        MATCH (cand)-[r2]-(a:Stock {ticker: $after})
        WHERE type(r2) = $after_rel
          AND (r2.status IN ['confirmed', 'probable'] OR type(r2) = 'PEER_OF')
        RETURN cand.ticker AS ticker,
               cand.name AS name,
               cand.sector AS sector,
               cand.industry AS industry,
               cand.heat_score AS heat_score,
               2 AS overlap,
               {rel_type: type(r1), truth_score: r1.truth_score, status: r1.status} AS rel_before,
               {rel_type: type(r2), truth_score: r2.truth_score, status: r2.status} AS rel_after
        ORDER BY r1.truth_score + r2.truth_score DESC NULLS LAST
        LIMIT $limit

        UNION

        // overlap=1: before만 (after와는 연결 없음)
        MATCH (cand:Stock)-[r1]-(b:Stock {ticker: $before})
        WHERE type(r1) = $before_rel
          AND cand.ticker <> $target
          AND NOT cand.ticker IN $excluded
          AND (r1.status IN ['confirmed', 'probable'] OR type(r1) = 'PEER_OF')
          AND NOT EXISTS {
            MATCH (cand)-[r2]-(:Stock {ticker: $after})
            WHERE type(r2) = $after_rel
          }
        RETURN cand.ticker AS ticker,
               cand.name AS name,
               cand.sector AS sector,
               cand.industry AS industry,
               cand.heat_score AS heat_score,
               1 AS overlap,
               {rel_type: type(r1), truth_score: r1.truth_score, status: r1.status} AS rel_before,
               null AS rel_after
        ORDER BY r1.truth_score DESC NULLS LAST
        LIMIT $limit
        """,
        {
            'target': target,
            'before': before, 'before_rel': before_rel,
            'after': after, 'after_rel': after_rel,
            'excluded': excluded, 'limit': limit,
        }
    )

    return [_format_alternative(row) for row in rows[:limit]]


def _query_one_side(repo, neighbor_ticker, rel_type, side, excluded, limit):
    """한쪽 이웃만 고려."""
    rows = repo.run_query(
        """
        MATCH (cand:Stock)-[r]-(n:Stock {ticker: $neighbor})
        WHERE type(r) = $rel_type
          AND cand.ticker <> $neighbor
          AND NOT cand.ticker IN $excluded
          AND (r.status IN ['confirmed', 'probable'] OR type(r) = 'PEER_OF')
        RETURN cand.ticker AS ticker,
               cand.name AS name,
               cand.sector AS sector,
               cand.industry AS industry,
               cand.heat_score AS heat_score,
               r.truth_score AS truth_score,
               r.status AS status
        ORDER BY r.truth_score DESC NULLS LAST
        LIMIT $limit
        """,
        {'neighbor': neighbor_ticker, 'rel_type': rel_type,
         'excluded': excluded, 'limit': limit}
    )

    results = []
    for row in rows:
        rel_info = {
            'rel_type': rel_type,
            'truth_score': row.get('truth_score'),
            'status': row.get('status'),
        }
        results.append({
            'ticker': row['ticker'],
            'name': row.get('name') or row['ticker'],
            'sector': row.get('sector') or '',
            'industry': row.get('industry') or '',
            'overlap_count': 1,
            'relation_before': rel_info if side == 'before' else None,
            'relation_after': rel_info if side == 'after' else None,
            'why_summary': f'{side}쪽 노드와 같은 {rel_type} 관계',
        })
    return results


def _format_alternative(row: Dict) -> Dict:
    """양옆 검색 결과 포맷."""
    overlap = row.get('overlap', 0)
    rel_before = row.get('rel_before')
    rel_after = row.get('rel_after')

    if overlap == 2:
        why = '양옆 노드 모두와 같은 관계 유형 확인'
    elif overlap == 1 and rel_before:
        why = '앞쪽 노드와 같은 관계 유형'
    elif overlap == 1 and rel_after:
        why = '뒤쪽 노드와 같은 관계 유형'
    else:
        why = '관련 노드'

    return {
        'ticker': row['ticker'],
        'name': row.get('name') or row['ticker'],
        'sector': row.get('sector') or '',
        'industry': row.get('industry') or '',
        'overlap_count': overlap,
        'relation_before': rel_before,
        'relation_after': rel_after,
        'why_summary': why,
    }
```

### ViewSet 액션

```python
# chainsight/views/watchlist_views.py (이어서)

from chainsight.services.alternatives_service import find_alternatives


class WatchlistViewSet(viewsets.ModelViewSet):
    # ...

    @action(detail=True, methods=['post'])
    def alternatives(self, request, pk=None):
        """
        Alternatives 액션.

        Body (필수):
          { "target_ticker": "AMAT", "limit": 10 }
        """
        saved_path = self.get_object()

        if saved_path.status in (SavedPath.Status.ARCHIVED, SavedPath.Status.RESOLVED):
            return Response(
                {'detail': f'{saved_path.status} 상태에서는 Alternatives 탐색 불가.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target = request.data.get('target_ticker')
        if not target:
            return Response(
                {'detail': 'target_ticker는 필수입니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if target not in saved_path.path_nodes:
            return Response(
                {'detail': 'target_ticker가 경로에 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        limit = min(int(request.data.get('limit', 10)), 50)

        try:
            result = find_alternatives(
                path_nodes=saved_path.path_nodes,
                target_ticker=target,
                limit=limit,
            )
        except ValueError as e:
            return Response({'detail': str(e)},
                             status=status.HTTP_400_BAD_REQUEST)

        # 액션 로그
        PathAction.objects.create(
            saved_path=saved_path,
            action_type=PathAction.ActionType.ALTERNATIVES,
            metadata={
                'target_ticker': target,
                'candidates_count': len(result['alternatives']),
                'top_candidates': [c['ticker'] for c in result['alternatives'][:3]],
            }
        )

        return Response(result)
```

---

## 테스트

```python
# chainsight/tests/test_alternatives.py

import pytest
from chainsight.services.alternatives_service import find_alternatives
from chainsight.models import SavedPath, PathAction


@pytest.mark.django_db
def test_find_alternatives_middle_node(mocker):
    """중간 노드의 양옆 고려."""
    mock_repo = mocker.MagicMock()
    # before/after 관계 조회
    mock_repo.run_query.side_effect = [
        # before_rel (TSM-AMAT)
        [{'rel_type': 'SUPPLIES_TO', 'truth_score': 85, 'status': 'confirmed'}],
        # after_rel (AMAT-LRCX)
        [{'rel_type': 'COMPETES_WITH', 'truth_score': 60, 'status': 'probable'}],
        # alternatives
        [
            {'ticker': 'KLAC', 'name': 'KLA', 'sector': 'Tech',
             'industry': 'Semi', 'heat_score': 0.6, 'overlap': 2,
             'rel_before': {'rel_type': 'SUPPLIES_TO', 'truth_score': 80, 'status': 'probable'},
             'rel_after': {'rel_type': 'COMPETES_WITH', 'truth_score': 55, 'status': 'probable'}},
        ],
    ]
    mocker.patch(
        'chainsight.services.alternatives_service.Neo4jGraphRepository',
        return_value=mock_repo,
    )

    result = find_alternatives(
        path_nodes=['NVDA', 'TSM', 'AMAT', 'LRCX'],
        target_ticker='AMAT',
        limit=10,
    )

    assert result['target_ticker'] == 'AMAT'
    assert result['neighbor_constraints']['before']['ticker'] == 'TSM'
    assert result['neighbor_constraints']['after']['ticker'] == 'LRCX'
    assert len(result['alternatives']) == 1
    assert result['alternatives'][0]['ticker'] == 'KLAC'
    assert result['alternatives'][0]['overlap_count'] == 2


@pytest.mark.django_db
def test_find_alternatives_start_node(mocker):
    """시작 노드는 after만 고려."""
    mock_repo = mocker.MagicMock()
    mock_repo.run_query.side_effect = [
        [{'rel_type': 'SUPPLIES_TO', 'truth_score': 85, 'status': 'confirmed'}],  # after_rel
        [
            {'ticker': 'AAPL', 'name': 'Apple', 'sector': 'Tech',
             'industry': 'Consumer', 'heat_score': 0.5,
             'truth_score': 80, 'status': 'probable'}
        ],  # alternatives (one_side 쿼리는 다른 스키마)
    ]
    mocker.patch(
        'chainsight.services.alternatives_service.Neo4jGraphRepository',
        return_value=mock_repo,
    )

    result = find_alternatives(
        path_nodes=['NVDA', 'TSM'],
        target_ticker='NVDA',
        limit=10,
    )

    assert result['neighbor_constraints']['before'] is None
    assert result['neighbor_constraints']['after']['ticker'] == 'TSM'
    assert len(result['alternatives']) == 1
    assert result['alternatives'][0]['overlap_count'] == 1


@pytest.mark.django_db
def test_find_alternatives_target_not_in_path():
    with pytest.raises(ValueError):
        find_alternatives(
            path_nodes=['A', 'B', 'C'],
            target_ticker='XYZ',
        )


@pytest.mark.django_db
def test_alternatives_api_success(client, mocker):
    path = SavedPath.objects.create(
        path_nodes=['NVDA', 'TSM', 'AMAT', 'LRCX'],
    )
    mocker.patch(
        'chainsight.services.alternatives_service.find_alternatives',
        return_value={
            'target_ticker': 'AMAT',
            'neighbor_constraints': {
                'before': {'ticker': 'TSM', 'relation_type': 'SUPPLIES_TO'},
                'after': {'ticker': 'LRCX', 'relation_type': 'COMPETES_WITH'},
            },
            'alternatives': [{'ticker': 'KLAC', 'name': 'KLA',
                              'sector': 'Tech', 'industry': 'Semi',
                              'overlap_count': 2}],
            'total_found': 1,
        }
    )

    r = client.post(
        f'/api/chainsight/watchlist/{path.id}/alternatives/',
        {'target_ticker': 'AMAT'},
        format='json',
    )
    assert r.status_code == 200
    assert r.data['target_ticker'] == 'AMAT'
    assert len(r.data['alternatives']) == 1

    actions = path.actions.filter(action_type='alternatives')
    assert actions.count() == 1
    assert actions.first().metadata['target_ticker'] == 'AMAT'


@pytest.mark.django_db
def test_alternatives_missing_target(client):
    path = SavedPath.objects.create(path_nodes=['A', 'B'])
    r = client.post(
        f'/api/chainsight/watchlist/{path.id}/alternatives/',
        {},
        format='json',
    )
    assert r.status_code == 400


@pytest.mark.django_db
def test_alternatives_target_not_in_path(client):
    path = SavedPath.objects.create(path_nodes=['A', 'B'])
    r = client.post(
        f'/api/chainsight/watchlist/{path.id}/alternatives/',
        {'target_ticker': 'XYZ'},
        format='json',
    )
    assert r.status_code == 400
```

---

## 완료 기준

```
□ find_alternatives() 구현
□ target이 시작 노드 (before 없음) 처리
□ target이 끝 노드 (after 없음) 처리
□ target이 중간 노드 (양옆 모두)에서 overlap=2 우선 반환
□ 양옆 모두 매칭이 부족하면 한쪽만 매칭된 overlap=1도 포함
□ POST /watchlist/{id}/alternatives/ 동작
□ target_ticker 누락 시 400
□ target_ticker가 경로에 없으면 400
□ archived/resolved 거부
□ PathAction(ALTERNATIVES) 기록, metadata.target_ticker + top_candidates
□ 응답에 neighbor_constraints 포함 (사용자가 왜 이 관계인지 이해)
□ 6개 테스트 pass
```

---

## 주의사항

### Cypher UNION LIMIT 문제

Neo4j Cypher에서 `UNION` 사용 시 각 쿼리에 개별 LIMIT을 걸고, 최종 limit은 Python에서 slice. 이렇게 해야 overlap=2 결과와 overlap=1 결과가 섞이지 않고 각각 충분히 나옴. 위 코드에서 `rows[:limit]`으로 최종 자름.

### Overlap 정렬

overlap=2 결과가 overlap=1 결과보다 위로 와야 함. Python에서 정렬:

```python
alternatives.sort(key=lambda a: (-a['overlap_count'], ...))
```

위 코드에서는 UNION의 순서에 의존. 안정성을 위해 명시적 정렬 추가 권장 (TODO로 남김).

### 관계 방향성

`MATCH (cand)-[r1]-(b)`는 undirected 매칭. SUPPLIES_TO는 directed이므로 엄밀히는 방향 구분 필요. 하지만 Alternatives의 의미상 "같은 관계 역할"을 찾는 것이므로 방향 무시해도 됨 (A가 B에 공급하든, B가 A로부터 공급받든 "공급망 연결"로 처리).

필요 시 Cypher에서 방향 명시:
```cypher
MATCH (cand)-[r1:SUPPLIES_TO]->(b)  // 방향 지정
```

MVP에서는 방향 무시 정책.

### PEER_OF status 누락 대응

PEER_OF는 status가 없을 수 있음. `r.status IN [...] OR type(r) = 'PEER_OF'` 예외로 처리 (CS-6-6과 동일).

### 결과 0개일 때

neighbor_constraints는 반환하되 alternatives가 빈 배열일 수 있음. 프론트엔드(CS-7-3)에서 "조건에 맞는 대안이 없습니다. 경로를 그대로 유지하거나 Expand로 확장해보세요." 메시지 표시.

### 대안 선택 후 처리

Expand와 마찬가지로 본 API는 **후보만 반환**. 사용자가 선택하면 새 SavedPath 생성 (기존 path_nodes에서 target을 대안으로 교체한 버전). 기존 경로는 보존. 프론트엔드 CS-7-3에서 처리.

---

→ **다음**: CS-7-1 (Watch 버튼)

```
★ M4 달성: "API 완성 + Path Watchlist 백엔드 완성"
  → Phase 6 전체(CS-6-1~6-7) 완료
  → 프론트엔드 개발(Phase 7) 시작 가능
```

**END OF DOCUMENT**
