# CS-6-2: Watchlist CRUD API

> **작업 번호**: CS-6-2
> **목표**: Path Watchlist의 생성(Watch), 조회(목록/상세), 삭제를 담당하는 DRF ViewSet 구현. Watch 시점에 edge_snapshot/path_signature/summary_path 자동 생성.
> **예상 소요**: 2~3일
> **선행 조건**:
> - CS-6-1 (SavedPath/PathAction 모델 검증 완료)
> - CS-3-2 (Neo4j 엣지 동기화)
> - CS-6-3은 선행 아님 (summary_path 생성 로직은 별도 서비스 레이어, 본 작업에서 호출만)
> **산출물**:
> - `chainsight/serializers/path_watchlist.py`
> - `chainsight/views/watchlist_views.py` (WatchlistViewSet)
> - `chainsight/services/path_service.py` (snapshot/signature 생성 헬퍼)
> - `chainsight/urls.py` (라우팅)

---

## 배경

Phase 6의 핵심 엔드포인트. 프론트엔드 Watch 버튼(CS-7-1)이 POST를 호출하고, Watchlist 화면(CS-7-2)이 GET을 호출한다.

**v1.2 → v1.4 변경점**:
- POST 시 `edge_snapshot`, `path_signature` 자동 생성 로직 추가
- GET list 쿼리 파라미터를 MVP에서는 `status` + `-updated_at`만 유지 (intent, sector 필터는 v1.3 이후)

---

## API 엔드포인트 요약

```
POST   /api/chainsight/watchlist/              → Watch (경로 저장)
GET    /api/chainsight/watchlist/              → 목록
GET    /api/chainsight/watchlist/{id}/         → 상세
DELETE /api/chainsight/watchlist/{id}/         → 삭제

# 액션 API (CS-6-4, 6-5, 6-6, 6-7에서 각각 구현)
POST   /api/chainsight/watchlist/{id}/archive/
POST   /api/chainsight/watchlist/{id}/resolve/
POST   /api/chainsight/watchlist/{id}/recheck/
POST   /api/chainsight/watchlist/{id}/expand/
POST   /api/chainsight/watchlist/{id}/alternatives/
```

본 작업에서는 CRUD 4개와 **archive/resolve placeholder** (CS-6-4로 분리되지만 ViewSet 뼈대는 여기서 만들어 놓음)까지 다룬다.

---

## Serializer

### SavedPathListSerializer (목록용, 경량)

```python
# chainsight/serializers/path_watchlist.py

from rest_framework import serializers
from chainsight.models import SavedPath, PathAction


class SavedPathListSerializer(serializers.ModelSerializer):
    """목록 화면용. path 전체는 내려주지 않고 summary만."""

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
        """why_now_snapshot에서 headline만 추출."""
        if obj.why_now_snapshot and isinstance(obj.why_now_snapshot, dict):
            return obj.why_now_snapshot.get('headline', '')
        return ''

    def get_path_length(self, obj):
        """전체 경로 노드 수. 프론트엔드에서 summary_path와 비교해 '(+N)' 힌트 생성."""
        return len(obj.path_nodes) if obj.path_nodes else 0
```

### SavedPathDetailSerializer (상세용)

```python
class PathActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PathAction
        fields = ['id', 'action_type', 'metadata', 'created_at']


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
```

### SavedPathCreateSerializer (POST 입력용)

```python
class SavedPathCreateSerializer(serializers.ModelSerializer):
    """Watch 액션 입력. 사용자는 path_nodes + source만 제공.
    나머지는 서버가 자동 생성."""

    class Meta:
        model = SavedPath
        fields = [
            'path_nodes', 'source_center', 'source_slot',
        ]

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
        # 중복 체크
        if len(set(value)) != len(value):
            raise serializers.ValidationError('경로 내 중복 ticker 불가.')
        return [t.upper() for t in value]
```

---

## Service Layer (snapshot/signature 생성)

