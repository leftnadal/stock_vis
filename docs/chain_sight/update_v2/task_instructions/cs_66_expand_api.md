# CS-6-6: Expand API

> **작업 번호**: CS-6-6
> **목표**: 저장된 경로의 마지막 노드에서 1-hop 확장 후보를 반환하는 API 구현
> **예상 소요**: 1~2일
> **선행 조건**: CS-6-2 (Watchlist CRUD), CS-3-2 (Neo4j 엣지 동기화), CS-4-4 (heat_score)
> **산출물**:
> - `chainsight/services/expand_service.py`
> - WatchlistViewSet.expand() action 구현

---

## 배경

사용자가 Recheck 결과에서 `suggested_action: "expand"`를 받거나 직접 Expand 버튼을 누르면 "그 다음 경로로 어디로 갈 수 있나"를 보여준다.

경로 `NVDA → TSM → ASML`의 끝 노드 ASML에서 확장 가능한 후보: AMAT, LRCX, KLAC, ... 등 1-hop 이웃 중 이미 경로에 포함되지 않은 노드들.

**설계 원칙**: 단순 이웃 나열이 아니라 "탐색할 가치가 있는 순서"로 정렬. heat_score + truth_score + 관계 다양성을 고려.

---

## API 스펙

```
POST /api/chainsight/watchlist/{id}/expand/

Body: (선택)
  {
    "target_ticker": "ASML",   // 기본: path_nodes 마지막 노드
    "limit": 10                // 기본: 10
  }

Response:
  {
    "source_ticker": "ASML",
    "candidates": [
      {
        "ticker": "AMAT",
        "name": "Applied Materials",
        "sector": "Technology",
        "relation_type": "SUPPLIES_TO",
        "truth_score": 85,
        "relation_status": "confirmed",
        "heat_score": 0.72,
        "basis_summary": "반도체 장비 공급 공시 확인",
        "why_summary": "강한 공급망 연결 + 높은 heat_score"
      },
      ...
    ],
    "total_found": 23   // 전체 1-hop 이웃 수 (limit 적용 전)
  }
```

---

## 구현

### Service

