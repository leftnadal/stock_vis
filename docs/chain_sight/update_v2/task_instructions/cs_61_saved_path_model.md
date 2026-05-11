# CS-6-1: SavedPath / PathAction 모델 migration 검증

> **작업 번호**: CS-6-1
> **목표**: Path Watchlist의 두 핵심 테이블(SavedPath, PathAction)이 v1.4 스키마대로 존재하고, 핵심 필드(edge_snapshot, path_signature, why_now_snapshot)가 동작함을 검증
> **예상 소요**: 0.5~1일
> **선행 조건**: CS-0-0 (스키마 마이그레이션 준비 단계에서 모델 생성 완료)
> **산출물**:
> - `chainsight/models/path_watchlist.py` (또는 기존 `chainsight/models.py` 내)
> - `chainsight/models/__init__.py` (SavedPath, PathAction export)
> - migration 파일
> - Django admin 등록 (선택)

---

## 배경

CS-0-0 Phase 0 착수 시점에 SavedPath/PathAction 모델을 만들어 showmigrations로 14개 테이블을 확인했다. 본 작업은 **Phase 6 진입 시점에 이 모델이 실제로 사용 가능한 상태인지 최종 검증**하는 작업이다.

CS-0-0에서 모델을 만들기만 했다면 필드 이름/타입 실수나 마이그레이션 누락이 있을 수 있다. Phase 6의 나머지 작업(CS-6-2 ~ CS-6-7)이 모두 이 모델에 의존하므로, 여기서 한 번 정리하고 넘어간다.

---

## SavedPath 모델 스키마

### 필드 정의

```python
# chainsight/models/path_watchlist.py

from django.db import models
from django.conf import settings


class SavedPath(models.Model):
    """
    사용자가 Chain Sight 탐색 중 저장한 경로.
    전략 단위로 모니터링/확장/비교의 대상이 된다.
    """

    class Status(models.TextChoices):
        WATCHING = 'watching', 'Watching'
        ACTIVE = 'active', 'Active'
        ARCHIVED = 'archived', 'Archived'
        RESOLVED = 'resolved', 'Resolved'
        # v1.3 이후 추가 예정: strengthening, weakening, broken

    # 소유자 (MVP 단일 사용자 가정, user FK nullable)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='saved_paths',
        help_text='MVP에서는 null 허용 (단일 사용자 가정). '
                  'Django auth 본격 도입 시 default user 마이그레이션 필요.'
    )

    # 경로 본체
    path_nodes = models.JSONField(
        help_text='ticker 배열. 예: ["NVDA", "TSM", "ASML", "AMAT"]. '
                  '최소 2개, 최대 10개 권장.'
    )
    summary_path = models.JSONField(
        blank=True, null=True,
        help_text='카드 요약용 landmark ticker 배열. '
                  '5+ 노드 경로를 3~4개로 압축. '
                  'CS-6-3 Summary path 생성 로직에서 채움. '
                  '예: ["NVDA", "TSM", "ASML"] (원래 7개 노드를 3개로 축약)'
    )

    # 경로 성격 태그
    path_signature = models.CharField(
        max_length=80, blank=True, null=True,
        help_text='경로의 관계 성격 태그. '
                  'edge_snapshot에서 relation_type 빈도 분석 → 주된 성격 추출. '
                  '예: "공급망 중심 · Technology" / "동종업계 경쟁 · Healthcare"'
    )

    # 엣지 상태 스냅샷 (Recheck 시 비교 기준)
    edge_snapshot = models.JSONField(
        blank=True, null=True,
        help_text='저장 시점 각 인접 노드 쌍의 관계 스냅샷. '
                  'Recheck API에서 현재 상태와 diff 비교에 사용. '
                  '예: [{"from": "NVDA", "to": "TSM", "type": "SUPPLIES_TO", '
                  '"truth_score": 85, "status": "confirmed"}, ...]'
    )

    # Why Now 스냅샷 (저장 이유, 카드에 노출)
    why_now_snapshot = models.JSONField(
        blank=True, null=True,
        help_text='저장 시점의 why now 요약 (headline + signals). '
                  'Recheck 시 갱신 가능. '
                  '예: {"headline": "장비 체인 relevance 상승", '
                  '"signals": [...], "generated_at": "2026-04-16T07:30:00Z"}'
    )

    # 출처 추적 (개인화 분석용, MVP 수집만)
    source_center = models.CharField(
        max_length=10, blank=True, null=True,
        help_text='Watch가 발생한 시점의 그래프 중심 노드 ticker. 예: "NVDA"'
    )
    source_slot = models.CharField(
        max_length=40, blank=True, null=True,
        help_text='Watch가 발생한 UI 위치. '
                  '값: "exploration_trail" / "next_best_chain" / '
                  '"chain_story_feed" / "hidden_hub" 등'
    )

    # 상태
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.WATCHING,
        db_index=True,
    )

    # Recheck 카운트 (watching→active 전이 조건)
    recheck_count = models.PositiveIntegerField(
        default=0,
        help_text='Recheck 액션이 실행된 누적 횟수. '
                  '2회 이상 + created_at으로부터 24시간 경과 시 watching→active.'
    )

    # 시각
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        db_table = 'chainsight_saved_path'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', '-updated_at']),
            models.Index(fields=['status', '-updated_at']),
        ]

    def __str__(self):
        path_display = ' → '.join(self.path_nodes[:3])
        if len(self.path_nodes) > 3:
            path_display += f' (+{len(self.path_nodes) - 3})'
        return f'[{self.status}] {path_display}'
```

