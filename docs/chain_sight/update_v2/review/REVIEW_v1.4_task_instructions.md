# Chain Sight v1.4 작업 지시서 12개 전수 점검 리포트

> **작성일**: 2026-04-16
> **점검 대상**: ROADMAP v1.4 + 12개 작업 지시서 (cs_44, cs_55, cs_61, cs_62, cs_63, cs_65, cs_66, cs_67, cs_71, cs_72, cs_73)
> **점검 기준**: v1.2 초안 22개 점검과 동일 (High / Medium / Low / Consistency)
> **총 검토 페이지**: 약 8,000줄

---

## 요약

| 심각도 | 건수 | 조치 필요 시점 |
|---|---|---|
| **High** (치명) | 2건 | CS-0-0 착수 전 또는 해당 작업 착수 시 |
| **Medium** (보완) | 4건 | 해당 작업 완료 전 반영 |
| **Low** (개선) | 2건 | 여유 있을 때 |
| **Consistency** (일관성) | 2건 | 통합 검토 |

이번 검토에서 확인된 **치명 결함 없음**. 실제 코드를 그대로 돌리면 깨지는 것은 H1 1건(테스트 코드 오타). H2는 작업 순서 상 혼란 유발 가능성이지만 로직 자체는 올바름.

---

## [High] 치명 결함

### H1 — CS-6-1 `test_saved_path_cascade_delete` 테스트에 FK 필드명 오타

**위치**: cs_61_saved_path_model.md : 328 lines

```python
@pytest.mark.django_db
def test_saved_path_cascade_delete():
    """SavedPath 삭제 시 PathAction도 삭제"""
    path = SavedPath.objects.create(path_nodes=['NVDA', 'TSM'])
    PathAction.objects.create(path=path, action_type='watch')  # ❌ path=path
    path_id = path.pk
    path.delete()
    assert PathAction.objects.filter(saved_path_id=path_id).count() == 0
```

**문제**: `PathAction` 모델의 FK 이름은 `saved_path`(CS-6-1 모델 정의 기준)인데 테스트 코드에서 `path=path`로 호출. 실제 실행 시 `TypeError: PathAction() got unexpected keyword arguments: 'path'` 발생.

**다른 테스트는 정상**: `test_path_action_create` 함수는 `saved_path=path`로 올바르게 작성됨. 한 곳만 오타.

**수정**:
```python
PathAction.objects.create(saved_path=path, action_type='watch')
```

**영향**: CS-6-1 완료 기준 중 "FK cascade 동작 확인" 테스트가 실패 → 수정 없이는 CS-6-1 완료 불가.

---

### H2 — CS-5-5와 CS-7-1 사이 ExplorationTrail Props 스키마 변경 누락

**위치**: cs_55_market_view.md(ExplorationTrail 정의) vs cs_71_watch_button.md(ExplorationTrail 수정 지시)

**문제**:
- CS-5-5 구현: `ExplorationTrail`은 `{ trail, onUndo, onWatch: () => void }` props를 받고, 부모(MarketView)가 `handleWatch()`를 구현
- CS-7-1에서 ExplorationTrail을 수정: `onWatch` prop 제거하고 WatchButton을 컴포넌트 내부에 embed
- CS-7-1 본문 "6. ExplorationTrail 수정" 섹션에서 이 변경을 명시했지만, **CS-5-5 완료 기준 체크박스에는 '이 컴포넌트의 onWatch는 placeholder이고 CS-7-1에서 제거됨'이라는 명시가 없음**

**시나리오**:
1. CS-5-5 완료 후 MarketView 화면 동작 OK (onWatch=alert() placeholder)
2. CS-7-1 착수 시 개발자가 ExplorationTrail 수정을 잊고 WatchButton만 새로 만듦
3. MarketView의 `onWatch` prop은 여전히 부모에서 `handleWatch()` 호출 → 두 경로로 Watch 트리거 가능 또는 아무 경로로도 작동 안 함 (오타/실수에 따라)

**수정 방향 (둘 중 택1)**:

**옵션 A**: CS-5-5 완료 기준에 주의 문구 추가
```
□ ExplorationTrail의 onWatch는 placeholder이며 CS-7-1에서 제거 예정
```