```python
# chainsight/services/expand_service.py

from typing import List, Dict, Optional
from django.conf import settings
from chainsight.graph.repository import Neo4jGraphRepository


# 관계 타입별 우선순위 (같은 truth_score일 때 타이브레이커)
RELATION_PRIORITY = {
    'SUPPLIES_TO': 5,
    'COMPETES_WITH': 4,
    'HAS_THEME': 3,
    'PEER_OF': 2,
    'CO_MENTIONED': 1,
    'PRICE_CORRELATED': 0,
}


def find_expansion_candidates(
    source_ticker: str,
    excluded_tickers: List[str],
    limit: int = 10,
) -> Dict:
    """
    source_ticker에서 1-hop 이웃 중 excluded_tickers에 없는 노드들을 찾아
    탐색 가치 순으로 정렬 반환.

    Args:
        source_ticker: 확장 시작점 (경로 끝 노드)
        excluded_tickers: 이미 경로에 포함된 노드들 (중복 방지)
        limit: 반환할 최대 후보 수

    Returns:
        {
            'source_ticker': str,
            'candidates': [...],
            'total_found': int,
        }
    """
    repo = Neo4jGraphRepository(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD,
    )

    # 1-hop 이웃 + 관계 정보 + heat_score 조회
    # Truth 관계 confirmed/probable만 (v1.4 성능 가드레일)
    rows = repo.run_query(
        """
        MATCH (src:Stock {ticker: $source})-[r]-(neighbor:Stock)
        WHERE neighbor.ticker <> $source
          AND NOT neighbor.ticker IN $excluded
          AND (
            (r.status IN ['confirmed', 'probable'])
            OR type(r) IN ['PEER_OF']  // PEER_OF는 status 없이도 포함
          )
        WITH neighbor, r,
             type(r) AS rel_type,
             r.truth_score AS truth_score,
             r.status AS relation_status,
             r.relation_basis_summary AS basis_summary
        ORDER BY truth_score DESC NULLS LAST
        RETURN neighbor.ticker AS ticker,
               neighbor.name AS name,
               neighbor.sector AS sector,
               neighbor.heat_score AS heat_score,
               collect(DISTINCT {
                 rel_type: rel_type,
                 truth_score: truth_score,
                 status: relation_status,
                 basis_summary: basis_summary
               })[0] AS primary_relation,
               size(collect(DISTINCT rel_type)) AS relation_count
        LIMIT 100
        """,
        {'source': source_ticker, 'excluded': excluded_tickers}
    )

    total_found = len(rows)

    # Python에서 종합 점수 계산 + 정렬
    candidates = []
    for row in rows:
        rel = row['primary_relation']
        score = _compute_expansion_score(
            truth_score=rel.get('truth_score') or 0,
            heat_score=row.get('heat_score') or 0,
            rel_type=rel.get('rel_type') or '',
            relation_count=row.get('relation_count') or 1,
        )

        candidates.append({
            'ticker': row['ticker'],
            'name': row.get('name') or row['ticker'],
            'sector': row.get('sector') or '',
            'relation_type': rel.get('rel_type'),
            'truth_score': rel.get('truth_score'),
            'relation_status': rel.get('status'),
            'heat_score': row.get('heat_score'),
            'basis_summary': rel.get('basis_summary') or '',
            'why_summary': _build_why_summary(rel, row),
            '_score': score,  # 정렬 후 제거
        })

    # 정렬 후 limit 적용
    candidates.sort(key=lambda x: x['_score'], reverse=True)
    top = candidates[:limit]
    for c in top:
        del c['_score']

    return {
        'source_ticker': source_ticker,
        'candidates': top,
        'total_found': total_found,
    }


def _compute_expansion_score(
    truth_score: float,
    heat_score: float,
    rel_type: str,
    relation_count: int,
) -> float:
    """
    후보 정렬용 종합 점수.

    공식:
      0.40 × (truth_score / 100)
    + 0.30 × heat_score
    + 0.20 × (관계 타입 우선순위 / 5)
    + 0.10 × min(relation_count / 3, 1)  // 여러 관계로 연결될수록 신뢰
    """
    rel_priority = RELATION_PRIORITY.get(rel_type, 0)
    return (
        0.40 * (truth_score / 100.0)
        + 0.30 * heat_score
        + 0.20 * (rel_priority / 5.0)
        + 0.10 * min(relation_count / 3.0, 1.0)
    )


def _build_why_summary(relation: Dict, row: Dict) -> str:
    """간단한 why_summary 생성 (why_now_snapshot과는 다른, 카드 툴팁용)."""
    reasons = []

    status = relation.get('status')
    rel_type = relation.get('rel_type') or ''
    if status == 'confirmed':
        reasons.append(f'{rel_type} 확인됨')
    elif status == 'probable':
        reasons.append(f'{rel_type} 가능성 높음')

    heat = row.get('heat_score') or 0
    if heat >= 0.6:
        reasons.append('높은 시장 관심도')

    if not reasons:
        reasons.append('관련 노드')

    return ', '.join(reasons)
```

### ViewSet 액션

