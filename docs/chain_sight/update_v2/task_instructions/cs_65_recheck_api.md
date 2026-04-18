# CS-6-5: Recheck API

> **작업 번호**: CS-6-5
> **목표**: 저장된 경로의 현재 상태를 재평가하고, 강화/약화/끊김 신호를 headline과 suggested_action으로 돌려주는 API 구현
> **예상 소요**: 3~4일 (Phase 6의 가장 복잡한 작업)
> **선행 조건**:
> - CS-6-1 (SavedPath/PathAction 모델)
> - CS-6-2 (Watchlist CRUD, edge_snapshot 생성)
> - CS-6-3 (Summary path 생성) — summary_path를 업데이트할 때 필요
> - CS-3-2 (Neo4j 엣지 동기화 완료)
> - CS-2-4 (RelationConfidence 판정)
> **산출물**:
> - `chainsight/services/recheck_service.py` (6단계 로직)
> - WatchlistViewSet.recheck() action 구현 (CS-6-2에서 만든 뼈대에 채우기)

---

## 배경

Recheck는 Path Watchlist의 "살아있음"을 책임지는 핵심 기능이다. 저장된 경로가 시간이 지나면서 어떻게 변했는지 — 어떤 엣지가 강화됐고, 어떤 엣지가 약해지거나 끊겼는지 — 를 감지해서 사용자에게 "지금 뭘 해야 하는지" 제안한다.

**PM_DESIGN.md v1.2 섹션 12-2** 기준 출력 구조:
```json
{
  "headline": "공급망 구간 강화, 1개 엣지 약화",
  "strengthened": [...],
  "weakened": [...],
  "path_intact": true,
  "broken_edges": [],
  "suggested_action": "expand",
  "suggested_reason": "강화된 구간의 인접 노드를 탐색해볼 가치가 있습니다.",
  "updated_why_now": {...}
}
```

**v1.4 상태 전이 규칙** (PM_DESIGN.md 섹션 8-1 보수화):
- watching → active: Recheck 2회 이상 + created_at으로부터 24시간 경과

---

## 6단계 로직

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 저장된 edge_snapshot 불러오기                             │
│    └─ SavedPath.edge_snapshot (Watch 시점 / 지난 Recheck)   │
│                                                             │
│ 2. 현재 엣지 상태 조회 (Neo4j)                               │
│    └─ path_nodes 인접 쌍의 현재 relation_status/truth_score  │
│                                                             │
│ 3. 엣지별 변화 감지 (Diff)                                   │
│    └─ 각 엣지를 4개 버킷으로 분류:                           │
│       - strengthened: score 상승 or status 승격              │
│       - weakened: score 하락 or status 강등                  │
│       - unchanged: 동일                                      │
│       - broken: 관계 소실 or stale/hidden 전락              │
│                                                             │
│ 4. Headline 템플릿 생성                                      │
│    └─ 변화 패턴에 맞는 한 줄 요약                            │
│                                                             │
│ 5. suggested_action 결정                                     │
│    └─ expand / alternatives / archive / resolve / none       │
│                                                             │
│ 6. 부가 처리                                                 │
│    ├─ edge_snapshot 업데이트 (새 현재 상태로 덮어씀)         │
│    ├─ why_now_snapshot 갱신                                  │
│    ├─ PathAction(RECHECK) 기록                               │
│    ├─ recheck_count += 1                                     │
│    └─ 상태 전이 검사 (watching → active 조건)                │
└─────────────────────────────────────────────────────────────┘
```

---

## 구현

### Service Layer

```python
# chainsight/services/recheck_service.py

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django.db import transaction

from chainsight.models import SavedPath, PathAction
from chainsight.graph.repository import Neo4jGraphRepository


# ─────────────────────────────────────────────────────────
# 상수
# ─────────────────────────────────────────────────────────

STATUS_ORDER = {
    'hidden': 0,
    'stale': 1,
    'weak': 2,
    'probable': 3,
    'confirmed': 4,
}