```python
# chainsight/services/path_service.py

from typing import List, Dict, Optional
from django.conf import settings
from chainsight.graph.repository import Neo4jGraphRepository


def build_edge_snapshot(path_nodes: List[str]) -> List[Dict]:
    """
    경로 내 인접 노드 쌍의 현재 관계 상태를 Neo4j에서 조회하여 스냅샷 생성.

    Args:
        path_nodes: ["NVDA", "TSM", "ASML", ...]

    Returns:
        [
            {"from": "NVDA", "to": "TSM", "type": "SUPPLIES_TO",
             "truth_score": 85, "status": "confirmed"},
            ...
        ]
    """
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
        # 양방향 엣지 중 가장 강한 관계 1개 선택
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
            # 관계 방향 정규화 (canonical direction from start_ticker)
            snapshot.append({
                'from': row['start_ticker'],
                'to': b if row['start_ticker'] == a else a,
                'type': row['rel_type'],
                'truth_score': row['truth_score'],
                'status': row['status'],
            })
        else:
            # 관계가 없어도 스냅샷에는 남김 (나중에 발견 가능)
            snapshot.append({
                'from': a,
                'to': b,
                'type': None,
                'truth_score': None,
                'status': 'hidden',
            })

    return snapshot


def build_path_signature(path_nodes: List[str], edge_snapshot: List[Dict]) -> str:
    """
    경로의 성격을 한 줄 태그로 압축.

    규칙:
    1. relation_type 빈도 집계 → 가장 많은 것이 "주된 관계 성격"
    2. 노드들의 sector 집계 → 가장 많은 것이 "대표 섹터"
    3. 조합: "{관계 라벨} · {섹터}"

    관계 라벨 매핑:
        SUPPLIES_TO → 공급망 중심
        COMPETES_WITH → 경쟁 관계
        PEER_OF → 동종업계
        HAS_THEME → 테마 연결
        CO_MENTIONED → 뉴스 연동
        PRICE_CORRELATED → 가격 동조
        (혼합) → 복합 체인
    """
    from collections import Counter
    from stocks.models import Stock

    RELATION_LABEL = {
        'SUPPLIES_TO': '공급망 중심',
        'COMPETES_WITH': '경쟁 관계',
        'PEER_OF': '동종업계',
        'HAS_THEME': '테마 연결',
        'CO_MENTIONED': '뉴스 연동',
        'PRICE_CORRELATED': '가격 동조',
    }

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
        # 1등이 전체의 60% 이상이면 그것으로, 아니면 "복합 체인"
        total = sum(rel_counts.values())
        if top_two[0][1] / total >= 0.6:
            rel_label = RELATION_LABEL.get(top_two[0][0], top_two[0][0])
        else:
            rel_label = '복합 체인'

    # 2) 섹터 빈도
    stocks = Stock.objects.filter(ticker__in=path_nodes).values_list('ticker', 'sector')
    sector_map = dict(stocks)
    sector_counts = Counter(sector_map.get(t) for t in path_nodes if sector_map.get(t))

    if not sector_counts:
        sector_label = ''
    else:
        dominant_sector = sector_counts.most_common(1)[0][0]
        sector_label = dominant_sector

    # 3) 조합
    if sector_label:
        return f'{rel_label} · {sector_label}'
    return rel_label


def build_initial_why_now(path_nodes: List[str], edge_snapshot: List[Dict]) -> Dict:
    """
    Watch 시점의 why_now_snapshot 초기값 생성.
    Recheck에서 갱신됨.
    """
    from django.utils import timezone

    # 강한 관계(confirmed/probable) 수
    strong_count = sum(
        1 for e in edge_snapshot
        if e.get('status') in ('confirmed', 'probable')
    )

    # 헤드라인 템플릿
    if strong_count == len(edge_snapshot) and strong_count > 0:
        headline = f'{len(path_nodes)}개 노드 전 구간 확인된 경로'
    elif strong_count >= len(edge_snapshot) * 0.6:
        headline = f'주요 구간 확인된 {len(path_nodes)}개 노드 경로'
    else:
        headline = f'{len(path_nodes)}개 노드 관찰 대상 경로'

    return {
        'headline': headline,
        'signals': [],  # Recheck에서 채워짐
        'generated_at': timezone.now().isoformat(),
        'strong_edges': strong_count,
        'total_edges': len(edge_snapshot),
    }
```

---

## ViewSet

```python
# chainsight/views/watchlist_views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

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

    GET /api/chainsight/watchlist/           → list
    POST /api/chainsight/watchlist/          → create (Watch)
    GET /api/chainsight/watchlist/{id}/      → retrieve
    DELETE /api/chainsight/watchlist/{id}/   → destroy

    Actions (CS-6-4 ~ CS-6-7):
        POST /{id}/archive/       → 본 작업 구현
        POST /{id}/resolve/       → 본 작업 구현
        POST /{id}/recheck/       → CS-6-5
        POST /{id}/expand/        → CS-6-6
        POST /{id}/alternatives/  → CS-6-7
    """

    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        qs = SavedPath.objects.all()

        # MVP: user 필터 (단일 사용자 가정 시 default user)
        user = self.request.user if self.request.user.is_authenticated else None
        if user:
            qs = qs.filter(user=user)
        else:
            qs = qs.filter(user__isnull=True)

        # status 필터 (쉼표 구분)
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
        """
        Watch 액션.

        입력: { "path_nodes": ["NVDA", "TSM"], "source_center": "NVDA",
                "source_slot": "exploration_trail" }
        출력: SavedPathDetailSerializer (edge_snapshot/path_signature 포함)

        처리:
        1. 입력 검증
        2. edge_snapshot 생성 (Neo4j 조회)
        3. path_signature 생성
        4. why_now_snapshot 초기값 생성
        5. summary_path 생성 (path_nodes가 4개 이하면 그대로,
           5개 이상이면 CS-6-3 로직 호출 — 본 작업에서는 일단 path_nodes 그대로 저장,
           CS-6-3에서 갱신)
        6. SavedPath 저장
        7. PathAction(WATCH) 기록
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        path_nodes = validated['path_nodes']

        # 자동 생성 필드
        edge_snapshot = build_edge_snapshot(path_nodes)
        path_signature = build_path_signature(path_nodes, edge_snapshot)
        why_now = build_initial_why_now(path_nodes, edge_snapshot)

        # summary_path: CS-6-3 미구현 시점에는 path_nodes 그대로
        # (4개 이하 경로는 어차피 그대로 표시 가능)
        summary_path = path_nodes if len(path_nodes) <= 4 else path_nodes
        # TODO: CS-6-3 완료 후 generate_summary_path(path_nodes, edge_snapshot) 호출

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

        # 액션 로그
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
        """Archive 액션. 단순 상태 변경."""
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
        """Resolve 액션. 전략 종료."""
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

    # recheck, expand, alternatives 는 CS-6-5/6/7에서 구현
```