```python
# chainsight/views/watchlist_views.py (이어서)

from chainsight.services.expand_service import find_expansion_candidates


class WatchlistViewSet(viewsets.ModelViewSet):
    # ...

    @action(detail=True, methods=['post'])
    def expand(self, request, pk=None):
        """
        Expand 액션.

        Body (선택):
          { "target_ticker": "AMAT", "limit": 10 }

        Response:
          { "source_ticker": ..., "candidates": [...], "total_found": ... }
        """
        saved_path = self.get_object()

        if saved_path.status in (SavedPath.Status.ARCHIVED, SavedPath.Status.RESOLVED):
            return Response(
                {'detail': f'{saved_path.status} 상태에서는 Expand할 수 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target = request.data.get('target_ticker')
        if not target:
            target = saved_path.path_nodes[-1]  # 기본: 마지막 노드

        if target not in saved_path.path_nodes:
            return Response(
                {'detail': 'target_ticker가 경로에 포함되지 않습니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        limit = min(int(request.data.get('limit', 10)), 50)

        result = find_expansion_candidates(
            source_ticker=target,
            excluded_tickers=saved_path.path_nodes,
            limit=limit,
        )

        # 액션 로그
        PathAction.objects.create(
            saved_path=saved_path,
            action_type=PathAction.ActionType.EXPAND,
            metadata={
                'target_ticker': target,
                'candidates_count': len(result['candidates']),
                'top_candidates': [c['ticker'] for c in result['candidates'][:3]],
            }
        )

        return Response(result)
```

---

## 테스트

```python
# chainsight/tests/test_expand.py

import pytest
from chainsight.services.expand_service import (
    find_expansion_candidates,
    _compute_expansion_score,
)
from chainsight.models import SavedPath, PathAction


def test_compute_expansion_score_truth_weight():
    """truth_score가 높을수록 점수 높음."""
    high = _compute_expansion_score(
        truth_score=85, heat_score=0.5, rel_type='PEER_OF', relation_count=1
    )
    low = _compute_expansion_score(
        truth_score=35, heat_score=0.5, rel_type='PEER_OF', relation_count=1
    )
    assert high > low


def test_compute_expansion_score_relation_priority():
    """SUPPLIES_TO가 PEER_OF보다 우선."""
    supply = _compute_expansion_score(
        truth_score=60, heat_score=0.5, rel_type='SUPPLIES_TO', relation_count=1
    )
    peer = _compute_expansion_score(
        truth_score=60, heat_score=0.5, rel_type='PEER_OF', relation_count=1
    )
    assert supply > peer


@pytest.mark.django_db
def test_find_candidates_excludes_existing(mocker):
    """이미 경로에 있는 노드는 제외."""
    mocker.patch(
        'chainsight.services.expand_service.Neo4jGraphRepository'
    ).return_value.run_query.return_value = [
        {
            'ticker': 'AMAT', 'name': 'Applied Materials',
            'sector': 'Technology', 'heat_score': 0.7,
            'primary_relation': {
                'rel_type': 'SUPPLIES_TO', 'truth_score': 85,
                'status': 'confirmed', 'basis_summary': '공시 확인',
            },
            'relation_count': 2,
        },
    ]

    result = find_expansion_candidates(
        source_ticker='ASML',
        excluded_tickers=['NVDA', 'TSM', 'ASML'],
        limit=10,
    )

    # Neo4j 쿼리 호출 시 excluded가 전달됐는지 확인
    assert result['source_ticker'] == 'ASML'
    assert len(result['candidates']) == 1
    assert result['candidates'][0]['ticker'] == 'AMAT'
    assert '_score' not in result['candidates'][0]  # 내부 점수는 제거됨


@pytest.mark.django_db
def test_expand_api_success(client, mocker):
    path = SavedPath.objects.create(
        path_nodes=['NVDA', 'TSM', 'ASML'],
    )
    mocker.patch(
        'chainsight.services.expand_service.find_expansion_candidates',
        return_value={
            'source_ticker': 'ASML',
            'candidates': [{'ticker': 'AMAT', 'name': 'AMAT', 'sector': 'Tech'}],
            'total_found': 5,
        }
    )

    r = client.post(f'/api/chainsight/watchlist/{path.id}/expand/')
    assert r.status_code == 200
    assert r.data['source_ticker'] == 'ASML'
    assert len(r.data['candidates']) == 1

    # PathAction 기록
    actions = path.actions.filter(action_type='expand')
    assert actions.count() == 1
    assert actions.first().metadata['target_ticker'] == 'ASML'


@pytest.mark.django_db
def test_expand_invalid_target(client):
    path = SavedPath.objects.create(path_nodes=['NVDA', 'TSM'])
    r = client.post(
        f'/api/chainsight/watchlist/{path.id}/expand/',
        {'target_ticker': 'UNKNOWN'},
        format='json',
    )
    assert r.status_code == 400


@pytest.mark.django_db
def test_expand_archived_rejected(client):
    path = SavedPath.objects.create(
        path_nodes=['A', 'B'], status='archived',
    )
    r = client.post(f'/api/chainsight/watchlist/{path.id}/expand/')
    assert r.status_code == 400
```

