# Chain Sight 작업 지시서 v1.4 — 변경 내역

> **작성일**: 2026-04-16
> **버전**: v1.4 (리뷰 반영)
> **적용 대상**: cs_61, cs_62, cs_63, cs_65, cs_71, cs_72, cs_73 (총 7개 파일)
> **선행 문서**: ROADMAP v1.4, CHAIN_SIGHT_PM_v1.2, 작업 지시서 v1.3

---

## 반영 요약

교차검증 리뷰에서 도출된 10개 항목 전수 반영 완료.

| # | 심각도 | 항목 | 파일 | 유형 |
|---|-------|------|------|------|
| H1 | High | PathAction FK typo | cs_61 | 오타 수정 |
| H2 | High | ExplorationTrail 스키마 변경 완료 기준 | cs_71 | 의존성 명시 |
| M1 | Medium | Expand 후보에 relation_status + basis_summary | cs_73 | 타입 확장 |
| M2 | Medium | Recheck 로컬 상태 갱신 | cs_73 | UX 개선 |
| M3-a | Medium | path_length SerializerMethodField | cs_62 | 직렬화 보강 |
| M3-b | Medium | PathCard에서 path_length 사용 | cs_72 | 프론트 동기화 |
| M4 | Medium | centrality 조회 범위 축소 | cs_63 | 성능 최적화 |
| L1 | Low | _maybe_transition_to_active docstring | cs_65 | 문서화 |
| L2 | Low | SOURCE_SLOTS 상수화 (2개 신규) | cs_71, cs_73 | 매직 스트링 제거 |
| C1 | Consistency | STATUS_BADGE 공통 유틸 추출 | cs_72, cs_73 | 중복 제거 |

---

## H1 — cs_61 PathAction FK 오타

**문제**: SavedPath와 PathAction 간 related_name이 문서와 코드 간 불일치.

**Before**
```python
class PathAction(models.Model):
    saved_path = models.ForeignKey(
        SavedPath,
        on_delete=models.CASCADE,
        related_name='action'  # ← 단수형
    )
```

**After**
```python
class PathAction(models.Model):
    saved_path = models.ForeignKey(
        SavedPath,
        on_delete=models.CASCADE,
        related_name='actions'  # 복수형으로 통일. saved_path.actions.all() 로 조회
    )
```

**영향**: `saved_path.actions.filter(action=ActionType.RECHECK)` 형태의 역참조가 문서 전반에서 사용되므로 반드시 복수형 유지.

---

## H2 — cs_71 ExplorationTrail 스키마 변경 완료 기준

**문제**: Watch 버튼 구현(cs_71)은 ExplorationTrail에 `path[]` + `edge_metadata[]` 필드가 있다고 가정하는데, 현재 CS-5-5(마켓뷰) 작업 지시서에는 이 스키마 변경이 선행 작업으로 명시되지 않음.

**Before** (완료 기준 누락)
```markdown
## 완료 기준
- [ ] Watch 버튼 클릭 시 POST /watchlist/ 호출
- [ ] 토스트 메시지 표시
- [ ] Watchlist 열기 secondary action 동작
```

**After**
```markdown
## 완료 기준

### CS-5-5 ExplorationTrail 스키마 선행 변경

Watch 버튼은 현재 탐색 경로에서 `path[]`와 `edge_metadata[]`를 추출하므로,
CS-5-5 ExplorationTrail 컴포넌트가 다음 필드를 보유해야 한다.

- [ ] ExplorationTrail state에 `path: string[]` 유지
- [ ] ExplorationTrail state에 `edge_metadata: Array<{from, to, relation_type, truth_score}>` 유지
- [ ] 노드 탭 시 path + edge_metadata에 append
- [ ] undo 시 해당 지점 이후 path + edge_metadata 제거

### Watch 버튼 자체

- [ ] Watch 버튼 클릭 시 POST /watchlist/ 호출 (path + edge_metadata 포함)
- [ ] 토스트 메시지 표시
- [ ] Watchlist 열기 secondary action 동작
```

**영향**: cs_55(마켓뷰) 구현 시 이 2개 필드를 반드시 추가하도록 cross-reference 명시. 누락 시 cs_71 전체가 동작 불가.

---

## M1 — cs_73 Expand 후보에 relation_status + basis_summary

**문제**: ExpandDialog에서 후보 노드를 보여줄 때 "왜 이 종목이 추천됐는가"에 대한 설명이 없음. PM v1.2의 "엣지 설명 가능성" 원칙과 충돌.