**옵션 B** (권장): CS-7-1의 완료 기준에 명시적 체크박스 추가
```
□ CS-5-5의 ExplorationTrail Props에서 onWatch 제거
□ MarketView에서 handleWatch prop 전달 제거
□ WatchButton을 ExplorationTrail 내부에 embed 완료
```

**추가 수정**: CS-7-1 "5. MarketView 통합" 섹션의 수정 예시를 더 명시적으로. 현재는 `// onWatch prop 제거, 대신 WatchButton을 직접 embed`라는 주석 한 줄만 있어 혼동 가능.

---

## [Medium] 보완 필요

### M1 — CS-7-3 Candidate 타입이 백엔드 응답보다 축소됨

**위치**: cs_73_path_detail_view.md의 `interface Candidate`

**백엔드 Expand 응답 (CS-6-6)** 9개 필드:
```
ticker, name, sector, relation_type, truth_score, relation_status,
heat_score, basis_summary, why_summary
```

**프론트 Candidate 타입** 7개 필드:
```typescript
interface Candidate {
  ticker: string;
  name: string;
  sector: string;
  relation_type: string;
  truth_score: number;
  why_summary: string;
  heat_score: number | null;
  // relation_status, basis_summary 누락
}
```

**영향**: `basis_summary`는 "왜 이 노드와 연결됐는지"의 핵심 정보(예: "반도체 장비 공급 공시 확인"). 이 정보가 UI에 노출되지 않으면 ExpandDialog의 가치가 크게 떨어짐. PM_DESIGN 섹션 12-2의 "탐색 가치 설명" 원칙 훼손.

**수정**:
```typescript
interface Candidate {
  ticker: string;
  name: string;
  sector: string;
  relation_type: string;
  truth_score: number;
  relation_status: string;   // 추가
  heat_score: number | null;
  basis_summary: string;     // 추가
  why_summary: string;
}
```

ExpandDialog 카드 UI에서 `basis_summary`를 `why_summary` 위 또는 아래에 표시 (인용부호로 구분).

---

### M2 — CS-7-3 RecheckResult 타입에 updated_why_now 누락

**위치**: cs_73_path_detail_view.md의 `export interface RecheckResult`

**백엔드 응답 (CS-6-5 recheck action)**:
```python
return Response({
    'headline': ..., 'strengthened': ..., 'weakened': ..., 'unchanged': ...,
    'broken_edges': ..., 'path_intact': ..., 'suggested_action': ...,
    'suggested_reason': ..., 'updated_why_now': result.updated_why_now,  # ← 이 필드
    'status': ..., 'recheck_count': ...,
})
```

**프론트 타입**: `updated_why_now` 필드 없음.

**현재 영향**: `usePathDetail` 훅에서 Recheck 후 `fetchPath()`로 서버에서 갱신된 `why_now_snapshot` 다시 가져오기 때문에 로직은 작동. 그러나:
1. 타입 안전성 위반 — 실제 응답과 타입이 다름
2. 불필요한 추가 API 호출 (`fetchPath()`) — 응답에 이미 데이터 있음에도 다시 조회

**수정**: 타입에 필드 추가 + `recheck()` 훅이 응답의 `updated_why_now`로 path state 직접 업데이트 (fetchPath 호출 제거).

```typescript
export interface RecheckResult {
  // ... 기존 필드
  updated_why_now: {
    headline: string;
    signals: any[];
    generated_at: string;
    strong_edges?: number;
    total_edges?: number;
    suggested_action?: string;
  };
  status: string;
  recheck_count: number;
}

// usePathDetail.ts 수정
const recheck = useCallback(async () => {
  setActionInProgress('recheck');
  try {
    const result = await recheckPath(id);
    setRecheckResult(result);
    // fetchPath() 호출 대신 로컬 state 업데이트
    setPath(prev => prev ? {
      ...prev,
      status: result.status as PathStatus,
      recheck_count: result.recheck_count,
      why_now_snapshot: result.updated_why_now,
    } : prev);
    return result;
  } finally {
    setActionInProgress(null);
  }
}, [id]);
```

---