# watching → active 전이 조건
ACTIVE_TRANSITION_RECHECK_COUNT = 2
ACTIVE_TRANSITION_HOURS = 24


# ─────────────────────────────────────────────────────────
# 데이터 클래스
# ─────────────────────────────────────────────────────────

@dataclass
class EdgeDiff:
    """한 엣지의 과거-현재 비교 결과."""
    from_ticker: str
    to_ticker: str
    rel_type: Optional[str]
    old_status: Optional[str]
    new_status: Optional[str]
    old_score: Optional[int]
    new_score: Optional[int]
    bucket: str  # 'strengthened' | 'weakened' | 'unchanged' | 'broken'


@dataclass
class RecheckResult:
    """Recheck 최종 출력."""
    headline: str = ''
    strengthened: List[Dict] = field(default_factory=list)
    weakened: List[Dict] = field(default_factory=list)
    unchanged: List[Dict] = field(default_factory=list)
    broken_edges: List[Dict] = field(default_factory=list)
    path_intact: bool = True
    suggested_action: str = 'none'
    suggested_reason: str = ''
    updated_why_now: Dict = field(default_factory=dict)
    new_edge_snapshot: List[Dict] = field(default_factory=list)


# ─────────────────────────────────────────────────────────
# 메인 엔트리
# ─────────────────────────────────────────────────────────

def run_recheck(saved_path: SavedPath) -> RecheckResult:
    """
    Recheck 6단계 로직 실행.
    DB 저장까지 수행 (트랜잭션 안에서).
    """
    # 1. 저장된 snapshot
    old_snapshot = saved_path.edge_snapshot or []

    # 2. 현재 상태 조회
    new_snapshot = _fetch_current_snapshot(saved_path.path_nodes)

    # 3. diff
    diffs = _compute_diffs(old_snapshot, new_snapshot)

    # 4. headline
    result = RecheckResult(
        new_edge_snapshot=new_snapshot,
        strengthened=[_diff_to_dict(d) for d in diffs if d.bucket == 'strengthened'],
        weakened=[_diff_to_dict(d) for d in diffs if d.bucket == 'weakened'],
        unchanged=[_diff_to_dict(d) for d in diffs if d.bucket == 'unchanged'],
        broken_edges=[_diff_to_dict(d) for d in diffs if d.bucket == 'broken'],
    )
    result.path_intact = not result.broken_edges
    result.headline = _build_headline(result)

    # 5. suggested_action
    result.suggested_action, result.suggested_reason = _decide_suggestion(
        result, saved_path
    )

    # 6. why_now 갱신
    result.updated_why_now = _build_updated_why_now(saved_path, result)

    # DB 저장 (트랜잭션)
    with transaction.atomic():
        saved_path.edge_snapshot = new_snapshot
        saved_path.why_now_snapshot = result.updated_why_now
        saved_path.recheck_count += 1

        # 상태 전이 검사
        _maybe_transition_to_active(saved_path)

        saved_path.save()

        # 액션 로그
        PathAction.objects.create(
            saved_path=saved_path,
            action_type=PathAction.ActionType.RECHECK,
            metadata={
                'strengthened': len(result.strengthened),
                'weakened': len(result.weakened),
                'broken': len(result.broken_edges),
                'suggested_action': result.suggested_action,
            }
        )

    return result


# ─────────────────────────────────────────────────────────
# 단계 구현
# ─────────────────────────────────────────────────────────

