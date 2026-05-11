# Phase 6: Path Watchlist API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** SavedPath/PathAction 모델 검증 후 Watchlist CRUD + Summary Path + Recheck + Expand + Alternatives API 6개를 순차 구현하여 M4(API + Watchlist 백엔드 완성) 달성

**Architecture:** DRF ViewSet(WatchlistViewSet) 하나에 CRUD + 4개 action(archive/resolve/recheck/expand/alternatives)을 집중. 각 action의 비즈니스 로직은 services/ 레이어에 분리. Neo4j 조회는 싱글턴 `get_graph_repository()` 사용.

**Tech Stack:** Django 5.1, DRF, PostgreSQL, Neo4j (Cypher), pytest + pytest-django + pytest-mock

---

## Critical Adaptation Notes (코드 작성 시 반드시 참조)

| 태스크 지시서 원문 | 실제 코드베이스 | 설명 |
|---|---|---|
| `Stock.objects.filter(ticker__in=...)` | `Stock.objects.filter(symbol__in=...)` | Stock PK는 `symbol` 필드 |
| `values_list('ticker', 'sector')` | `values_list('symbol', 'sector')` | 동일 |
| `Neo4jGraphRepository(uri=..., user=..., password=...)` | `get_graph_repository()` | 싱글턴 팩토리 사용 |
| `settings.NEO4J_URI/USER/PASSWORD` 직접 참조 | `from chainsight.graph import get_graph_repository` | 팩토리가 settings 참조를 캡슐화 |
| `/api/chainsight/watchlist/` | `/api/v1/chainsight/watchlist/` | config/urls.py가 `api/v1/` prefix 추가 |
| SavedPath PK = integer | SavedPath PK = UUID (`uuid.uuid4`) | 기존 모델이 UUID 사용 |
| `chainsight/models/path_watchlist.py` | `chainsight/models/saved_path.py` | 이미 이 이름으로 생성됨 |

---

## File Structure

### 새로 생성할 파일

| 파일 | 역할 |
|------|------|
| `chainsight/serializers/__init__.py` | Serializer 패키지 초기화 |
| `chainsight/serializers/path_watchlist.py` | SavedPath CRUD용 serializer 4개 |
| `chainsight/views/watchlist_views.py` | WatchlistViewSet (CRUD + actions) |
| `chainsight/views/__init__.py` | Views 패키지 초기화 |
| `chainsight/services/path_service.py` | edge_snapshot, path_signature, summary_path 생성 |
| `chainsight/services/recheck_service.py` | Recheck 6단계 로직 |
| `chainsight/services/expand_service.py` | Expand 후보 검색 + 정렬 |
| `chainsight/services/alternatives_service.py` | Alternatives 대안 검색 |
| `chainsight/management/commands/regenerate_summary_paths.py` | summary_path 일괄 재생성 |
| `tests/unit/chainsight/__init__.py` | 테스트 패키지 |
| `tests/unit/chainsight/test_path_watchlist_models.py` | CS-6-1 모델 테스트 |
| `tests/unit/chainsight/test_watchlist_api.py` | CS-6-2 CRUD API 테스트 |
| `tests/unit/chainsight/test_summary_path.py` | CS-6-3 Summary path 테스트 |
| `tests/unit/chainsight/test_recheck.py` | CS-6-5 Recheck 테스트 |
| `tests/unit/chainsight/test_expand.py` | CS-6-6 Expand 테스트 |
| `tests/unit/chainsight/test_alternatives.py` | CS-6-7 Alternatives 테스트 |

### 수정할 파일

| 파일 | 변경 내용 |
|------|----------|
| `chainsight/admin.py` | SavedPath, PathAction admin 등록 |
| `chainsight/api/urls.py` | DRF Router로 watchlist/ URL 추가 |
| `chainsight/services/__init__.py` | 새 서비스 export 추가 |

---

## Task 1: CS-6-1 — SavedPath/PathAction 모델 검증

**Files:**
- Read: `chainsight/models/saved_path.py`
- Modify: `chainsight/admin.py`
- Create: `tests/unit/chainsight/__init__.py`
- Create: `tests/unit/chainsight/test_path_watchlist_models.py`

- [ ] **Step 1: 마이그레이션 상태 확인**

Run: `python manage.py showmigrations chainsight`
Expected: `0006_add_savedpath_pathaction` 가 `[X]`로 표시

- [ ] **Step 2: 테이블/필드 존재 확인**

Run: `python manage.py dbshell -c "\d chainsight_saved_path" && python manage.py dbshell -c "\d chainsight_path_action"`
Expected: saved_path 12개 필드(id, user_id, path_nodes, summary_path, path_signature, edge_snapshot, why_now_snapshot, source_center, source_slot, status, recheck_count, created_at, updated_at), path_action 5개 필드(id, saved_path_id, action_type, created_at, metadata)

- [ ] **Step 3: 테스트 디렉토리 생성 + 모델 테스트 작성**

```python
# tests/unit/chainsight/__init__.py
# (empty)
```

```python
# tests/unit/chainsight/test_path_watchlist_models.py

import pytest
from django.core.exceptions import ValidationError
from chainsight.models import SavedPath, PathAction


@pytest.mark.django_db
class TestSavedPathModel:

    def test_create_minimal(self):
        """최소 필드로 생성 가능"""
        path = SavedPath.objects.create(path_nodes=['NVDA', 'TSM'])
        assert path.status == SavedPath.Status.WATCHING
        assert path.recheck_count == 0
        assert path.user is None

    def test_full_data_roundtrip(self):
        """JSONField 저장/조회 round-trip"""
        edge_snapshot = [
            {'from': 'NVDA', 'to': 'TSM', 'type': 'SUPPLIES_TO',
             'truth_score': 85, 'status': 'confirmed'}
        ]
        why_now = {
            'headline': '장비 체인 relevance 상승',
            'signals': [{'type': 'heat_score_up', 'delta': 0.12}],
            'generated_at': '2026-04-16T07:30:00Z',
        }
        path = SavedPath.objects.create(
            path_nodes=['NVDA', 'TSM'],
            summary_path=['NVDA', 'TSM'],
            path_signature='공급망 중심 · Technology',
            edge_snapshot=edge_snapshot,
            why_now_snapshot=why_now,
            source_center='NVDA',
            source_slot='exploration_trail',
        )
        reloaded = SavedPath.objects.get(pk=path.pk)
        assert reloaded.edge_snapshot == edge_snapshot
        assert reloaded.why_now_snapshot['headline'] == '장비 체인 relevance 상승'

    def test_ordering_by_updated_at(self):
        """기본 정렬: -updated_at"""
        p1 = SavedPath.objects.create(path_nodes=['A', 'B'])
        p2 = SavedPath.objects.create(path_nodes=['C', 'D'])
        ordered = list(SavedPath.objects.all()[:2])
        assert ordered[0].pk == p2.pk
        assert ordered[1].pk == p1.pk

    def test_invalid_status_rejected(self):
        """유효하지 않은 status는 full_clean에서 거부"""
        path = SavedPath(path_nodes=['A', 'B'], status='invalid_status')
        with pytest.raises(ValidationError):
            path.full_clean()


@pytest.mark.django_db
class TestPathActionModel:

    def test_create_action(self):
        """PathAction 생성 + 관계"""
        path = SavedPath.objects.create(path_nodes=['NVDA', 'TSM'])
        action = PathAction.objects.create(
            saved_path=path,
            action_type=PathAction.ActionType.WATCH,
            metadata={'source_slot': 'exploration_trail'},
        )
        assert path.actions.count() == 1
        assert path.actions.first().action_type == 'watch'

    def test_cascade_delete(self):
        """SavedPath 삭제 시 PathAction도 삭제"""
        path = SavedPath.objects.create(path_nodes=['NVDA', 'TSM'])
        PathAction.objects.create(saved_path=path, action_type='watch')
        path_id = path.pk
        path.delete()
        assert PathAction.objects.filter(saved_path_id=path_id).count() == 0
```