### M3 — SavedPathListSerializer에 path_length 누락 → CS-7-2 `(+N)` 힌트 불가능

**위치**: cs_62_watchlist_crud_api.md(SavedPathListSerializer) vs cs_72_watchlist_view.md(PathCard `pathLengthHint`)

**문제 연쇄**:
1. CS-6-2 SavedPathListSerializer는 경량이라 `path_nodes` 제외. 필드는 `id, summary_path, path_signature, status, latest_headline, recheck_count, created_at, updated_at` 8개
2. CS-7-2 PathCard는 `path.path_nodes && path.summary_path && path.path_nodes.length > ...`로 `(+N)` 힌트 계산
3. 결과: list 응답에 `path_nodes`가 없어 조건문이 항상 false → 힌트 표시 안 됨
4. CS-7-2 주의사항에서 이를 언급했지만 **양쪽 모두 수정되지 않음**

**수정 (선택지)**:

**옵션 A**: CS-6-2의 SavedPathListSerializer에 `path_length` SerializerMethodField 추가
```python
class SavedPathListSerializer(serializers.ModelSerializer):
    latest_headline = serializers.SerializerMethodField()
    path_length = serializers.SerializerMethodField()

    class Meta:
        model = SavedPath
        fields = [
            'id', 'summary_path', 'path_signature', 'status',
            'latest_headline', 'recheck_count',
            'path_length',  # 추가
            'created_at', 'updated_at',
        ]

    def get_path_length(self, obj):
        return len(obj.path_nodes) if obj.path_nodes else 0
```

CS-7-2 PathCard도 `path_length` 기반으로 수정:
```typescript
const pathLengthHint =
  path.path_length && path.summary_path &&
  path.path_length > path.summary_path.length
    ? ` (+${path.path_length - path.summary_path.length})`
    : '';
```

**옵션 B**: `(+N)` 힌트 제거. 목록 카드는 summary_path만 표시 (항상 3~4개). 상세 진입 시 전체 경로 노출.

**권장**: **옵션 A**. 이유:
- 사용자가 "이 경로가 몇 단계인지"를 카드에서 바로 인지하는 건 UX에 중요
- path_length는 1바이트 정수로 응답 크기 무시 가능
- 프론트 로직 단순 유지

---

### M4 — CS-6-3 _fetch_centrality 호출 인자 불필요

**위치**: cs_63_summary_path.md의 `compute_landmark_scores()`

```python
centrality = _fetch_centrality(middle_nodes + [full_path[0], full_path[-1]])
```

**문제**: 시작/끝 노드는 항상 summary_path에 포함되므로 landmark 선정 대상이 아님. 이들의 pagerank/betweenness/degree는 계산에 쓰이지 않는다 (`bridge_scores`, `sector_scores`, `ranks` 모두 middle_nodes에만 적용).

**영향**: 불필요한 데이터 조회(3~5개 노드 추가). Neo4j 쿼리 자체는 단일 UNWIND라 네트워크 왕복은 1회로 동일. 성능 영향 미미지만 **코드 의도 불분명**.

**수정**:
```python
centrality = _fetch_centrality(middle_nodes)
```

또는 의도가 "경로 전체의 상대적 랭크 비교"라면 주석 추가:
```python
# 경로 전체를 기준으로 중심성 normalize하기 위해 시작/끝 노드도 조회
centrality = _fetch_centrality(full_path)
```

정답은 "middle_nodes만 조회"가 맞음(`_normalize_rank`에서 `middle_nodes`만 입력으로 받기 때문). 현재 구현이 그 의미였다면 정리 필요.

---

## [Low] 개선 사항

### L1 — CS-6-5 `_maybe_transition_to_active` 주석 혼동

**위치**: cs_65_recheck_api.md

```python
def _maybe_transition_to_active(saved_path: SavedPath) -> None:
    """
    watching → active 전이 조건:
    - recheck_count >= 2 (이 호출에서 +1 되기 전 기준 이미 1 이상이어야 함,
      즉 이 Recheck가 2회째)
    - created_at으로부터 24시간 경과
    """
    # ...
    # recheck_count는 아직 증가 전 (run_recheck에서 이미 +1 했는지 확인 필요)
    # 이 함수는 run_recheck 내에서 recheck_count += 1 이후에 호출됨
```