def _fetch_current_snapshot(path_nodes: List[str]) -> List[Dict]:
    """2단계: Neo4j에서 현재 엣지 상태 조회."""
    if len(path_nodes) < 2:
        return []

    repo = Neo4jGraphRepository(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD,
    )

    snapshot = []
    for i in range(len(path_nodes) - 1):
        a, b = path_nodes[i], path_nodes[i + 1]
        rows = repo.run_query(
            """
            MATCH (from:Stock {ticker: $a})-[r]-(to:Stock {ticker: $b})
            RETURN type(r) AS rel_type,
                   r.truth_score AS truth_score,
                   r.status AS status,
                   startNode(r).ticker AS start_ticker
            ORDER BY r.truth_score DESC NULLS LAST
            LIMIT 1
            """,
            {'a': a, 'b': b}
        )
        if rows:
            row = rows[0]
            snapshot.append({
                'from': row['start_ticker'],
                'to': b if row['start_ticker'] == a else a,
                'type': row['rel_type'],
                'truth_score': row['truth_score'],
                'status': row['status'],
            })
        else:
            snapshot.append({
                'from': a, 'to': b,
                'type': None, 'truth_score': None, 'status': 'hidden',
            })
    return snapshot


def _compute_diffs(old_snapshot: List[Dict],
                   new_snapshot: List[Dict]) -> List[EdgeDiff]:
    """
    3단계: 엣지 쌍별 diff.
    순서가 같다고 가정 (path_nodes 순서 고정).
    길이가 다르면 경고 로그 + 가능한 만큼만 비교.
    """
    import logging
    logger = logging.getLogger(__name__)

    diffs = []
    if len(old_snapshot) != len(new_snapshot):
        logger.warning(
            f'edge_snapshot 길이 불일치: old={len(old_snapshot)}, '
            f'new={len(new_snapshot)}. path_nodes 변경 의심.'
        )

    pairs = min(len(old_snapshot), len(new_snapshot))
    for i in range(pairs):
        old = old_snapshot[i]
        new = new_snapshot[i]

        bucket = _classify_edge_change(old, new)
        diffs.append(EdgeDiff(
            from_ticker=new.get('from', old.get('from')),
            to_ticker=new.get('to', old.get('to')),
            rel_type=new.get('type') or old.get('type'),
            old_status=old.get('status'),
            new_status=new.get('status'),
            old_score=old.get('truth_score'),
            new_score=new.get('truth_score'),
            bucket=bucket,
        ))
    return diffs


def _classify_edge_change(old: Dict, new: Dict) -> str:
    """
    엣지 하나를 4개 버킷으로 분류.

    우선순위:
    1. 관계 자체 소실 (type: value → None) → broken
    2. status 하락 (confirmed → hidden/stale) → broken or weakened
    3. status 상승 (weak → probable 등) → strengthened
    4. 점수 변동 → strengthened / weakened
    5. 동일 → unchanged
    """
    old_status = old.get('status')
    new_status = new.get('status')
    old_score = old.get('truth_score') or 0
    new_score = new.get('truth_score') or 0

    # broken: 관계 자체 끊김 (hidden/stale로 전락)
    if old_status in ('confirmed', 'probable', 'weak') and \
       new_status in ('hidden', 'stale'):
        return 'broken'

    # status 기반 비교 (우선)
    if old_status in STATUS_ORDER and new_status in STATUS_ORDER:
        old_rank = STATUS_ORDER[old_status]
        new_rank = STATUS_ORDER[new_status]
        if new_rank > old_rank:
            return 'strengthened'
        elif new_rank < old_rank:
            return 'weakened' if new_rank >= STATUS_ORDER['weak'] else 'broken'

    # 점수 기반 비교 (보조 — status 대표값이 비슷할 때 세부 차이 감지)
    score_delta = new_score - old_score
    if abs(score_delta) < 5:
        return 'unchanged'
    return 'strengthened' if score_delta > 0 else 'weakened'