- [ ] **Step 4: 테스트 실행 — 6개 통과 확인**

Run: `python -m pytest tests/unit/chainsight/test_path_watchlist_models.py -v`
Expected: 6 passed

- [ ] **Step 5: Django Admin 등록**

`chainsight/admin.py` 하단에 추가:

```python
from .models import SavedPath, PathAction


@admin.register(SavedPath)
class SavedPathAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'path_signature',
                    'recheck_count', 'updated_at')
    list_filter = ('status', 'updated_at')
    search_fields = ('path_signature', 'source_center')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-updated_at',)


@admin.register(PathAction)
class PathActionAdmin(admin.ModelAdmin):
    list_display = ('id', 'saved_path', 'action_type', 'created_at')
    list_filter = ('action_type', 'created_at')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
```

- [ ] **Step 6: 커밋**

```bash
git add tests/unit/chainsight/ chainsight/admin.py
git commit -m "feat(chainsight): CS-6-1 SavedPath/PathAction 모델 검증 + admin 등록"
```

---

## Task 2: CS-6-2 — Watchlist CRUD API (Watch/List/Retrieve/Delete + Archive/Resolve)

**Files:**
- Create: `chainsight/serializers/__init__.py`
- Create: `chainsight/serializers/path_watchlist.py`
- Create: `chainsight/views/__init__.py`
- Create: `chainsight/views/watchlist_views.py`
- Create: `chainsight/services/path_service.py`
- Modify: `chainsight/services/__init__.py`
- Modify: `chainsight/api/urls.py`
- Create: `tests/unit/chainsight/test_watchlist_api.py`

### Step Group A: Serializers

- [ ] **Step 1: Serializer 패키지 생성**

```python
# chainsight/serializers/__init__.py
from .path_watchlist import (
    SavedPathListSerializer,
    SavedPathDetailSerializer,
    SavedPathCreateSerializer,
    PathActionSerializer,
)

__all__ = [
    'SavedPathListSerializer',
    'SavedPathDetailSerializer',
    'SavedPathCreateSerializer',
    'PathActionSerializer',
]
```

```python
# chainsight/serializers/path_watchlist.py

from rest_framework import serializers
from chainsight.models import SavedPath, PathAction


class PathActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PathAction
        fields = ['id', 'action_type', 'metadata', 'created_at']


class SavedPathListSerializer(serializers.ModelSerializer):
    """목록 화면용. summary만 내려줌."""

    latest_headline = serializers.SerializerMethodField()
    path_length = serializers.SerializerMethodField()

    class Meta:
        model = SavedPath
        fields = [
            'id', 'summary_path', 'path_signature', 'status',
            'latest_headline', 'recheck_count',
            'path_length',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_latest_headline(self, obj):
        if obj.why_now_snapshot and isinstance(obj.why_now_snapshot, dict):
            return obj.why_now_snapshot.get('headline', '')
        return ''

    def get_path_length(self, obj):
        return len(obj.path_nodes) if obj.path_nodes else 0


class SavedPathDetailSerializer(serializers.ModelSerializer):
    """상세 화면용. 전체 필드 + action 이력."""

    actions = PathActionSerializer(many=True, read_only=True)

    class Meta:
        model = SavedPath
        fields = [
            'id', 'path_nodes', 'summary_path', 'path_signature',
            'edge_snapshot', 'why_now_snapshot',
            'source_center', 'source_slot',
            'status', 'recheck_count',
            'created_at', 'updated_at',
            'actions',
        ]
        read_only_fields = [
            'id', 'summary_path', 'path_signature',
            'edge_snapshot', 'why_now_snapshot',
            'status', 'recheck_count',
            'created_at', 'updated_at', 'actions',
        ]


class SavedPathCreateSerializer(serializers.ModelSerializer):
    """Watch 입력용. path_nodes + source만 받음."""

    class Meta:
        model = SavedPath
        fields = ['path_nodes', 'source_center', 'source_slot']

    def validate_path_nodes(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('path_nodes는 리스트여야 합니다.')
        if len(value) < 2:
            raise serializers.ValidationError('경로는 최소 2개 노드 필요.')
        if len(value) > 10:
            raise serializers.ValidationError('경로는 최대 10개 노드까지.')
        for ticker in value:
            if not isinstance(ticker, str) or not ticker.isalpha() or not (1 <= len(ticker) <= 5):
                raise serializers.ValidationError(f'유효하지 않은 ticker: {ticker}')
        if len(set(value)) != len(value):
            raise serializers.ValidationError('경로 내 중복 ticker 불가.')
        return [t.upper() for t in value]
```

### Step Group B: Service Layer (path_service.py)

- [ ] **Step 2: path_service.py 생성**