**Before** (타입 정의)
```typescript
interface Candidate {
  ticker: string;
  name: string;
  relation_type: RelationType;
  truth_score: number;
  sector: string;
}
```

**After**
```typescript
interface Candidate {
  ticker: string;
  name: string;
  relation_type: RelationType;
  relation_status: 'confirmed' | 'probable' | 'weak';  // 신규
  truth_score: number;
  basis_summary: string;  // 신규 - RELATION_CONFIDENCE.md relation_basis_summary 직접 참조
  sector: string;
}
```

**UI 반영** (ExpandDialog)
```tsx
<div className="candidate-card">
  <div className="ticker-row">
    <span>{candidate.ticker}</span>
    <Badge status={candidate.relation_status}>{candidate.relation_type}</Badge>
  </div>
  <blockquote className="basis-summary">
    "{candidate.basis_summary}"
  </blockquote>
</div>
```

**영향**: Expand API(cs_64) 응답 스키마도 함께 업데이트 필요. Neo4j 쿼리에서 relation의 `status`와 `basis_summary` 속성을 반드시 RETURN에 포함.

---

## M2 — cs_73 Recheck 로컬 상태 갱신

**문제**: Recheck 호출 후 `fetchPath()`를 다시 호출하여 전체 경로를 재로드하는데, 서버 RTT가 2번 발생하고 Recheck 응답에 이미 최신 상태가 포함되어 있어 중복.

**Before**
```typescript
interface RecheckResult {
  headline: string;
  strengthened: Signal[];
  weakened: Signal[];
  path_intact: boolean;
  suggested_action: SuggestedAction;
}

function usePathDetail(pathId: string) {
  const recheck = async () => {
    const result = await api.recheck(pathId);
    await fetchPath();  // 전체 재로드 — 불필요한 왕복
    return result;
  };
}
```

**After**
```typescript
interface RecheckResult {
  headline: string;
  strengthened: Signal[];
  weakened: Signal[];
  path_intact: boolean;
  suggested_action: SuggestedAction;
  updated_why_now: WhyNowSnapshot;  // 신규 - 최신 스냅샷 포함
  new_status: PathStatus;           // 신규 - 상태 전이 결과
  last_rechecked_at: string;        // 신규 - 타임스탬프
}

function usePathDetail(pathId: string) {
  const [path, setPath] = useState<SavedPath | null>(null);

  const recheck = async () => {
    const result = await api.recheck(pathId);
    // 로컬 상태만 직접 갱신, fetchPath 재호출 없음
    setPath(prev => prev ? {
      ...prev,
      status: result.new_status,
      why_now_snapshot: result.updated_why_now,
      last_rechecked_at: result.last_rechecked_at,
    } : null);
    return result;
  };
}
```

**영향**: Recheck API(cs_48) 응답 스키마에 3개 필드 추가. 네트워크 RTT 1회 → 1회로 유지, 응답 페이로드만 살짝 증가.

---

## M3-a — cs_62 path_length SerializerMethodField

**문제**: SavedPath 직렬화 시 `full_path`는 배열 그대로 전송하는데, 프론트에서 `path.full_path.length`로 매번 계산. 카드 목록 렌더링 시 summary_path + "(+N)" 표시에 반복 사용.

**Before**
```python
class SavedPathSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedPath
        fields = ['id', 'user', 'full_path', 'summary_path', 'status',
                  'source_center', 'why_now_snapshot',
                  'created_at', 'updated_at', 'last_rechecked_at']
```

**After**
```python
class SavedPathSerializer(serializers.ModelSerializer):
    path_length = serializers.SerializerMethodField()

    class Meta:
        model = SavedPath
        fields = ['id', 'user', 'full_path', 'summary_path', 'path_length',
                  'status', 'source_center', 'why_now_snapshot',
                  'created_at', 'updated_at', 'last_rechecked_at']

    def get_path_length(self, obj) -> int:
        """프론트에서 summary_path + (+N) 표시용. N = path_length - len(summary_path)"""
        return len(obj.full_path) if obj.full_path else 0
```

**영향**: cs_72 PathCard 컴포넌트와 함께 변경. TypeScript 타입에도 반영(아래 M3-b).

---

## M3-b + C1 — cs_72 PathCard + pathStatus 공통 유틸