### ⚠️ path_nodes 크기 제한

명시적 DB 제약은 걸지 않되 (JSONField에 제약 불가), serializer 레벨에서 검증:
- 최소 2개 (경로의 정의상)
- 최대 10개 (너무 긴 경로는 의미 없음, UI 부담 증가)

CS-6-2 Watchlist CRUD API의 POST validator에서 enforce.

---

## PathAction 모델 스키마

```python
# chainsight/models/path_watchlist.py (같은 파일)

class PathAction(models.Model):
    """
    SavedPath에 가해진 액션 이력.
    이벤트 로깅 + watching→active 전이 판정 + 개인화 분석용.
    """

    class ActionType(models.TextChoices):
        WATCH = 'watch', 'Watch (저장)'
        RECHECK = 'recheck', 'Recheck (상태 재확인)'
        EXPAND = 'expand', 'Expand (경로 확장)'
        ALTERNATIVES = 'alternatives', 'Alternatives (노드 대안 탐색)'
        ARCHIVE = 'archive', 'Archive (보관)'
        RESOLVE = 'resolve', 'Resolve (전략 종료)'

    saved_path = models.ForeignKey(
        SavedPath,
        on_delete=models.CASCADE,
        related_name='actions',
    )

    action_type = models.CharField(
        max_length=20,
        choices=ActionType.choices,
        db_index=True,
    )

    metadata = models.JSONField(
        blank=True, null=True,
        help_text='액션별 부가 데이터. 예시: '
                  'expand: {"added_nodes": ["MU", "NXPI"]}, '
                  'alternatives: {"target": "AMAT", "selected": "LRCX"}, '
                  'recheck: {"strengthened": 2, "weakened": 1, "broken": 0}'
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'chainsight_path_action'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['saved_path', '-created_at']),
            models.Index(fields=['action_type', '-created_at']),
        ]

    def __str__(self):
        return f'{self.action_type} on path#{self.saved_path_id}'
```

---

## __init__.py 업데이트

```python
# chainsight/models/__init__.py

from .path_watchlist import SavedPath, PathAction
# ... (기존 imports: CompanyChainProfile, RelationConfidence 등)

__all__ = [
    # ... 기존 모델들
    'SavedPath',
    'PathAction',
]
```

기존 `chainsight/models.py` 단일 파일 구조라면, 하위 디렉토리로 분리하지 말고 `models.py` 하단에 추가해도 무방. 원칙 4(단순 구조) 부합.

---

## Migration 검증 절차

### 1. CS-0-0 완료 확인

```bash
python manage.py showmigrations chainsight
```

14개 migration이 모두 [X]인지 확인. SavedPath, PathAction 관련 migration이 포함되어 있어야 함.

### 2. 없으면 생성

```bash
python manage.py makemigrations chainsight
# → 0015_add_saved_path_and_path_action.py 같은 파일 생성 확인

python manage.py migrate
```

### 3. 테이블 존재 확인

```bash
python manage.py dbshell
```

```sql
\dt chainsight_saved_path;
\dt chainsight_path_action;

\d chainsight_saved_path;
-- 모든 필드 존재 + 타입 확인

\di chainsight_saved_path;
-- user_id+updated_at, status+updated_at 인덱스 확인
```

### 4. 모델 단위 테스트