```python
# chainsight/services/path_service.py

"""
Path Watchlist 서비스 — edge_snapshot, path_signature, why_now 생성.
CS-6-2 + CS-6-3 공유.
"""

from collections import Counter
from typing import Dict, List

from django.utils import timezone

from chainsight.graph import get_graph_repository
from stocks.models import Stock


# ─── 관계 라벨 매핑 ───────────────────────────
RELATION_LABEL = {
    'SUPPLIES_TO': '공급망 중심',
    'COMPETES_WITH': '경쟁 관계',
    'PEER_OF': '동종업계',
    'HAS_THEME': '테마 연결',
    'CO_MENTIONED': '뉴스 연동',
    'PRICE_CORRELATED': '가격 동조',
}


def build_edge_snapshot(path_nodes: List[str]) -> List[Dict]:
    """
    경로 내 인접 노드 쌍의 현재 관계 상태를 Neo4j에서 조회.

    Returns:
        [{"from": "NVDA", "to": "TSM", "type": "SUPPLIES_TO",
          "truth_score": 85, "status": "confirmed"}, ...]
    """
    if len(path_nodes) < 2:
        return []

    repo = get_graph_repository()
    snapshot = []

    for i in range(len(path_nodes) - 1):
        a, b = path_nodes[i], path_nodes[i + 1]
        result = repo.run_query(
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

        if result:
            row = result[0]
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


def build_path_signature(path_nodes: List[str], edge_snapshot: List[Dict]) -> str:
    """
    경로의 성격을 한 줄 태그로 압축.
    예: "공급망 중심 · Technology"
    """
    # 1) 관계 타입 빈도
    rel_counts = Counter(
        edge['type'] for edge in edge_snapshot if edge.get('type')
    )

    if not rel_counts:
        rel_label = '관계 미확정'
    elif len(rel_counts) == 1:
        dominant = rel_counts.most_common(1)[0][0]
        rel_label = RELATION_LABEL.get(dominant, dominant)
    else:
        top_two = rel_counts.most_common(2)
        total = sum(rel_counts.values())
        if top_two[0][1] / total >= 0.6:
            rel_label = RELATION_LABEL.get(top_two[0][0], top_two[0][0])
        else:
            rel_label = '복합 체인'

    # 2) 섹터 빈도 — Stock 모델의 PK는 symbol
    stocks = Stock.objects.filter(
        symbol__in=path_nodes
    ).values_list('symbol', 'sector')
    sector_map = dict(stocks)
    sector_counts = Counter(
        sector_map.get(t) for t in path_nodes if sector_map.get(t)
    )

    if not sector_counts:
        sector_label = ''
    else:
        sector_label = sector_counts.most_common(1)[0][0]

    if sector_label:
        return f'{rel_label} · {sector_label}'
    return rel_label


def build_initial_why_now(path_nodes: List[str], edge_snapshot: List[Dict]) -> Dict:
    """Watch 시점의 why_now_snapshot 초기값 생성."""
    strong_count = sum(
        1 for e in edge_snapshot
        if e.get('status') in ('confirmed', 'probable')
    )

    if strong_count == len(edge_snapshot) and strong_count > 0:
        headline = f'{len(path_nodes)}개 노드 전 구간 확인된 경로'
    elif strong_count >= len(edge_snapshot) * 0.6:
        headline = f'주요 구간 확인된 {len(path_nodes)}개 노드 경로'
    else:
        headline = f'{len(path_nodes)}개 노드 관찰 대상 경로'

    return {
        'headline': headline,
        'signals': [],
        'generated_at': timezone.now().isoformat(),
        'strong_edges': strong_count,
        'total_edges': len(edge_snapshot),
    }
```

### Step Group C: ViewSet

- [ ] **Step 3: views 패키지 + WatchlistViewSet 생성**

```python
# chainsight/views/__init__.py
# (empty)
```

```python
# chainsight/views/watchlist_views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from chainsight.models import SavedPath, PathAction
from chainsight.serializers.path_watchlist import (
    SavedPathListSerializer,
    SavedPathDetailSerializer,
    SavedPathCreateSerializer,
)
from chainsight.services.path_service import (
    build_edge_snapshot,
    build_path_signature,
    build_initial_why_now,
)


class WatchlistViewSet(viewsets.ModelViewSet):
    """
    Path Watchlist CRUD + 액션.

    GET    /watchlist/           → list
    POST   /watchlist/           → create (Watch)
    GET    /watchlist/{id}/      → retrieve
    DELETE /watchlist/{id}/      → destroy
    POST   /watchlist/{id}/archive/
    POST   /watchlist/{id}/resolve/
    POST   /watchlist/{id}/recheck/    (CS-6-5)
    POST   /watchlist/{id}/expand/     (CS-6-6)
    POST   /watchlist/{id}/alternatives/ (CS-6-7)
    """

    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        qs = SavedPath.objects.all()

        user = self.request.user if self.request.user.is_authenticated else None
        if user:
            qs = qs.filter(user=user)
        else:
            qs = qs.filter(user__isnull=True)

        status_param = self.request.query_params.get('status')
        if status_param:
            statuses = [s.strip() for s in status_param.split(',')]
            qs = qs.filter(status__in=statuses)

        return qs.prefetch_related('actions')

    def get_serializer_class(self):
        if self.action == 'list':
            return SavedPathListSerializer
        if self.action == 'create':
            return SavedPathCreateSerializer
        return SavedPathDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        path_nodes = validated['path_nodes']

        edge_snapshot = build_edge_snapshot(path_nodes)
        path_signature = build_path_signature(path_nodes, edge_snapshot)
        why_now = build_initial_why_now(path_nodes, edge_snapshot)

        # CS-6-3 에서 generate_summary_path 추가 예정; 일단 path_nodes 그대로
        summary_path = path_nodes

        user = request.user if request.user.is_authenticated else None

        saved_path = SavedPath.objects.create(
            user=user,
            path_nodes=path_nodes,
            summary_path=summary_path,
            path_signature=path_signature,
            edge_snapshot=edge_snapshot,
            why_now_snapshot=why_now,
            source_center=validated.get('source_center'),
            source_slot=validated.get('source_slot'),
            status=SavedPath.Status.WATCHING,
        )

        PathAction.objects.create(
            saved_path=saved_path,
            action_type=PathAction.ActionType.WATCH,
            metadata={
                'source_center': validated.get('source_center'),
                'source_slot': validated.get('source_slot'),
            }
        )

        response_serializer = SavedPathDetailSerializer(saved_path)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        saved_path = self.get_object()
        if saved_path.status == SavedPath.Status.ARCHIVED:
            return Response(
                {'detail': '이미 archived 상태입니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        saved_path.status = SavedPath.Status.ARCHIVED
        saved_path.save(update_fields=['status', 'updated_at'])

        PathAction.objects.create(
            saved_path=saved_path,
            action_type=PathAction.ActionType.ARCHIVE,
        )

        return Response(SavedPathDetailSerializer(saved_path).data)

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        saved_path = self.get_object()
        if saved_path.status == SavedPath.Status.RESOLVED:
            return Response(
                {'detail': '이미 resolved 상태입니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        saved_path.status = SavedPath.Status.RESOLVED
        saved_path.save(update_fields=['status', 'updated_at'])

        PathAction.objects.create(
            saved_path=saved_path,
            action_type=PathAction.ActionType.RESOLVE,
        )

        return Response(SavedPathDetailSerializer(saved_path).data)
```

### Step Group D: URL 라우팅

- [ ] **Step 4: URL 등록**

`chainsight/api/urls.py` 수정:

```python
# chainsight/api/urls.py

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ChainSightGraphView, ChainSightSuggestionView, ChainSightTraceView,
    SeedListView, SectorGraphView, NeighborGraphView, SignalFeedView,
)
from chainsight.views.watchlist_views import WatchlistViewSet

router = DefaultRouter()
router.register(r'watchlist', WatchlistViewSet, basename='watchlist')

urlpatterns = [
    # 마켓 뷰 (고정 경로 먼저)
    path('seeds/', SeedListView.as_view(), name='chainsight-seeds'),
    path('sector/<str:sector>/graph/', SectorGraphView.as_view(), name='chainsight-sector-graph'),
    path('signals/', SignalFeedView.as_view(), name='chainsight-signals'),
    path('trace/', ChainSightTraceView.as_view(), name='chainsight-trace'),

    # 동적 경로 (symbol 기반)
    path('<str:symbol>/neighbors/', NeighborGraphView.as_view(), name='chainsight-neighbors'),
    path('<str:symbol>/graph/', ChainSightGraphView.as_view(), name='chainsight-graph'),
    path('<str:symbol>/suggestions/', ChainSightSuggestionView.as_view(), name='chainsight-suggestions'),
] + router.urls
```

### Step Group E: 테스트