def _build_headline(result: RecheckResult) -> str:
    """
    4단계: headline 템플릿.

    규칙:
    1. 모두 unchanged → "큰 변화 없음. 관계 유지."
    2. 강화만 있음 → "N개 구간 강화" (또는 "공급망/동종업계 등 주된 타입)
    3. 약화/끊김만 있음 → "N개 구간 약화" / "M개 구간 끊김"
    4. 혼합 → 주 패턴 + 부차 패턴
    """
    s = len(result.strengthened)
    w = len(result.weakened)
    b = len(result.broken_edges)
    u = len(result.unchanged)
    total = s + w + b + u

    if b > 0:
        # 끊김이 있으면 최우선 경고
        if b == total:
            return f'전 구간({b}개) 연결 끊김'
        if b > 0 and s > 0:
            return f'{b}개 구간 끊김, 다른 {s}개 구간은 강화'
        if b > 0 and w > 0:
            return f'{b}개 구간 끊김, {w}개 구간 약화 — 경로 재검토 필요'
        return f'{b}개 구간 연결 끊김'

    if s > 0 and w == 0:
        return f'{s}개 구간 강화 — 관계 활성 ↑'

    if w > 0 and s == 0:
        return f'{w}개 구간 약화'

    if s > 0 and w > 0:
        if s > w:
            return f'전반적 강화 ({s}개 ↑ / {w}개 ↓)'
        elif w > s:
            return f'전반적 약화 ({w}개 ↓ / {s}개 ↑)'
        else:
            return f'혼재 신호 ({s}개 ↑ / {w}개 ↓)'

    # 모두 unchanged
    return '큰 변화 없음 — 관계 유지'


def _decide_suggestion(result: RecheckResult,
                       saved_path: SavedPath) -> tuple[str, str]:
    """
    5단계: suggested_action 결정.

    우선순위:
    1. broken_edges 전부 → resolve or archive 권유
    2. broken_edges 일부 → alternatives (끊긴 노드 대안 찾기)
    3. strengthened 있음 → expand (강화된 구간 확장)
    4. weakened 있음 → recheck 반복 추적 또는 archive
    5. unchanged 모두 → 유지 (none)

    Returns:
        (action, reason) — 프론트엔드에 그대로 노출됨.
    """
    b = len(result.broken_edges)
    s = len(result.strengthened)
    w = len(result.weakened)
    total_edges = b + s + w + len(result.unchanged)

    if b == total_edges:
        return 'resolve', '전 구간이 끊어진 경로입니다. 전략 종료를 고려해보세요.'

    if b > 0:
        broken_nodes = set()
        for e in result.broken_edges:
            broken_nodes.add(e['from'])
            broken_nodes.add(e['to'])
        broken_list = ', '.join(sorted(broken_nodes)[:3])
        return 'alternatives', f'{broken_list} 주변에서 대체 경로를 탐색해보세요.'

    if s > 0 and w == 0:
        return 'expand', f'강화된 {s}개 구간의 인접 노드를 탐색해볼 가치가 있습니다.'

    if s > 0 and w > 0:
        if s >= w:
            return 'expand', '주 구간이 강화되는 중입니다. 확장을 고려해보세요.'
        else:
            return 'alternatives', '일부 구간이 약해지고 있습니다. 대안 경로를 살펴보세요.'

    if w > 0:
        # 약화만 있고 끊기진 않음
        if saved_path.recheck_count >= 3:
            # 3회 이상 Recheck했는데 계속 약화 → archive 권유
            return 'archive', '여러 차례 Recheck에서 약화 신호가 반복됩니다. 보관을 고려해보세요.'
        return 'none', '구간이 약해지는 중입니다. 며칠 후 다시 Recheck해보세요.'

    return 'none', '현재 큰 변화가 없습니다.'


def _build_updated_why_now(saved_path: SavedPath,
                            result: RecheckResult) -> Dict:
    """6단계의 일부: why_now_snapshot 갱신."""
    new_snapshot = result.new_edge_snapshot
    strong_count = sum(
        1 for e in new_snapshot
        if e.get('status') in ('confirmed', 'probable')
    )

    return {
        'headline': result.headline,
        'signals': [
            {'type': 'strengthened', 'count': len(result.strengthened)},
            {'type': 'weakened', 'count': len(result.weakened)},
            {'type': 'broken', 'count': len(result.broken_edges)},
        ],
        'generated_at': timezone.now().isoformat(),
        'strong_edges': strong_count,
        'total_edges': len(new_snapshot),
        'suggested_action': result.suggested_action,
    }