```python
# chainsight/tests/test_path_watchlist_models.py

import pytest
from django.contrib.auth import get_user_model
from chainsight.models import SavedPath, PathAction

User = get_user_model()


@pytest.mark.django_db
def test_saved_path_create_minimal():
    """최소 필드로 생성 가능"""
    path = SavedPath.objects.create(
        path_nodes=['NVDA', 'TSM'],
    )
    assert path.status == SavedPath.Status.WATCHING
    assert path.recheck_count == 0
    assert path.user is None  # MVP 단일 사용자


@pytest.mark.django_db
def test_saved_path_with_full_data():
    """edge_snapshot, why_now_snapshot 저장/조회"""
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


@pytest.mark.django_db
def test_path_action_create():
    """PathAction 생성 + 관계"""
    path = SavedPath.objects.create(path_nodes=['NVDA', 'TSM'])
    action = PathAction.objects.create(
        saved_path=path,
        action_type=PathAction.ActionType.WATCH,
        metadata={'source_slot': 'exploration_trail'},
    )
    assert path.actions.count() == 1
    assert path.actions.first().action_type == 'watch'


@pytest.mark.django_db
def test_saved_path_cascade_delete():
    """SavedPath 삭제 시 PathAction도 삭제"""
    path = SavedPath.objects.create(path_nodes=['NVDA', 'TSM'])
    PathAction.objects.create(saved_path=path, action_type='watch')
    path_id = path.pk
    path.delete()
    assert PathAction.objects.filter(saved_path_id=path_id).count() == 0


@pytest.mark.django_db
def test_saved_path_ordering():
    """기본 정렬: -updated_at"""
    p1 = SavedPath.objects.create(path_nodes=['A', 'B'])
    p2 = SavedPath.objects.create(path_nodes=['C', 'D'])
    # p2가 더 최근에 생성됨
    ordered = list(SavedPath.objects.all()[:2])
    assert ordered[0].pk == p2.pk
    assert ordered[1].pk == p1.pk


@pytest.mark.django_db
def test_status_choices():
    """유효하지 않은 status는 full_clean에서 거부"""
    from django.core.exceptions import ValidationError
    path = SavedPath(path_nodes=['A', 'B'], status='invalid_status')
    with pytest.raises(ValidationError):
        path.full_clean()
```

---

## Django Admin 등록 (선택)

1인 개발 MVP 단계에서 데이터 확인에 유용. 본격 사용자용 아니므로 간단히.

```python
# chainsight/admin.py

from django.contrib import admin
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

---

## 완료 기준

```
□ chainsight_saved_path 테이블 존재, 12개 필드 확인 (user, path_nodes, summary_path,
   path_signature, edge_snapshot, why_now_snapshot, source_center, source_slot,
   status, recheck_count, created_at, updated_at)
□ chainsight_path_action 테이블 존재, 5개 필드 확인 (saved_path, action_type,
   metadata, created_at, + id)
□ 인덱스 4개 확인 (saved_path의 user+updated, status+updated / path_action의
   saved_path+created, action_type+created)
□ FK cascade 동작 확인 (SavedPath 삭제 → PathAction 삭제)
□ JSONField 저장/조회 round-trip 테스트 통과 (edge_snapshot, why_now_snapshot)
□ 기본 ordering=-updated_at 동작 확인
□ 6개 단위 테스트 pass
□ Django admin 접속 가능 (선택)
```

---

## 주의사항

### user FK Nullable 유지 이유

MVP는 단일 사용자(병진님 본인) 가정. Django auth가 이미 구현되어 있다면 default user를 자동 할당하는 signal이나 save() override를 추가할 수 있으나, 본 작업에서는 구현하지 않음. CS-6-2 CRUD에서 request.user가 없는 경우 default user를 쓰도록 처리.

### path_nodes를 별도 테이블로 분리하지 않는 이유

관계형 DB 정석으로는 `path_node` 테이블(saved_path FK + ticker + order)로 분리해야 한다. 하지만:
- 경로는 항상 전체를 함께 조회/수정 (부분 업데이트 없음)
- path_nodes JSONField로 저장해도 조회 성능 차이 미미 (N+1 문제 없음)
- 테이블 하나 더 관리하는 오버헤드 > 얻는 이득
- 원칙 4 (단순 구조) 부합

단, path_nodes에 기반한 SQL 쿼리(예: "AAPL이 포함된 모든 경로")가 필요해지면 별도 테이블 필요. MVP에서는 프론트엔드에서 Python 필터링으로 충분.

### v1.3 이후 추가 예정 필드

현재 스키마에서 의도적으로 생략한 것들:
- `strengthening_score`, `weakening_score` (자동 상태 전환용, v1.3)
- `folder` FK (커스텀 폴더 구조, v2.0 — MVP에서 불필요)
- `memo` TextField (자유 메모, v2.0 — 긴 메모 중심 설계는 원칙 6 부합 안 함)
- `shared_with` M2M (공유 기능, 단일 사용자 MVP에서 불필요)

필요 시 향후 migration으로 추가. 지금 넣지 않는 게 원칙 4.

### edge_snapshot 스키마 변경 시 version 필드?

스키마가 JSONField라 버전 관리가 애매하다. 예를 들어 Recheck 로직이 개선되면서 edge_snapshot 스키마가 변경될 수 있음. 하지만 MVP에서 이 문제를 미리 해결하려 하면 복잡도 폭증. **v1.4에서는 스키마 고정, 변경 시 migration이나 일괄 재계산 script로 처리.**

---

→ **다음**: CS-6-2 (Watchlist CRUD API)

**END OF DOCUMENT**