**문제**: docstring 상단 "+1 되기 전 기준" vs 하단 주석 "이미 +1 이후에 호출됨" 상충. 실제 코드는 후자가 맞음 (`run_recheck`에서 `+= 1` 후 호출).

**수정**: docstring 정리
```python
"""
watching → active 전이 조건:
- recheck_count >= 2 (이 함수 호출 시점에 이미 증가된 값 기준)
- created_at으로부터 24시간 경과
"""
```

하단 주석도 제거 또는 단일화.

---

### L2 — CS-7-3의 source_slot 값이 상수로 관리되지 않음

**위치**: cs_71_watch_button.md(SOURCE_SLOTS 상수) vs cs_73_path_detail_view.md(하드코딩)

**CS-7-1에서 정의한 상수**:
```typescript
export const SOURCE_SLOTS = {
  EXPLORATION_TRAIL: 'exploration_trail',
  NEXT_BEST_CHAIN: 'next_best_chain',
  CHAIN_STORY_FEED: 'chain_story_feed',
  HIDDEN_HUB: 'hidden_hub',
};
```

**CS-7-3에서 실사용**:
```typescript
source_slot: 'expand_from_watchlist',       // 하드코딩
source_slot: 'alternatives_from_watchlist', // 하드코딩
```

**수정**: CS-7-1의 SOURCE_SLOTS 상수에 누락된 값 추가
```typescript
export const SOURCE_SLOTS = {
  EXPLORATION_TRAIL: 'exploration_trail',
  NEXT_BEST_CHAIN: 'next_best_chain',
  CHAIN_STORY_FEED: 'chain_story_feed',
  HIDDEN_HUB: 'hidden_hub',
  EXPAND_FROM_WATCHLIST: 'expand_from_watchlist',
  ALTERNATIVES_FROM_WATCHLIST: 'alternatives_from_watchlist',
} as const;
```

CS-7-3도 상수 참조로 변경:
```typescript
source_slot: SOURCE_SLOTS.EXPAND_FROM_WATCHLIST,
```

---

## [Consistency] 일관성

### C1 — SavedPath `status` 한글 라벨 매핑 위치 분산

여러 컴포넌트에서 독자적으로 매핑 정의:
- CS-7-2 PathCard: `STATUS_BADGE = { watching: {label: '관찰 중', ...}, ... }`
- CS-7-3 PathDetailView: `STATUS_BADGE = { watching: {label: '관찰 중', ...}, ... }` (동일 내용 복제)

**문제**: 두 곳에서 라벨이 다르게 수정될 위험. 원칙 4 단순 구조 측면에서 일원화 권장.

**수정**: 공통 유틸로 추출
```typescript
// frontend/utils/pathStatus.ts
export const PATH_STATUS_BADGE = {
  watching: { label: '관찰 중', color: 'bg-blue-100 text-blue-800', icon: '●' },
  active: { label: '활성', color: 'bg-green-100 text-green-800', icon: '●' },
  archived: { label: '보관됨', color: 'bg-gray-100 text-gray-700', icon: '○' },
  resolved: { label: '종료됨', color: 'bg-purple-100 text-purple-800', icon: '◉' },
} as const;
```

양쪽 컴포넌트에서 import.

---

### C2 — 에러 응답 메시지 포맷

백엔드 에러 응답은 DRF 기본 형식: `{'detail': '...'}`

프론트 처리:
- CS-7-1 watchlistService: `error.detail || ... (${response.status})` ✅
- CS-7-2 useWatchlist: `(e as Error).message` — Error 객체로 변환된 후 사용
- CS-7-3 usePathDetail: `(e as Error).message`

**판단**: 일관 OK. `(e as Error).message`는 watchlistService에서 `throw new Error(error.detail || ...)`로 감싸기 때문에 결과적으로 `error.detail`이 전달됨. 현재 구조 유지.

---

## 우선순위별 조치 계획

### 착수 전 필수 수정 (2건)