- [ ] **Step 5: CRUD API 테스트 작성**

```python
# tests/unit/chainsight/test_watchlist_api.py

import pytest
from rest_framework.test import APIClient
from chainsight.models import SavedPath, PathAction


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
def test_watch_success(client, mocker):
    """POST /watchlist/ 성공 케이스"""
    mocker.patch(
        'chainsight.services.path_service.build_edge_snapshot',
        return_value=[
            {'from': 'NVDA', 'to': 'TSM', 'type': 'SUPPLIES_TO',
             'truth_score': 85, 'status': 'confirmed'}
        ]
    )

    response = client.post('/api/v1/chainsight/watchlist/', {
        'path_nodes': ['NVDA', 'TSM'],
        'source_center': 'NVDA',
        'source_slot': 'exploration_trail',
    }, format='json')

    assert response.status_code == 201
    assert response.data['path_nodes'] == ['NVDA', 'TSM']
    assert len(response.data['edge_snapshot']) == 1
    assert response.data['path_signature']
    assert response.data['status'] == 'watching'
    assert len(response.data['actions']) == 1
    assert response.data['actions'][0]['action_type'] == 'watch'


@pytest.mark.django_db
def test_watch_validation_too_few(client):
    r = client.post('/api/v1/chainsight/watchlist/',
                     {'path_nodes': ['NVDA']}, format='json')
    assert r.status_code == 400


@pytest.mark.django_db
def test_watch_validation_duplicate(client):
    r = client.post('/api/v1/chainsight/watchlist/',
                     {'path_nodes': ['NVDA', 'NVDA']}, format='json')
    assert r.status_code == 400


@pytest.mark.django_db
def test_watch_validation_empty(client):
    r = client.post('/api/v1/chainsight/watchlist/', {}, format='json')
    assert r.status_code == 400


@pytest.mark.django_db
def test_list_filter_by_status(client):
    SavedPath.objects.create(path_nodes=['A', 'B'], status='watching')
    SavedPath.objects.create(path_nodes=['C', 'D'], status='archived')
    SavedPath.objects.create(path_nodes=['E', 'F'], status='resolved')

    r = client.get('/api/v1/chainsight/watchlist/?status=watching,archived')
    assert r.status_code == 200
    assert len(r.data) == 2


@pytest.mark.django_db
def test_list_default_ordering(client):
    p1 = SavedPath.objects.create(path_nodes=['A', 'B'])
    p2 = SavedPath.objects.create(path_nodes=['C', 'D'])

    r = client.get('/api/v1/chainsight/watchlist/')
    assert r.data[0]['id'] == str(p2.id)
    assert r.data[1]['id'] == str(p1.id)


@pytest.mark.django_db
def test_retrieve_with_actions(client):
    path = SavedPath.objects.create(path_nodes=['A', 'B'])
    PathAction.objects.create(saved_path=path, action_type='watch')
    PathAction.objects.create(saved_path=path, action_type='recheck')

    r = client.get(f'/api/v1/chainsight/watchlist/{path.id}/')
    assert r.status_code == 200
    assert len(r.data['actions']) == 2


@pytest.mark.django_db
def test_archive_action(client):
    path = SavedPath.objects.create(path_nodes=['A', 'B'], status='watching')
    r = client.post(f'/api/v1/chainsight/watchlist/{path.id}/archive/')
    assert r.status_code == 200
    assert r.data['status'] == 'archived'
    path.refresh_from_db()
    assert path.status == 'archived'


@pytest.mark.django_db
def test_archive_already_archived(client):
    path = SavedPath.objects.create(path_nodes=['A', 'B'], status='archived')
    r = client.post(f'/api/v1/chainsight/watchlist/{path.id}/archive/')
    assert r.status_code == 400


@pytest.mark.django_db
def test_delete(client):
    path = SavedPath.objects.create(path_nodes=['A', 'B'])
    r = client.delete(f'/api/v1/chainsight/watchlist/{path.id}/')
    assert r.status_code == 204
    assert not SavedPath.objects.filter(id=path.id).exists()
```

- [ ] **Step 6: 테스트 실행**

Run: `python -m pytest tests/unit/chainsight/test_watchlist_api.py -v`
Expected: 11 passed

- [ ] **Step 7: 커밋**

```bash
git add chainsight/serializers/ chainsight/views/ chainsight/services/path_service.py \
  chainsight/api/urls.py tests/unit/chainsight/test_watchlist_api.py
git commit -m "feat(chainsight): CS-6-2 Watchlist CRUD API + archive/resolve"
```

---

## Task 3: CS-6-3 — Summary Path 생성

**Files:**
- Modify: `chainsight/services/path_service.py` (generate_summary_path 추가)
- Modify: `chainsight/views/watchlist_views.py` (create에서 호출)
- Create: `chainsight/management/commands/regenerate_summary_paths.py`
- Create: `tests/unit/chainsight/test_summary_path.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/unit/chainsight/test_summary_path.py

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
    """7노드 경로 → 4개(시작 + landmark2 + 끝)로 압축."""
    mocker.patch(
        'chainsight.services.path_service._fetch_centrality',
        return_value={
            'B': {'pagerank': None, 'betweenness': None, 'degree': 10},
            'C': {'pagerank': None, 'betweenness': None, 'degree': 15},
            'D': {'pagerank': None, 'betweenness': None, 'degree': 8},
            'E': {'pagerank': None, 'betweenness': None, 'degree': 6},
            'F': {'pagerank': None, 'betweenness': None, 'degree': 7},
        }
    )
    mock_qs = mocker.MagicMock()
    mock_qs.values_list.return_value = [
        ('A', 'Tech'), ('B', 'Tech'), ('C', 'Tech'),
        ('D', 'Finance'), ('E', 'Tech'), ('F', 'Tech'), ('G', 'Tech'),
    ]
    mocker.patch('stocks.models.Stock.objects.filter', return_value=mock_qs)

    summary = generate_summary_path(['A', 'B', 'C', 'D', 'E', 'F', 'G'])
    assert summary[0] == 'A'
    assert summary[-1] == 'G'
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
        'B': {'degree': 10}, 'C': {'degree': 10}, 'D': {'degree': 10},
    }
    scores = _compute_bridge_scores(
        middle=['B', 'C', 'D'],
        full_path=['A', 'B', 'C', 'D', 'E'],
        centrality=centrality,
    )
    assert scores[1] > scores[0]
    assert scores[1] > scores[2]


def test_sector_uniqueness(mocker):
    mock_qs = mocker.MagicMock()
    mock_qs.values_list.return_value = [
        ('A', 'Tech'), ('B', 'Tech'), ('C', 'Healthcare'),
        ('D', 'Tech'), ('E', 'Tech')
    ]
    mocker.patch('stocks.models.Stock.objects.filter', return_value=mock_qs)

    scores = _compute_sector_uniqueness(
        middle=['B', 'C', 'D'],
        full_path=['A', 'B', 'C', 'D', 'E'],
    )
    assert scores[1] == 1.0        # Healthcare 유일
    assert scores[0] == pytest.approx(0.25)  # Tech 4개 중 하나


def test_null_centrality_fallback(mocker):
    """GDS 미실행 상태에서도 정상 동작"""
    mocker.patch(
        'chainsight.services.path_service._fetch_centrality',
        return_value={
            'B': {'pagerank': None, 'betweenness': None, 'degree': 5},
            'C': {'pagerank': None, 'betweenness': None, 'degree': 8},
            'D': {'pagerank': None, 'betweenness': None, 'degree': 4},
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
    assert len(summary) == 3  # 5노드 → landmark 1개
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `python -m pytest tests/unit/chainsight/test_summary_path.py -v`
Expected: FAIL (generate_summary_path 미정의)

- [ ] **Step 3: path_service.py에 summary path 함수 추가**

`chainsight/services/path_service.py` 하단에 추가:

```python
# ─── Summary Path (CS-6-3) ──────────────────────