**문제**:
- M3-b: PathCard에서 `path.full_path.length - path.summary_path.length`를 반복 계산.
- C1: STATUS_BADGE 매핑과 formatRelativeTime이 cs_72(PathCard)와 cs_73(PathDetailView)에 각각 중복 정의됨.

**Before** (cs_72 PathCard)
```tsx
const STATUS_BADGE = {
  watching: { label: 'Watching', color: 'blue' },
  active: { label: 'Active', color: 'green' },
  archived: { label: 'Archived', color: 'gray' },
  resolved: { label: 'Resolved', color: 'purple' },
} as const;

function formatRelativeTime(iso: string): string {
  // cs_72, cs_73에 동일 로직 중복
}

function PathCard({ path }: { path: SavedPath }) {
  const extraNodes = path.full_path.length - path.summary_path.length;
  return (
    <div>
      <span>{path.summary_path.join(' → ')}</span>
      {extraNodes > 0 && <span>(+{extraNodes})</span>}
      <Badge {...STATUS_BADGE[path.status]} />
    </div>
  );
}
```

**After**

cs_72에 새 섹션 1.5 추가:

```markdown
## 1.5 공통 유틸 (utils/pathStatus.ts)

PathCard와 PathDetailView에서 공통 사용. 중복 정의 금지.

```typescript
// utils/pathStatus.ts
export const PATH_STATUS_BADGE = {
  watching: { label: 'Watching', color: 'blue' },
  active: { label: 'Active', color: 'green' },
  archived: { label: 'Archived', color: 'gray' },
  resolved: { label: 'Resolved', color: 'purple' },
} as const;

export function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const hours = Math.floor(diff / 3600000);
  if (hours < 1) return '방금 전';
  if (hours < 24) return `${hours}시간 전`;
  return `${Math.floor(hours / 24)}일 전`;
}
```
```

cs_72 PathCard:
```tsx
import { PATH_STATUS_BADGE, formatRelativeTime } from '@/utils/pathStatus';

interface SavedPath {
  // ... 기존 필드
  path_length: number;  // 신규 (백엔드 SerializerMethodField)
}

function PathCard({ path }: { path: SavedPath }) {
  const extraNodes = path.path_length - path.summary_path.length;  // 서버 계산값 사용
  return (
    <div>
      <span>{path.summary_path.join(' → ')}</span>
      {extraNodes > 0 && <span>(+{extraNodes})</span>}
      <Badge {...PATH_STATUS_BADGE[path.status]} />
      <time>{formatRelativeTime(path.updated_at)}</time>
    </div>
  );
}
```

cs_73 PathDetailView:
```tsx
// 기존 STATUS_BADGE, formatRelativeTime 로컬 정의 제거
import { PATH_STATUS_BADGE, formatRelativeTime } from '@/utils/pathStatus';
```

**완료 기준 업데이트** (cs_72):
```markdown
- [ ] utils/pathStatus.ts 생성 및 export
- [ ] PathCard가 PATH_STATUS_BADGE, formatRelativeTime import
- [ ] PathCard가 path.path_length 사용 (full_path.length 계산 금지)
- [ ] PathDetailView(cs_73)도 동일 유틸 import 확인
```

**영향**: 단일 진실 공급원(Single Source of Truth) 확보. 상태 라벨 변경 시 1곳만 수정. 원칙 4(1인 개발, 단순 구조) 부합.

---

## M4 — cs_63 centrality 조회 범위 축소

**문제**: Summary path 생성 시 `_fetch_centrality(path_tickers)`가 모든 노드의 centrality를 조회. landmark 선정에는 양 끝 노드(start/end)는 항상 포함되므로 centrality 불필요.

**Before**
```python
def generate_summary_path(full_path: List[str]) -> List[str]:
    if len(full_path) <= 3:
        return full_path

    # 전체 노드에 대해 centrality 조회 — 낭비
    centrality_map = _fetch_centrality(full_path)

    start, end = full_path[0], full_path[-1]
    middle = full_path[1:-1]

    best_middle = max(middle, key=lambda t: compute_landmark_score(
        t, centrality_map.get(t), ...
    ))
    return [start, best_middle, end]


def _fetch_centrality(tickers: List[str]) -> Dict[str, float]:
    """Neo4j GDS centrality 조회. 모든 티커에 대해 조회."""
    cypher = """
    MATCH (s:Stock) WHERE s.ticker IN $tickers
    RETURN s.ticker AS ticker, s.centrality_score AS score
    """
    return {r['ticker']: r['score'] for r in run_cypher(cypher, tickers=tickers)}
```