def _maybe_transition_to_active(saved_path: SavedPath) -> None:
    """
    watching → active 전이 조건:
    - recheck_count >= ACTIVE_TRANSITION_RECHECK_COUNT (이 함수 호출 시점에 이미 증가된 값 기준)
    - created_at으로부터 ACTIVE_TRANSITION_HOURS 경과

    호출 위치: run_recheck()에서 `recheck_count += 1` 이후, save() 이전.
    즉 여기서 보는 recheck_count는 "이번 Recheck 포함 누적 횟수".
    """
    if saved_path.status != SavedPath.Status.WATCHING:
        return

    if saved_path.recheck_count < ACTIVE_TRANSITION_RECHECK_COUNT:
        return

    age = timezone.now() - saved_path.created_at
    if age < timedelta(hours=ACTIVE_TRANSITION_HOURS):
        return

    saved_path.status = SavedPath.Status.ACTIVE


def _diff_to_dict(diff: EdgeDiff) -> Dict:
    """API 응답용 serialize."""
    return {
        'from': diff.from_ticker,
        'to': diff.to_ticker,
        'type': diff.rel_type,
        'old_status': diff.old_status,
        'new_status': diff.new_status,
        'old_score': diff.old_score,
        'new_score': diff.new_score,
    }
```

---

## ViewSet 액션 구현

CS-6-2에서 만든 WatchlistViewSet에 `recheck` action 추가:

```python
# chainsight/views/watchlist_views.py (이어서)

from chainsight.services.recheck_service import run_recheck