def generate_summary_path(path_nodes: List[str]) -> List[str]:
    """
    5+ 노드 경로를 3~4개 landmark로 압축.
    4개 이하는 그대로 반환.
    """
    if len(path_nodes) <= 4:
        return list(path_nodes)

    middle = path_nodes[1:-1]
    total = len(path_nodes)
    k = 1 if total <= 6 else 2

    scores = compute_landmark_scores(middle, path_nodes)

    top_k_indices = sorted(
        range(len(middle)),
        key=lambda i: scores[i],
        reverse=True,
    )[:k]
    top_k_indices.sort()

    selected_middle = [middle[i] for i in top_k_indices]
    return [path_nodes[0]] + selected_middle + [path_nodes[-1]]


def compute_landmark_scores(middle_nodes: List[str],
                             full_path: List[str]) -> List[float]:
    """중간 노드들의 landmark_score를 계산."""
    if not middle_nodes:
        return []

    centrality = _fetch_centrality(middle_nodes)

    pagerank_valid = any(
        centrality.get(n, {}).get('pagerank') is not None for n in middle_nodes
    )
    betweenness_valid = any(
        centrality.get(n, {}).get('betweenness') is not None for n in middle_nodes
    )

    if pagerank_valid and betweenness_valid:
        w = {'pagerank': 0.25, 'betweenness': 0.20, 'bridge': 0.30, 'sector': 0.25}
    elif pagerank_valid:
        w = {'pagerank': 0.25, 'betweenness': 0.0, 'bridge': 0.50, 'sector': 0.25}
    elif betweenness_valid:
        w = {'pagerank': 0.0, 'betweenness': 0.20, 'bridge': 0.55, 'sector': 0.25}
    else:
        w = {'pagerank': 0.0, 'betweenness': 0.0, 'bridge': 0.75, 'sector': 0.25}

    pagerank_ranks = _normalize_rank(
        {n: centrality.get(n, {}).get('pagerank') or 0 for n in middle_nodes}
    )
    betweenness_ranks = _normalize_rank(
        {n: centrality.get(n, {}).get('betweenness') or 0 for n in middle_nodes}
    )
    bridge_scores = _compute_bridge_scores(middle_nodes, full_path, centrality)
    sector_scores = _compute_sector_uniqueness(middle_nodes, full_path)

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
    repo = get_graph_repository()
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
    """bridge_score = 0.5 * position_weight + 0.5 * degree_weight"""
    scores = []
    total_middle = len(middle)

    degrees = {n: centrality.get(n, {}).get('degree', 0) for n in middle}
    max_degree = max(degrees.values()) if degrees else 1
    if max_degree == 0:
        max_degree = 1

    for i, node in enumerate(middle):
        if total_middle == 1:
            position_weight = 1.0
        else:
            center = (total_middle - 1) / 2
            position_weight = 1.0 - abs(i - center) / center

        degree_weight = degrees[node] / max_degree
        scores.append(0.5 * position_weight + 0.5 * degree_weight)

    return scores


def _compute_sector_uniqueness(middle: List[str],
                                full_path: List[str]) -> List[float]:
    """경로 내 섹터 다양성 기여도."""
    stocks = Stock.objects.filter(
        symbol__in=full_path
    ).values_list('symbol', 'sector')
    sector_map = dict(stocks)
    path_sectors = [sector_map.get(t) for t in full_path if sector_map.get(t)]
    sector_counts = Counter(path_sectors)

    scores = []
    for node in middle:
        sector = sector_map.get(node)
        if sector is None:
            scores.append(0.5)
        else:
            scores.append(1.0 / sector_counts[sector])

    return scores
```

- [ ] **Step 4: WatchlistViewSet.create()에서 summary_path 호출 수정**

`chainsight/views/watchlist_views.py`의 import에 `generate_summary_path` 추가하고, create() 내의 summary_path 할당을 변경:

```python
# import 추가
from chainsight.services.path_service import (
    build_edge_snapshot,
    build_path_signature,
    build_initial_why_now,
    generate_summary_path,
)

# create() 내부에서 변경:
# 변경 전: summary_path = path_nodes
# 변경 후:
        summary_path = generate_summary_path(path_nodes)
```

- [ ] **Step 5: management command 생성**

```bash
mkdir -p chainsight/management/commands
touch chainsight/management/__init__.py
# __init__.py in commands/ already exists from previous commands
```

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
        self.stdout.write(self.style.SUCCESS(f'Regenerated {count} summary_paths.'))
```

- [ ] **Step 6: 테스트 실행 — 통과 확인**

Run: `python -m pytest tests/unit/chainsight/test_summary_path.py -v`
Expected: 7 passed

- [ ] **Step 7: 커밋**

```bash
git add chainsight/services/path_service.py chainsight/views/watchlist_views.py \
  chainsight/management/ tests/unit/chainsight/test_summary_path.py
git commit -m "feat(chainsight): CS-6-3 Summary path landmark 압축 알고리즘"
```

---

## Task 4: CS-6-5 — Recheck API (6단계 로직)