---

## 완료 기준

```
□ expand_service.py 구현 (find_expansion_candidates)
□ Cypher 쿼리: 1-hop 이웃 + excluded 필터 + truth_score confirmed/probable
□ 종합 점수 공식 동작 (truth 40% + heat 30% + rel type 20% + count 10%)
□ 응답에 source_ticker, candidates, total_found 포함
□ 각 candidate에 ticker, name, sector, relation_type, truth_score, heat_score, why_summary
□ POST /watchlist/{id}/expand/ 기본값(마지막 노드) 동작
□ target_ticker 명시 동작 (경로 중간 노드에서도 확장 가능)
□ target_ticker가 경로에 없으면 400
□ archived/resolved 상태 거부
□ PathAction(EXPAND) 기록, metadata에 target + top_candidates
□ limit 파라미터 동작 (기본 10, 최대 50)
□ 6개 테스트 pass
```

---

## 주의사항

### total_found와 limit의 구분

`total_found`는 Cypher `LIMIT 100`에 걸리기 전까지의 실제 이웃 수를 반영하지 않는다. 대형 허브 노드(예: AAPL)는 1-hop 이웃이 100개 이상일 수 있음. UI에 "5/100+개 중" 같은 모호한 표시로 처리. 정확한 총계가 필요하면 별도 COUNT 쿼리 추가 (현재는 불필요).

### PEER_OF의 status 예외

PEER_OF는 RelationConfidence에서 `probable` 이상이 아니어도 Finnhub/FMP 소스가 있으면 저장됨. 그래서 Cypher WHERE에 `type(r) IN ['PEER_OF']` 예외 처리. 이렇게 해야 초기 데이터 부족 상황에서도 확장 후보가 나옴.

### 관계 여러 개가 한 쌍에 있을 때

A와 B가 PEER_OF이면서 동시에 CO_MENTIONED일 수 있음. 이때 Cypher의 `collect(DISTINCT ...)`으로 모두 수집하되, `primary_relation`은 truth_score 상위 1개만 사용. 나머지는 `relation_count`로만 반영. UI에서 필요하면 별도 쿼리로 전체 관계 조회 가능.

### Expand 후 실제 경로 추가

본 API는 **후보만 반환**. 사용자가 후보 중 하나를 선택해서 실제로 경로에 추가하는 건:
- 옵션 A: 새 SavedPath 생성 (기존 것 보존)
- 옵션 B: 기존 SavedPath의 path_nodes에 append

**MVP는 옵션 A**. 이유:
- 기존 경로를 수정하면 edge_snapshot 기준이 흔들림
- Recheck 결과가 의미 잃어버림
- PATCH/PUT을 막아둔 CS-6-2 정책과 일관

프론트엔드(CS-7-3)에서 Expand 후보 선택 시 "새 경로로 저장" POST /watchlist/ 호출. 원본 경로는 별도로 남음.

### heat_score 없는 노드

heat_score가 null이면 score 공식에서 0으로 처리. 확장 우선순위는 낮아지지만 배제되지는 않음. GDS 배치 실행 후 개선됨.

---

→ **다음**: CS-6-7 (Alternatives API)

**END OF DOCUMENT**