---

## URL 라우팅

```python
# chainsight/urls.py

from rest_framework.routers import DefaultRouter
from chainsight.views.watchlist_views import WatchlistViewSet

router = DefaultRouter()
router.register(r'watchlist', WatchlistViewSet, basename='watchlist')

urlpatterns = [
    # ... 기존 URL들 (CS-4-1~3)
] + router.urls

# 루트 urls.py:
# path('api/chainsight/', include('chainsight.urls')),
```

결과 URL:
```
POST   /api/chainsight/watchlist/
GET    /api/chainsight/watchlist/
GET    /api/chainsight/watchlist/{id}/
DELETE /api/chainsight/watchlist/{id}/
POST   /api/chainsight/watchlist/{id}/archive/
POST   /api/chainsight/watchlist/{id}/resolve/
```

---

## 테스트

```python
# chainsight/tests/test_watchlist_api.py

import pytest
from rest_framework.test import APIClient
from chainsight.models import SavedPath, PathAction


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
def test_watch_success(client, mocker):
    """POST /watchlist/ 성공 케이스"""
    # Neo4j 호출 mock
    mocker.patch(
        'chainsight.services.path_service.build_edge_snapshot',
        return_value=[
            {'from': 'NVDA', 'to': 'TSM', 'type': 'SUPPLIES_TO',
             'truth_score': 85, 'status': 'confirmed'}
        ]
    )

    response = client.post('/api/chainsight/watchlist/', {
        'path_nodes': ['NVDA', 'TSM'],
        'source_center': 'NVDA',
        'source_slot': 'exploration_trail',
    }, format='json')

    assert response.status_code == 201
    assert response.data['path_nodes'] == ['NVDA', 'TSM']
    assert len(response.data['edge_snapshot']) == 1
    assert response.data['path_signature']  # 비어있지 않음
    assert response.data['status'] == 'watching'
    assert len(response.data['actions']) == 1
    assert response.data['actions'][0]['action_type'] == 'watch'


@pytest.mark.django_db
def test_watch_validation_errors(client):
    """잘못된 입력"""
    # path_nodes 1개
    r1 = client.post('/api/chainsight/watchlist/',
                     {'path_nodes': ['NVDA']}, format='json')
    assert r1.status_code == 400

    # 중복 ticker
    r2 = client.post('/api/chainsight/watchlist/',
                     {'path_nodes': ['NVDA', 'NVDA']}, format='json')
    assert r2.status_code == 400

    # 빈 요청
    r3 = client.post('/api/chainsight/watchlist/', {}, format='json')
    assert r3.status_code == 400


@pytest.mark.django_db
def test_list_filter_by_status(client):
    SavedPath.objects.create(path_nodes=['A', 'B'], status='watching')
    SavedPath.objects.create(path_nodes=['C', 'D'], status='archived')
    SavedPath.objects.create(path_nodes=['E', 'F'], status='resolved')

    r = client.get('/api/chainsight/watchlist/?status=watching,archived')
    assert r.status_code == 200
    assert len(r.data) == 2


@pytest.mark.django_db
def test_list_default_ordering(client):
    """-updated_at 순서"""
    p1 = SavedPath.objects.create(path_nodes=['A', 'B'])
    p2 = SavedPath.objects.create(path_nodes=['C', 'D'])
    # p2가 더 최근

    r = client.get('/api/chainsight/watchlist/')
    assert r.data[0]['id'] == p2.id
    assert r.data[1]['id'] == p1.id


@pytest.mark.django_db
def test_retrieve_with_actions(client):
    path = SavedPath.objects.create(path_nodes=['A', 'B'])
    PathAction.objects.create(saved_path=path, action_type='watch')
    PathAction.objects.create(saved_path=path, action_type='recheck')

    r = client.get(f'/api/chainsight/watchlist/{path.id}/')
    assert r.status_code == 200
    assert len(r.data['actions']) == 2


@pytest.mark.django_db
def test_archive_action(client):
    path = SavedPath.objects.create(path_nodes=['A', 'B'], status='watching')
    r = client.post(f'/api/chainsight/watchlist/{path.id}/archive/')
    assert r.status_code == 200
    assert r.data['status'] == 'archived'
    path.refresh_from_db()
    assert path.status == 'archived'


@pytest.mark.django_db
def test_archive_idempotent(client):
    path = SavedPath.objects.create(path_nodes=['A', 'B'], status='archived')
    r = client.post(f'/api/chainsight/watchlist/{path.id}/archive/')
    assert r.status_code == 400  # 이미 archived


@pytest.mark.django_db
def test_delete(client):
    path = SavedPath.objects.create(path_nodes=['A', 'B'])
    r = client.delete(f'/api/chainsight/watchlist/{path.id}/')
    assert r.status_code == 204
    assert not SavedPath.objects.filter(id=path.id).exists()
```