**Files:**
- Create: `chainsight/services/recheck_service.py`
- Modify: `chainsight/views/watchlist_views.py` (recheck action 추가)
- Create: `tests/unit/chainsight/test_recheck.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/unit/chainsight/test_recheck.py

import pytest
from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APIClient

from chainsight.models import SavedPath, PathAction
from chainsight.services.recheck_service import (
    run_recheck,
    _classify_edge_change,
    _build_headline,
    _decide_suggestion,
    RecheckResult,
)


@pytest.fixture
def client():
    return APIClient()


# ─── 단위: _classify_edge_change ────────────────

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
    old = {'status': 'probable', 'truth_score': 55}
    new = {'status': 'probable', 'truth_score': 70}
    assert _classify_edge_change(old, new) == 'strengthened'


# ─── 단위: _build_headline ──────────────────────

def test_headline_all_unchanged():
    r = RecheckResult(unchanged=[{}, {}, {}])
    assert '큰 변화 없음' in _build_headline(r)


def test_headline_strengthened_only():
    r = RecheckResult(strengthened=[{}, {}])
    assert '2개 구간 강화' in _build_headline(r)


def test_headline_broken():
    r = RecheckResult(broken_edges=[{}])
    assert '끊김' in _build_headline(r)


def test_headline_mixed():
    r = RecheckResult(strengthened=[{}, {}], weakened=[{}])
    h = _build_headline(r)
    assert '↑' in h or '강화' in h


# ─── 단위: _decide_suggestion ───────────────────

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


# ─── 통합: run_recheck ─────────────────────────

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

    assert len(result.strengthened) == 1
    assert result.path_intact is True
    assert result.suggested_action == 'expand'
    assert '강화' in result.headline

    path.refresh_from_db()
    assert path.edge_snapshot == new_snapshot
    assert path.recheck_count == 1
    assert path.actions.filter(action_type='recheck').count() == 1


@pytest.mark.django_db
def test_watching_to_active_transition(mocker):
    """Recheck 2회 + 24시간 경과 → active"""
    mocker.patch(
        'chainsight.services.recheck_service._fetch_current_snapshot',
        return_value=[{'from': 'A', 'to': 'B', 'type': 'PEER_OF',
                       'truth_score': 60, 'status': 'probable'}],
    )

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

    run_recheck(path)
    path.refresh_from_db()

    assert path.status == 'active'
    assert path.recheck_count == 2


@pytest.mark.django_db
def test_no_transition_if_too_soon(mocker):
    """24시간 미경과 → watching 유지"""
    mocker.patch(
        'chainsight.services.recheck_service._fetch_current_snapshot',
        return_value=[{'from': 'A', 'to': 'B', 'type': 'PEER_OF',
                       'truth_score': 60, 'status': 'probable'}],
    )

    path = SavedPath.objects.create(
        path_nodes=['A', 'B'],
        edge_snapshot=[{'from': 'A', 'to': 'B', 'type': 'PEER_OF',
                        'truth_score': 60, 'status': 'probable'}],
        recheck_count=1,
    )

    run_recheck(path)
    path.refresh_from_db()
    assert path.status == 'watching'


# ─── API 테스트 ─────────────────────────────────

@pytest.mark.django_db
def test_recheck_api_archived_rejected(client):
    path = SavedPath.objects.create(path_nodes=['A', 'B'], status='archived')
    r = client.post(f'/api/v1/chainsight/watchlist/{path.id}/recheck/')
    assert r.status_code == 400


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

    r = client.post(f'/api/v1/chainsight/watchlist/{path.id}/recheck/')
    assert r.status_code == 200

    required = ['headline', 'strengthened', 'weakened', 'unchanged',
                'broken_edges', 'path_intact', 'suggested_action',
                'suggested_reason', 'updated_why_now', 'status',
                'recheck_count']
    for f in required:
        assert f in r.data

    assert r.data['recheck_count'] == 1
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `python -m pytest tests/unit/chainsight/test_recheck.py -v`
Expected: FAIL

- [ ] **Step 3: recheck_service.py 구현**

```python
# chainsight/services/recheck_service.py

"""
Recheck 6단계 로직 — CS-6-5
1. 저장된 edge_snapshot 불러오기
2. 현재 엣지 상태 조회 (Neo4j)
3. 엣지별 변화 감지 (Diff)
4. Headline 템플릿 생성
5. suggested_action 결정
6. DB 업데이트 (edge_snapshot, why_now, recheck_count, 상태 전이)
"""

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Dict, List, Optional

from django.db import transaction
from django.utils import timezone

from chainsight.graph import get_graph_repository
from chainsight.models import PathAction, SavedPath

logger = logging.getLogger(__name__)

# ─── 상수 ──────────────────────────────────────

STATUS_ORDER = {
    'hidden': 0,
    'stale': 1,
    'weak': 2,
    'probable': 3,
    'confirmed': 4,
}

ACTIVE_TRANSITION_RECHECK_COUNT = 2
ACTIVE_TRANSITION_HOURS = 24


# ─── 데이터 클래스 ─────────────────────────────

@dataclass
class EdgeDiff:
    from_ticker: str
    to_ticker: str
    rel_type: Optional[str]
    old_status: Optional[str]
    new_status: Optional[str]
    old_score: Optional[int]
    new_score: Optional[int]
    bucket: str  # strengthened | weakened | unchanged | broken


@dataclass
class RecheckResult:
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


# ─── 메인 엔트리 ───────────────────────────────

def run_recheck(saved_path: SavedPath) -> RecheckResult:
    """Recheck 6단계 로직. DB 저장까지 수행."""
    old_snapshot = saved_path.edge_snapshot or []
    new_snapshot = _fetch_current_snapshot(saved_path.path_nodes)
    diffs = _compute_diffs(old_snapshot, new_snapshot)

    result = RecheckResult(
        new_edge_snapshot=new_snapshot,
        strengthened=[_diff_to_dict(d) for d in diffs if d.bucket == 'strengthened'],
        weakened=[_diff_to_dict(d) for d in diffs if d.bucket == 'weakened'],
        unchanged=[_diff_to_dict(d) for d in diffs if d.bucket == 'unchanged'],
        broken_edges=[_diff_to_dict(d) for d in diffs if d.bucket == 'broken'],
    )
    result.path_intact = not result.broken_edges
    result.headline = _build_headline(result)
    result.suggested_action, result.suggested_reason = _decide_suggestion(
        result, saved_path
    )
    result.updated_why_now = _build_updated_why_now(saved_path, result)

    with transaction.atomic():
        saved_path.edge_snapshot = new_snapshot
        saved_path.why_now_snapshot = result.updated_why_now
        saved_path.recheck_count += 1
        _maybe_transition_to_active(saved_path)
        saved_path.save()

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


# ─── 단계 구현 ─────────────────────────────────