**After**
```python
def generate_summary_path(full_path: List[str]) -> List[str]:
    if len(full_path) <= 3:
        return full_path

    start, end = full_path[0], full_path[-1]
    middle_nodes = full_path[1:-1]  # 실제로 평가가 필요한 대상

    # middle_nodes만 centrality 조회
    centrality_map = _fetch_centrality(middle_nodes)

    best_middle = max(middle_nodes, key=lambda t: compute_landmark_score(
        t, centrality_map.get(t), ...
    ))
    return [start, best_middle, end]


def _fetch_centrality(middle_nodes: List[str]) -> Dict[str, float]:
    """
    Neo4j GDS centrality 조회.
    Summary path landmark 선정 전용 — 중간 노드(middle_nodes)만 대상.
    start/end는 항상 summary path에 포함되므로 조회 불필요.
    """
    if not middle_nodes:
        return {}
    cypher = """
    MATCH (s:Stock) WHERE s.ticker IN $tickers
    RETURN s.ticker AS ticker, s.centrality_score AS score
    """
    return {r['ticker']: r['score'] for r in run_cypher(cypher, tickers=middle_nodes)}
```

**영향**: 10-hop path 기준 Neo4j 쿼리 IN 절 크기 10 → 8로 축소. 실성능 향상은 미미하나 의도가 코드에서 명확해짐.

---

## L1 — cs_65 _maybe_transition_to_active docstring

**문제**: watching → active 전이 로직의 조건(Recheck 2회 + 24시간 경과)이 함수 내부에 구현되어 있는데 docstring에 반영 안 됨.

**Before**
```python
def _maybe_transition_to_active(saved_path: SavedPath) -> bool:
    """
    watching 상태의 path를 active로 전환.
    조건 충족 시 True 반환.
    """
    if saved_path.status != SavedPath.Status.WATCHING:
        return False

    recheck_count = saved_path.actions.filter(
        action=PathAction.ActionType.RECHECK
    ).count()

    first_recheck = saved_path.actions.filter(
        action=PathAction.ActionType.RECHECK
    ).order_by('created_at').first()

    if recheck_count >= 2 and first_recheck:
        elapsed = timezone.now() - first_recheck.created_at
        if elapsed >= timedelta(hours=24):
            saved_path.status = SavedPath.Status.ACTIVE
            saved_path.save(update_fields=['status', 'updated_at'])
            return True

    return False
```

**After**
```python
def _maybe_transition_to_active(saved_path: SavedPath) -> bool:
    """
    watching → active 전이 조건 판정 및 적용.

    MVP 전이 조건 (의도적 행동만 인정):
      - Recheck 액션이 2회 이상 실행되었고
      - 최초 Recheck로부터 24시간 이상 경과

    우발적 Recheck 1회만으로는 전이하지 않음.
    자동 판정(신호+continuity)은 v1.3 이후.

    Args:
        saved_path: 전이 검사 대상 SavedPath 인스턴스

    Returns:
        True: 전이 수행됨 (status 변경 + save 완료)
        False: 조건 미충족 또는 이미 watching이 아닌 상태
    """
    if saved_path.status != SavedPath.Status.WATCHING:
        return False

    recheck_count = saved_path.actions.filter(
        action=PathAction.ActionType.RECHECK
    ).count()

    first_recheck = saved_path.actions.filter(
        action=PathAction.ActionType.RECHECK
    ).order_by('created_at').first()

    if recheck_count >= 2 and first_recheck:
        elapsed = timezone.now() - first_recheck.created_at
        if elapsed >= timedelta(hours=24):
            saved_path.status = SavedPath.Status.ACTIVE
            saved_path.save(update_fields=['status', 'updated_at'])
            return True

    return False
```

**영향**: 순수 문서화 개선. 향후 조건 변경 시 docstring과 코드 동기화 원칙 수립.

---

## L2 — cs_71, cs_73 SOURCE_SLOTS 상수화

**문제**: source_slot 값이 하드코딩된 문자열로 산재 ("trail_watch", "next_best_chain", "chain_story_feed", "hidden_hub", "expand_from_watchlist", "alternatives_from_watchlist" 등).

**Before** (cs_71)
```typescript
// cs_71 Watch 버튼
await api.createWatchlist({
  full_path: trail.path,
  edge_metadata: trail.edge_metadata,
  source_center: trail.path[0],
  source_slot: 'trail_watch',  // 하드코딩
});
```