class WatchlistViewSet(viewsets.ModelViewSet):
    # ... (기존 메서드들)

    @action(detail=True, methods=['post'])
    def recheck(self, request, pk=None):
        """
        Recheck 액션.

        출력 예시:
        {
          "headline": "공급망 구간 강화, 1개 엣지 약화",
          "strengthened": [{"from": "NVDA", "to": "TSM", ...}],
          "weakened": [...],
          "unchanged": [...],
          "broken_edges": [],
          "path_intact": true,
          "suggested_action": "expand",
          "suggested_reason": "강화된 구간의 인접 노드를 탐색해볼 가치가 있습니다.",
          "updated_why_now": {...},
          "status": "watching"  // 또는 "active" (전이됐으면)
        }
        """
        saved_path = self.get_object()

        # 종료 상태는 Recheck 거부
        if saved_path.status in (SavedPath.Status.ARCHIVED, SavedPath.Status.RESOLVED):
            return Response(
                {'detail': f'{saved_path.status} 상태에서는 Recheck할 수 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = run_recheck(saved_path)

        # saved_path refresh (상태 전이 반영)
        saved_path.refresh_from_db()

        return Response({
            'headline': result.headline,
            'strengthened': result.strengthened,
            'weakened': result.weakened,
            'unchanged': result.unchanged,
            'broken_edges': result.broken_edges,
            'path_intact': result.path_intact,
            'suggested_action': result.suggested_action,
            'suggested_reason': result.suggested_reason,
            'updated_why_now': result.updated_why_now,
            'status': saved_path.status,
            'recheck_count': saved_path.recheck_count,
        })
```

---

## 테스트

```python
# chainsight/tests/test_recheck.py

import pytest
from unittest.mock import patch
from django.utils import timezone
from datetime import timedelta

from chainsight.models import SavedPath, PathAction
from chainsight.services.recheck_service import (
    run_recheck,
    _classify_edge_change,
    _build_headline,
    _decide_suggestion,
    RecheckResult,
)


# ─── 단위: _classify_edge_change ────────────────────────

def test_classify_strengthened_by_status():
    old = {'status': 'weak', 'truth_score': 35}
    new = {'status': 'probable', 'truth_score': 60}
    assert _classify_edge_change(old, new) == 'strengthened'


def test_classify_weakened_by_status():
    old = {'status': 'confirmed', 'truth_score': 85}
    new = {'status': 'probable', 'truth_score': 60}
    assert _classify_edge_change(old, new) == 'weakened'


def test_classify_broken():
    old = {'status': 'confirmed', 'truth_score': 85}
    new = {'status': 'stale', 'truth_score': None}
    assert _classify_edge_change(old, new) == 'broken'


def test_classify_unchanged():
    old = {'status': 'probable', 'truth_score': 60}
    new = {'status': 'probable', 'truth_score': 61}
    assert _classify_edge_change(old, new) == 'unchanged'


def test_classify_score_delta_strengthened():
    """status는 같은데 점수가 유의미하게 오른 경우"""
    old = {'status': 'probable', 'truth_score': 55}
    new = {'status': 'probable', 'truth_score': 70}
    assert _classify_edge_change(old, new) == 'strengthened'


# ─── 단위: _build_headline ──────────────────────────────

def test_headline_all_unchanged():
    r = RecheckResult(unchanged=[{}, {}, {}])
    assert '큰 변화 없음' in _build_headline(r)


def test_headline_strengthened_only():
    r = RecheckResult(strengthened=[{}, {}])
    h = _build_headline(r)
    assert '2개 구간 강화' in h


def test_headline_broken():
    r = RecheckResult(broken_edges=[{}])
    h = _build_headline(r)
    assert '끊김' in h


def test_headline_mixed():
    r = RecheckResult(strengthened=[{}, {}], weakened=[{}])
    h = _build_headline(r)
    assert '↑' in h or '강화' in h


# ─── 단위: _decide_suggestion ────────────────────────────

@pytest.mark.django_db
def test_suggestion_all_broken():
    path = SavedPath.objects.create(path_nodes=['A', 'B'])
    r = RecheckResult(broken_edges=[{}, {}])
    action, reason = _decide_suggestion(r, path)
    assert action == 'resolve'


@pytest.mark.django_db
def test_suggestion_some_broken():
    path = SavedPath.objects.create(path_nodes=['A', 'B', 'C'])
    r = RecheckResult(
        broken_edges=[{'from': 'A', 'to': 'B'}],
        unchanged=[{}],
    )
    action, reason = _decide_suggestion(r, path)
    assert action == 'alternatives'


@pytest.mark.django_db
def test_suggestion_strengthened():
    path = SavedPath.objects.create(path_nodes=['A', 'B'])
    r = RecheckResult(strengthened=[{}, {}])
    action, reason = _decide_suggestion(r, path)
    assert action == 'expand'


@pytest.mark.django_db
def test_suggestion_repeated_weak_archive():
    path = SavedPath.objects.create(path_nodes=['A', 'B'], recheck_count=3)
    r = RecheckResult(weakened=[{}])
    action, reason = _decide_suggestion(r, path)
    assert action == 'archive'


# ─── 통합: run_recheck ──────────────────────────────────

@pytest.mark.django_db
def test_run_recheck_basic_flow(mocker):
    old_snapshot = [
        {'from': 'NVDA', 'to': 'TSM', 'type': 'SUPPLIES_TO',
         'truth_score': 60, 'status': 'probable'}
    ]
    new_snapshot = [
        {'from': 'NVDA', 'to': 'TSM', 'type': 'SUPPLIES_TO',
         'truth_score': 85, 'status': 'confirmed'}
    ]

    mocker.patch(
        'chainsight.services.recheck_service._fetch_current_snapshot',
        return_value=new_snapshot,
    )

    path = SavedPath.objects.create(
        path_nodes=['NVDA', 'TSM'],
        edge_snapshot=old_snapshot,
        why_now_snapshot={'headline': '초기 상태', 'signals': []},
    )

    result = run_recheck(path)

    # 결과 검증
    assert len(result.strengthened) == 1
    assert len(result.weakened) == 0
    assert result.path_intact is True
    assert result.suggested_action == 'expand'
    assert '강화' in result.headline

    # DB 저장 확인
    path.refresh_from_db()
    assert path.edge_snapshot == new_snapshot
    assert path.recheck_count == 1
    assert path.why_now_snapshot['headline'] == result.headline

    # 액션 로그
    assert path.actions.filter(action_type='recheck').count() == 1
    action = path.actions.filter(action_type='recheck').first()
    assert action.metadata['strengthened'] == 1
    assert action.metadata['suggested_action'] == 'expand'


@pytest.mark.django_db
def test_watching_to_active_transition(mocker):
    """Recheck 2회 + 24시간 경과 → active"""
    mocker.patch(
        'chainsight.services.recheck_service._fetch_current_snapshot',
        return_value=[{'from': 'A', 'to': 'B', 'type': 'PEER_OF',
                       'truth_score': 60, 'status': 'probable'}],
    )

    # 25시간 전에 생성, 이미 Recheck 1회
    path = SavedPath.objects.create(
        path_nodes=['A', 'B'],
        edge_snapshot=[{'from': 'A', 'to': 'B', 'type': 'PEER_OF',
                        'truth_score': 60, 'status': 'probable'}],
        recheck_count=1,
    )
    SavedPath.objects.filter(pk=path.pk).update(
        created_at=timezone.now() - timedelta(hours=25)
    )
    path.refresh_from_db()

    # 2번째 Recheck → active 전이
    run_recheck(path)
    path.refresh_from_db()

    assert path.status == 'active'
    assert path.recheck_count == 2


@pytest.mark.django_db
def test_no_transition_if_too_soon(mocker):
    """Recheck 2회는 했지만 24시간 미경과 → watching 유지"""
    mocker.patch(
        'chainsight.services.recheck_service._fetch_current_snapshot',
        return_value=[{'from': 'A', 'to': 'B', 'type': 'PEER_OF',
                       'truth_score': 60, 'status': 'probable'}],
    )

    # 1시간 전에 생성, Recheck 1회
    path = SavedPath.objects.create(
        path_nodes=['A', 'B'],
        edge_snapshot=[{'from': 'A', 'to': 'B', 'type': 'PEER_OF',
                        'truth_score': 60, 'status': 'probable'}],
        recheck_count=1,
    )

    run_recheck(path)
    path.refresh_from_db()

    assert path.status == 'watching'  # 아직 전이 안 됨


@pytest.mark.django_db
def test_recheck_api_archived_rejected(client):
    path = SavedPath.objects.create(
        path_nodes=['A', 'B'], status='archived',
    )
    r = client.post(f'/api/chainsight/watchlist/{path.id}/recheck/')
    assert r.status_code == 400
    assert 'archived' in r.data['detail']


@pytest.mark.django_db
def test_recheck_api_full_response(client, mocker):
    mocker.patch(
        'chainsight.services.recheck_service._fetch_current_snapshot',
        return_value=[{'from': 'A', 'to': 'B', 'type': 'PEER_OF',
                       'truth_score': 85, 'status': 'confirmed'}],
    )
    path = SavedPath.objects.create(
        path_nodes=['A', 'B'],
        edge_snapshot=[{'from': 'A', 'to': 'B', 'type': 'PEER_OF',
                        'truth_score': 60, 'status': 'probable'}],
    )

    r = client.post(f'/api/chainsight/watchlist/{path.id}/recheck/')
    assert r.status_code == 200

    # 필수 필드 확인
    required = ['headline', 'strengthened', 'weakened', 'unchanged',
                'broken_edges', 'path_intact', 'suggested_action',
                'suggested_reason', 'updated_why_now', 'status',
                'recheck_count']
    for f in required:
        assert f in r.data

    assert r.data['recheck_count'] == 1
```

---

## 완료 기준

```
□ recheck_service.py 6단계 로직 구현 (run_recheck)
□ 엣지 분류 4버킷 동작 (strengthened/weakened/unchanged/broken)
□ headline 템플릿 5가지 케이스 처리 (all unchanged/강화만/약화만/끊김/혼합)
□ suggested_action 5가지 결정 로직 (resolve/alternatives/expand/archive/none)
□ POST /watchlist/{id}/recheck/ 엔드포인트 작동
□ edge_snapshot DB 업데이트 확인 (Recheck 이후 old → new)
□ why_now_snapshot 갱신 확인 (headline, signals, generated_at)
□ PathAction(RECHECK) 기록 확인 (metadata에 strengthened/weakened/broken/action)
□ recheck_count 증가 확인
□ watching → active 전이 조건 2가지 테스트 (2회+24h 만족, 미만)
□ archived/resolved 상태에서 Recheck 요청 시 400
□ 단위 테스트 + 통합 테스트 14개 pass
```

---

## 주의사항

### _fetch_current_snapshot의 Neo4j 부하

경로당 최대 9개 쿼리(10개 노드 - 1). 하나의 Recheck에서 9번 round-trip. 대체로 문제없지만, 다수 SavedPath를 동시에 Recheck하는 상황에서는 병목 가능.

개선 방향(v1.3):
- 여러 쌍을 한 Cypher 쿼리로 묶음 조회 (UNWIND + pair 파라미터)
- Neo4j connection pool 크기 조정

MVP에서는 그냥 순차 실행.

### Path의 path_nodes 변경 가정 없음

Recheck는 path_nodes가 **불변**이라고 가정한다. 만약 edge_snapshot 길이와 path_nodes - 1 이 다르면 스키마 불일치. CS-6-2에서 PATCH/PUT을 막았으므로 정상 경로에서는 문제 없지만, 직접 DB 수정 시 위험. 경고 로그만 남기고 가능한 부분만 비교.

### 짧은 간격 Recheck 방지

사용자가 1초에 10번 Recheck를 누르면 Neo4j 쿼리 폭주. MVP에서는 별도 rate limit 없음. 프론트엔드(CS-7-3)에서 버튼 debounce로 1차 방어. 필요 시 `last_recheck_at` 필드를 SavedPath에 추가하고 "3분 이내 재실행 금지" 같은 규칙 추가 가능.

### watching → active 전이 타이밍

현재 구현: `run_recheck()` 내 `_maybe_transition_to_active()`에서 처리. `recheck_count`를 먼저 +1 한 뒤 조건 체크한다는 점 주의. 즉 "이 Recheck가 2회째인가?"는 `recheck_count >= 2`로 판정.

함수 호출 순서:
```python
saved_path.recheck_count += 1           # 먼저 증가
_maybe_transition_to_active(saved_path) # 이후 체크
saved_path.save()                        # 한 번만 저장
```

### 자동 상태 전환 (strengthening/weakening/broken) 제외

PM_DESIGN.md 섹션 8-1에서 strengthening/weakening/broken 3개 상태는 v1.3으로 연기됨. 본 작업에서는 status 변경은 오직 watching → active 한 방향만. Recheck 결과가 아무리 broken이어도 status는 자동으로 변경되지 않음 (사용자가 Resolve/Archive 버튼을 눌러야 변경).

이유: 자동 전환은 사용자 혼란과 예상 못한 UI 변화를 유발. 명시적 액션 기반이 MVP에 맞음.

### suggested_action이 사용자 액션을 결정하지 않음

suggested_action은 **제안**이지 자동 실행이 아니다. 프론트엔드(CS-7-3)는 headline과 suggested_reason을 보여주고, 사용자가 직접 버튼을 눌러야 한다. 이렇게 분리해야 "AI가 마음대로 아카이브했다" 같은 불만을 방지.

### 대용량 경로 성능

path_nodes 10개 → 9개 엣지 diff + headline + suggestion + why_now 갱신. Neo4j 쿼리 외에는 전부 Python 메모리 연산. 응답시간 대부분은 Neo4j 왕복. 응답 시간 목표는 2초 이내.

Celery 비동기 처리? MVP에서는 동기 요청. 사용자가 Recheck를 누르고 결과를 바로 보는 게 UX상 자연스러움. 2초 이상 걸리면 그때 비동기 + 폴링 전환.

---

→ **다음**: cs_66 (Expand API) — CS-6-4(Archive/Resolve)는 cs_62에 포함 완료

**END OF DOCUMENT**