def _fetch_current_snapshot(path_nodes: List[str]) -> List[Dict]:
    """2단계: Neo4j에서 현재 엣지 상태 조회."""
    if len(path_nodes) < 2:
        return []

    repo = get_graph_repository()
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
    """3단계: 엣지 쌍별 diff."""
    diffs = []
    if len(old_snapshot) != len(new_snapshot):
        logger.warning(
            f'edge_snapshot 길이 불일치: old={len(old_snapshot)}, '
            f'new={len(new_snapshot)}'
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
    """엣지 하나를 4개 버킷으로 분류."""
    old_status = old.get('status')
    new_status = new.get('status')
    old_score = old.get('truth_score') or 0
    new_score = new.get('truth_score') or 0

    if old_status in ('confirmed', 'probable', 'weak') and \
       new_status in ('hidden', 'stale'):
        return 'broken'

    if old_status in STATUS_ORDER and new_status in STATUS_ORDER:
        old_rank = STATUS_ORDER[old_status]
        new_rank = STATUS_ORDER[new_status]
        if new_rank > old_rank:
            return 'strengthened'
        elif new_rank < old_rank:
            return 'weakened' if new_rank >= STATUS_ORDER['weak'] else 'broken'

    score_delta = new_score - old_score
    if abs(score_delta) < 5:
        return 'unchanged'
    return 'strengthened' if score_delta > 0 else 'weakened'


def _build_headline(result: RecheckResult) -> str:
    """4단계: headline 템플릿."""
    s = len(result.strengthened)
    w = len(result.weakened)
    b = len(result.broken_edges)
    total = s + w + b + len(result.unchanged)

    if b > 0:
        if b == total:
            return f'전 구간({b}개) 연결 끊김'
        if s > 0:
            return f'{b}개 구간 끊김, 다른 {s}개 구간은 강화'
        if w > 0:
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

    return '큰 변화 없음 — 관계 유지'


def _decide_suggestion(result: RecheckResult,
                       saved_path: SavedPath) -> tuple[str, str]:
    """5단계: suggested_action 결정."""
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
        if saved_path.recheck_count >= 3:
            return 'archive', '여러 차례 Recheck에서 약화 신호가 반복됩니다. 보관을 고려해보세요.'
        return 'none', '구간이 약해지는 중입니다. 며칠 후 다시 Recheck해보세요.'

    return 'none', '현재 큰 변화가 없습니다.'


def _build_updated_why_now(saved_path: SavedPath,
                            result: RecheckResult) -> Dict:
    """6단계: why_now_snapshot 갱신."""
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
    """watching → active 전이 조건 체크."""
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

- [ ] **Step 4: ViewSet에 recheck action 추가**

`chainsight/views/watchlist_views.py`에 추가:

```python
# import 추가
from chainsight.services.recheck_service import run_recheck

# WatchlistViewSet 내부에 추가:
    @action(detail=True, methods=['post'])
    def recheck(self, request, pk=None):
        saved_path = self.get_object()

        if saved_path.status in (SavedPath.Status.ARCHIVED, SavedPath.Status.RESOLVED):
            return Response(
                {'detail': f'{saved_path.status} 상태에서는 Recheck할 수 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = run_recheck(saved_path)
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

- [ ] **Step 5: 테스트 실행 — 14개 통과**

Run: `python -m pytest tests/unit/chainsight/test_recheck.py -v`
Expected: 14 passed

- [ ] **Step 6: 커밋**

```bash
git add chainsight/services/recheck_service.py chainsight/views/watchlist_views.py \
  tests/unit/chainsight/test_recheck.py
git commit -m "feat(chainsight): CS-6-5 Recheck API 6단계 로직 (diff/headline/suggestion/transition)"
```

---

## Task 5: CS-6-6 — Expand API

**Files:**
- Create: `chainsight/services/expand_service.py`
- Modify: `chainsight/views/watchlist_views.py` (expand action 추가)
- Create: `tests/unit/chainsight/test_expand.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/unit/chainsight/test_expand.py

import pytest
from rest_framework.test import APIClient

from chainsight.services.expand_service import (
    find_expansion_candidates,
    _compute_expansion_score,
)
from chainsight.models import SavedPath, PathAction


@pytest.fixture
def client():
    return APIClient()


def test_expansion_score_truth_weight():
    """truth_score가 높을수록 점수 높음."""
    high = _compute_expansion_score(
        truth_score=85, heat_score=0.5, rel_type='PEER_OF', relation_count=1
    )
    low = _compute_expansion_score(
        truth_score=35, heat_score=0.5, rel_type='PEER_OF', relation_count=1
    )
    assert high > low


def test_expansion_score_relation_priority():
    """SUPPLIES_TO > PEER_OF"""
    supply = _compute_expansion_score(
        truth_score=60, heat_score=0.5, rel_type='SUPPLIES_TO', relation_count=1
    )
    peer = _compute_expansion_score(
        truth_score=60, heat_score=0.5, rel_type='PEER_OF', relation_count=1
    )
    assert supply > peer


@pytest.mark.django_db
def test_find_candidates_mock(mocker):
    mock_repo = mocker.MagicMock()
    mock_repo.run_query.return_value = [
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
    mocker.patch(
        'chainsight.services.expand_service.get_graph_repository',
        return_value=mock_repo,
    )

    result = find_expansion_candidates(
        source_ticker='ASML',
        excluded_tickers=['NVDA', 'TSM', 'ASML'],
        limit=10,
    )

    assert result['source_ticker'] == 'ASML'
    assert len(result['candidates']) == 1
    assert result['candidates'][0]['ticker'] == 'AMAT'
    assert '_score' not in result['candidates'][0]


@pytest.mark.django_db
def test_expand_api_success(client, mocker):
    path = SavedPath.objects.create(path_nodes=['NVDA', 'TSM', 'ASML'])
    mocker.patch(
        'chainsight.views.watchlist_views.find_expansion_candidates',
        return_value={
            'source_ticker': 'ASML',
            'candidates': [{'ticker': 'AMAT', 'name': 'AMAT', 'sector': 'Tech'}],
            'total_found': 5,
        }
    )

    r = client.post(f'/api/v1/chainsight/watchlist/{path.id}/expand/')
    assert r.status_code == 200
    assert r.data['source_ticker'] == 'ASML'

    actions = path.actions.filter(action_type='expand')
    assert actions.count() == 1
    assert actions.first().metadata['target_ticker'] == 'ASML'


@pytest.mark.django_db
def test_expand_invalid_target(client):
    path = SavedPath.objects.create(path_nodes=['NVDA', 'TSM'])
    r = client.post(
        f'/api/v1/chainsight/watchlist/{path.id}/expand/',
        {'target_ticker': 'UNKNOWN'},
        format='json',
    )
    assert r.status_code == 400


@pytest.mark.django_db
def test_expand_archived_rejected(client):
    path = SavedPath.objects.create(path_nodes=['A', 'B'], status='archived')
    r = client.post(f'/api/v1/chainsight/watchlist/{path.id}/expand/')
    assert r.status_code == 400
```

- [ ] **Step 2: expand_service.py 구현**

```python
# chainsight/services/expand_service.py

"""Expand API 서비스 — CS-6-6"""

from typing import Dict, List

from chainsight.graph import get_graph_repository

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
    """source_ticker에서 1-hop 확장 후보를 탐색 가치 순으로 정렬 반환."""
    repo = get_graph_repository()

    rows = repo.run_query(
        """
        MATCH (src:Stock {ticker: $source})-[r]-(neighbor:Stock)
        WHERE neighbor.ticker <> $source
          AND NOT neighbor.ticker IN $excluded
          AND (
            r.status IN ['confirmed', 'probable']
            OR type(r) = 'PEER_OF'
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
            '_score': score,
        })

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
    """종합 점수: truth 40% + heat 30% + rel_type 20% + count 10%"""
    rel_priority = RELATION_PRIORITY.get(rel_type, 0)
    return (
        0.40 * (truth_score / 100.0)
        + 0.30 * heat_score
        + 0.20 * (rel_priority / 5.0)
        + 0.10 * min(relation_count / 3.0, 1.0)
    )


def _build_why_summary(relation: Dict, row: Dict) -> str:
    """카드 툴팁용 why_summary."""
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

- [ ] **Step 3: ViewSet에 expand action 추가**

`chainsight/views/watchlist_views.py`에 추가:

```python
# import 추가
from chainsight.services.expand_service import find_expansion_candidates

# WatchlistViewSet 내부에 추가:
    @action(detail=True, methods=['post'])
    def expand(self, request, pk=None):
        saved_path = self.get_object()

        if saved_path.status in (SavedPath.Status.ARCHIVED, SavedPath.Status.RESOLVED):
            return Response(
                {'detail': f'{saved_path.status} 상태에서는 Expand할 수 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target = request.data.get('target_ticker')
        if not target:
            target = saved_path.path_nodes[-1]

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

- [ ] **Step 4: 테스트 실행 — 6개 통과**

Run: `python -m pytest tests/unit/chainsight/test_expand.py -v`
Expected: 6 passed

- [ ] **Step 5: 커밋**

```bash
git add chainsight/services/expand_service.py chainsight/views/watchlist_views.py \
  tests/unit/chainsight/test_expand.py
git commit -m "feat(chainsight): CS-6-6 Expand API (1-hop 확장 후보 + 종합 점수 정렬)"
```

---

## Task 6: CS-6-7 — Alternatives API

**Files:**
- Create: `chainsight/services/alternatives_service.py`
- Modify: `chainsight/views/watchlist_views.py` (alternatives action 추가)
- Create: `tests/unit/chainsight/test_alternatives.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/unit/chainsight/test_alternatives.py

import pytest
from rest_framework.test import APIClient

from chainsight.services.alternatives_service import find_alternatives
from chainsight.models import SavedPath, PathAction


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
def test_find_alternatives_middle_node(mocker):
    """중간 노드의 양옆 고려."""
    mock_repo = mocker.MagicMock()
    mock_repo.run_query.side_effect = [
        [{'rel_type': 'SUPPLIES_TO', 'truth_score': 85, 'status': 'confirmed'}],
        [{'rel_type': 'COMPETES_WITH', 'truth_score': 60, 'status': 'probable'}],
        [
            {'ticker': 'KLAC', 'name': 'KLA', 'sector': 'Tech',
             'industry': 'Semi', 'heat_score': 0.6, 'overlap': 2,
             'rel_before': {'rel_type': 'SUPPLIES_TO', 'truth_score': 80, 'status': 'probable'},
             'rel_after': {'rel_type': 'COMPETES_WITH', 'truth_score': 55, 'status': 'probable'}},
        ],
    ]
    mocker.patch(
        'chainsight.services.alternatives_service.get_graph_repository',
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
    assert result['alternatives'][0]['overlap_count'] == 2


@pytest.mark.django_db
def test_find_alternatives_start_node(mocker):
    """시작 노드는 after만 고려."""
    mock_repo = mocker.MagicMock()
    mock_repo.run_query.side_effect = [
        [{'rel_type': 'SUPPLIES_TO', 'truth_score': 85, 'status': 'confirmed'}],
        [
            {'ticker': 'AAPL', 'name': 'Apple', 'sector': 'Tech',
             'industry': 'Consumer', 'heat_score': 0.5,
             'truth_score': 80, 'status': 'probable'}
        ],
    ]
    mocker.patch(
        'chainsight.services.alternatives_service.get_graph_repository',
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
        'chainsight.views.watchlist_views.find_alternatives',
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
        f'/api/v1/chainsight/watchlist/{path.id}/alternatives/',
        {'target_ticker': 'AMAT'},
        format='json',
    )
    assert r.status_code == 200
    assert r.data['target_ticker'] == 'AMAT'

    actions = path.actions.filter(action_type='alternatives')
    assert actions.count() == 1
    assert actions.first().metadata['target_ticker'] == 'AMAT'


@pytest.mark.django_db
def test_alternatives_missing_target(client):
    path = SavedPath.objects.create(path_nodes=['A', 'B'])
    r = client.post(
        f'/api/v1/chainsight/watchlist/{path.id}/alternatives/',
        {},
        format='json',
    )
    assert r.status_code == 400


@pytest.mark.django_db
def test_alternatives_target_not_in_path(client):
    path = SavedPath.objects.create(path_nodes=['A', 'B'])
    r = client.post(
        f'/api/v1/chainsight/watchlist/{path.id}/alternatives/',
        {'target_ticker': 'XYZ'},
        format='json',
    )
    assert r.status_code == 400
```

- [ ] **Step 2: alternatives_service.py 구현**

```python
# chainsight/services/alternatives_service.py

"""Alternatives API 서비스 — CS-6-7"""

from typing import Dict, List, Optional

from chainsight.graph import get_graph_repository


def find_alternatives(
    path_nodes: List[str],
    target_ticker: str,
    limit: int = 10,
) -> Dict:
    """path_nodes 안의 target_ticker를 대체할 수 있는 대안 노드들을 찾는다."""
    if target_ticker not in path_nodes:
        raise ValueError(f'{target_ticker} not in path')

    idx = path_nodes.index(target_ticker)
    before = path_nodes[idx - 1] if idx > 0 else None
    after = path_nodes[idx + 1] if idx < len(path_nodes) - 1 else None

    if before is None and after is None:
        return {
            'target_ticker': target_ticker,
            'neighbor_constraints': {'before': None, 'after': None},
            'alternatives': [],
            'total_found': 0,
        }

    repo = get_graph_repository()

    before_rel = _fetch_relation(repo, before, target_ticker) if before else None
    after_rel = _fetch_relation(repo, target_ticker, after) if after else None

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
        'total_found': len(alternatives),
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
    return rows[0] if rows else None


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
    if before_ticker and after_ticker:
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
    rows = repo.run_query(
        """
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
    elif rel_before:
        why = '앞쪽 노드와 같은 관계 유형'
    elif rel_after:
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

- [ ] **Step 3: ViewSet에 alternatives action 추가**

`chainsight/views/watchlist_views.py`에 추가:

```python
# import 추가
from chainsight.services.alternatives_service import find_alternatives

# WatchlistViewSet 내부에 추가:
    @action(detail=True, methods=['post'])
    def alternatives(self, request, pk=None):
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

- [ ] **Step 4: 테스트 실행 — 6개 통과**

Run: `python -m pytest tests/unit/chainsight/test_alternatives.py -v`
Expected: 6 passed

- [ ] **Step 5: 전체 테스트 실행 — 43개 통과**

Run: `python -m pytest tests/unit/chainsight/ -v`
Expected: 43 passed (6+11+7+14+6+6 = 50개 — 중복 fixture 제외 시 조정 가능)

- [ ] **Step 6: 커밋**

```bash
git add chainsight/services/alternatives_service.py chainsight/views/watchlist_views.py \
  tests/unit/chainsight/test_alternatives.py
git commit -m "feat(chainsight): CS-6-7 Alternatives API (노드 대안 탐색) — M4 달성"
```

---

## Final Endpoints Summary

| Method | URL | 작업 |
|--------|-----|------|
| POST | `/api/v1/chainsight/watchlist/` | Watch (경로 저장) |
| GET | `/api/v1/chainsight/watchlist/` | 목록 |
| GET | `/api/v1/chainsight/watchlist/{uuid}/` | 상세 |
| DELETE | `/api/v1/chainsight/watchlist/{uuid}/` | 삭제 |
| POST | `/api/v1/chainsight/watchlist/{uuid}/archive/` | Archive |
| POST | `/api/v1/chainsight/watchlist/{uuid}/resolve/` | Resolve |
| POST | `/api/v1/chainsight/watchlist/{uuid}/recheck/` | Recheck |
| POST | `/api/v1/chainsight/watchlist/{uuid}/expand/` | Expand |
| POST | `/api/v1/chainsight/watchlist/{uuid}/alternatives/` | Alternatives |