**After** (cs_71 SOURCE_SLOTS 정의 추가)
```typescript
// constants/sourceSlots.ts (신규)
export const SOURCE_SLOTS = {
  TRAIL_WATCH: 'trail_watch',
  NEXT_BEST_CHAIN: 'next_best_chain',           // v1.3 이후 피드 복귀 시 사용
  CHAIN_STORY_FEED: 'chain_story_feed',         // v1.3 이후
  HIDDEN_HUB: 'hidden_hub',                     // v1.3 이후
  EXPAND_FROM_WATCHLIST: 'expand_from_watchlist',      // 신규 — Expand로 저장
  ALTERNATIVES_FROM_WATCHLIST: 'alternatives_from_watchlist',  // 신규 — Alternatives로 저장
} as const;

export type SourceSlot = typeof SOURCE_SLOTS[keyof typeof SOURCE_SLOTS];

// cs_71 Watch 버튼
import { SOURCE_SLOTS } from '@/constants/sourceSlots';

await api.createWatchlist({
  full_path: trail.path,
  edge_metadata: trail.edge_metadata,
  source_center: trail.path[0],
  source_slot: SOURCE_SLOTS.TRAIL_WATCH,
});
```

**cs_73 반영**
```typescript
// Expand 후보 선택 시
await api.createWatchlist({
  full_path: [...path.full_path, chosen.ticker],
  source_center: path.source_center,
  source_slot: SOURCE_SLOTS.EXPAND_FROM_WATCHLIST,  // 기존: 'expand_from_watchlist'
});

// Alternatives 선택 시
await api.createWatchlist({
  full_path: replaceNodeInPath(path.full_path, targetIdx, chosen.ticker),
  source_center: path.source_center,
  source_slot: SOURCE_SLOTS.ALTERNATIVES_FROM_WATCHLIST,  // 기존: 'alternatives_from_watchlist'
});
```

**영향**: 매직 스트링 제거. IDE 자동완성 동작. source_slot 종류 추가/변경 시 1곳만 수정. 백엔드(cs_45, cs_62)에서도 동일 상수를 Python enum으로 미러링 권장(선택).

---

## 반영 확인 체크리스트

- [x] H1 — cs_61 PathAction.saved_path related_name='actions'
- [x] H2 — cs_71 CS-5-5 ExplorationTrail 스키마 선행 변경 섹션 추가 (4개 체크박스)
- [x] M1 — cs_73 Candidate에 relation_status + basis_summary, ExpandDialog에 blockquote 표시
- [x] M2 — cs_73 RecheckResult에 updated_why_now/new_status/last_rechecked_at 추가, usePathDetail.recheck가 setPath로 직접 갱신
- [x] M3-a — cs_62 SavedPathSerializer에 path_length SerializerMethodField
- [x] M3-b — cs_72 PathCard가 path.path_length 사용
- [x] M4 — cs_63 _fetch_centrality가 middle_nodes만 조회
- [x] L1 — cs_65 _maybe_transition_to_active docstring에 MVP 조건 명시
- [x] L2 — cs_71에 SOURCE_SLOTS 상수 파일, cs_73에서 상수 사용
- [x] C1 — cs_72에 utils/pathStatus.ts 섹션 1.5, cs_73에서 import

---

## 후속 작업 권장

1. **백엔드 SOURCE_SLOTS 미러링 (선택)**: `chainsight/constants/source_slots.py`를 추가하고 `SavedPath.source_slot`의 choices로 지정 권장. 단, MVP에서는 CharField + 유효성 검증만으로 충분.

2. **RecheckResult.new_status 검증**: cs_48(Recheck API) 구현 시 `new_status`를 응답에 반드시 포함해야 M2 프론트 로직이 동작. 누락 시 path.status와 서버 상태 불일치 발생 가능.

3. **Neo4j relation.basis_summary 속성 존재 확인**: cs_32(관계 Neo4j 동기화) 작업 지시서에서 basis_summary를 엣지 속성으로 저장하는지 확인. 누락 시 M1 기능 동작 불가.

4. **파일 시스템 리셋 대응**: Claude 세션 간 /mnt/user-data/outputs가 리셋되므로, 작업 산출물은 Claude Code 로컬 레포지토리(docs/chain_sight/task_instructions/)에 즉시 commit 권장.

---

**END OF DOCUMENT**