---

## 완료 기준

```
□ WatchlistViewSet 라우팅 정상 (DRF router에 등록)
□ POST /watchlist/ 성공 시 201 + edge_snapshot/path_signature 포함
□ POST validation 4개 (노드 수, 중복, ticker 형식, 빈 요청) 거부
□ GET /watchlist/ 기본 -updated_at 정렬
□ GET /watchlist/?status=watching 필터 동작
□ GET /watchlist/{id}/ 상세에 actions 리스트 포함
□ DELETE /watchlist/{id}/ 성공 시 204, PathAction도 cascade 삭제
□ POST /watchlist/{id}/archive/ 성공, PathAction 기록
□ POST /watchlist/{id}/resolve/ 성공, PathAction 기록
□ 중복 archive/resolve 요청은 400
□ Neo4j 관계 없는 경로도 edge_snapshot에 status='hidden'으로 저장
□ 8개 테스트 pass
```

---

## 주의사항

### Neo4j 호출 실패 시 처리

`build_edge_snapshot()`이 Neo4j 연결 실패로 raise하면 전체 Watch가 실패한다. MVP에서는 그대로 500 에러로 노출하되, 프로덕션에서는:
- Neo4j 연결 실패 시 edge_snapshot을 빈 리스트로 저장
- 백그라운드 Celery task로 나중에 snapshot 보강

본 작업에서는 **실패 시 그대로 500 에러** 전략. 로그만 남김. Neo4j는 같은 서버에 있으므로 실제 실패 빈도 낮음.

### summary_path 생성 위치

CS-6-3에서 `generate_summary_path()` 함수를 만들 예정. 본 작업에서는:
- path_nodes 4개 이하: summary_path = path_nodes 그대로
- path_nodes 5개 이상: 일단 path_nodes 그대로 저장. CS-6-3 완료 후 일괄 재생성 migration 또는 lazy하게 GET 시 재계산

### user FK 처리

`request.user.is_authenticated`가 False면 `user=None`으로 저장. MVP에서는 Django session middleware만 활성화되어 있고 auth 시스템이 없을 가능성 있음. 이 경우 모든 SavedPath가 `user__isnull=True`에 들어가 자동으로 한 그룹이 됨.

Django auth 도입 후에는 signal로 기존 null user 레코드를 default admin user에 할당하는 migration을 쓸 수 있음. 지금은 그 고민 안 함 (원칙 4).

### PATCH/PUT은 막음

`http_method_names = ['get', 'post', 'delete', 'head', 'options']`로 PATCH/PUT 차단. Path의 본체(path_nodes)는 불변. 상태 변경은 액션 엔드포인트(archive/resolve/recheck)로만 가능. 이렇게 해야 edge_snapshot/path_signature의 일관성이 깨지지 않음.

단, v1.3 이후 "경로에 메모 추가" 기능이 들어오면 PATCH를 허용해야 할 수 있음. 그때 별도 serializer로 memo 필드만 업데이트 가능하게 열어주면 됨.

### 대량 Watch 방지

MVP에서는 rate limit 없음. 단일 사용자라 남용 가능성 낮음. 멀티유저 전환 시 DRF throttling 추가.

### 401/403 vs 200 처리

인증 시스템 없는 MVP에서는 `IsAuthenticated` permission 걸지 않음. 모든 요청이 user=None 그룹에 들어감. 인증 도입 시 `permission_classes = [IsAuthenticated]` 추가 + 기존 데이터 마이그레이션.

---

→ **다음**: CS-6-3 (Summary path 생성) 또는 CS-6-5 (Recheck API)

**END OF DOCUMENT**