```
□ H1: cs_61_saved_path_model.md 328줄 `path=path` → `saved_path=path`
□ H2: cs_71_watch_button.md 완료 기준에 ExplorationTrail 수정 체크박스 3개 추가
```

### 작업 진행 중 수정 (4건)

```
□ M1: cs_73_path_detail_view.md Candidate 타입에 relation_status, basis_summary 추가
□ M2: cs_73_path_detail_view.md RecheckResult 타입에 updated_why_now 추가 + useCallback에서 fetchPath 제거
□ M3: cs_62_watchlist_crud_api.md SavedPathListSerializer에 path_length SerializerMethodField 추가 + cs_72 PathCard 로직 수정
□ M4: cs_63_summary_path.md _fetch_centrality 호출을 middle_nodes로 축소 또는 주석으로 의도 명시
```

### 여유 있을 때 (4건)

```
□ L1: cs_65_recheck_api.md _maybe_transition_to_active docstring + 주석 정리
□ L2: cs_71_watch_button.md SOURCE_SLOTS에 EXPAND_FROM_WATCHLIST, ALTERNATIVES_FROM_WATCHLIST 추가
□ C1: frontend/utils/pathStatus.ts 공통 유틸 추출
□ C2: 현 구조 유지 (판단 결과 OK)
```

---

## 검증된 것 (일관성 OK)

이번 검토에서 다음 항목들은 **모두 일관성 확인 완료**:

```
✓ SavedPath 12개 필드 정의와 각 작업의 사용 일치
✓ PathAction.ActionType 6개 enum 값 (watch/recheck/expand/alternatives/archive/resolve) 모두 사용됨
✓ status 4개 값 (watching/active/archived/resolved) 백엔드/프론트 일치
✓ API URL 구조 /api/chainsight/watchlist/{id}/action/ 백엔드 라우팅과 프론트 호출 일치
✓ edge_snapshot 스키마 (from/to/type/truth_score/status) 생성·비교·프론트 표시 일치
✓ why_now_snapshot 스키마 (headline/signals/generated_at/strong_edges/total_edges) 일관
✓ path_nodes 길이 제약 (min 2, max 10) 백엔드 validator와 모델 help_text 일치
✓ http_method_names DELETE 허용 + 프론트 deleteSavedPath 일치
✓ heat_score 저장 위치 (Neo4j :Stock 속성) 생성·읽기 일치
✓ Celery Beat chainsight-heat-score-daily 등록 ROADMAP v1.4와 CS-4-4 일치
✓ 관계 타입 enum (SUPPLIES_TO/COMPETES_WITH/PEER_OF/HAS_THEME/CO_MENTIONED/PRICE_CORRELATED) 모든 작업 통일
✓ RELATION_PRIORITY 매핑이 CS-6-6 Expand에만 존재, 다른 작업에서 참조 없음 (Alternatives는 다른 로직)
```

---

## 총평

v1.2 초안 22개 지시서 점검에서 9개 불일치를 식별했던 것에 비해, 이번 v1.4 12개 지시서에서는 **심각한 결함이 크게 줄었다**. 주된 이유:

1. **명시적 인용**: CS-6-2가 CS-6-1의 모델을 "12개 필드"로 명시하고 생성 시 사용하는 필드를 순서대로 나열
2. **TODO 주석 일관 처리**: CS-6-2에서 "CS-6-3 완료 후 generate_summary_path 호출"이라는 TODO가 있고, CS-6-3에서 이 TODO를 해결하는 수정 예시를 제공
3. **PM_DESIGN.md 기반 설계**: 섹션 번호 인용으로 PM 결정과 일치 확인

남은 문제 대부분은 **프론트 타입 정의의 누락**(M1, M2)과 **경량 serializer 때문에 UI가 원하는 정보를 못 받는 문제**(M3). 이들은 CS-7-2/CS-7-3 구현 단계에서 바로 감지될 것이므로 치명적이지 않음.

H1(테스트 오타)만 CS-0-0 착수 전에 수정하고, H2(ExplorationTrail 수정 누락)만 CS-7-1 착수 시 체크리스트 강화하면, 나머지는 각 작업 자연스러운 흐름에서 발견·수정 가능.

**END OF REPORT**
