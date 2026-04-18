# Chain Sight PM / 설계문서

> **버전**: v1.2 (v1.4 로드맵 반영)  
> **최종 수정**: 2026-04-17  
> **서비스 위치**: Dashboard → **Chain Sight(발견)** → 1차 검증 → Thesis Control → Portfolio  
> **설계 원칙**: 1인 개발 · 엄지 조작 우선 · 수학 핵심, LLM 옵션 · batch-first

---

## 1. 제품 정의

Chain Sight는 **주식 시장 관계 탐색 엔진**이다. 기업 간 공급망, 경쟁, 테마 관계를 그래프로 시각화하고, 사용자가 "파도타기"하듯 종목 간 연결을 탐색할 수 있게 한다.

핵심 경험:
- 기업 간 관계를 한눈에 파악 (그래프 시각화)
- 시장 흐름 속 숨겨진 연결을 자연스럽게 발견 (시드 노드 + AI 가이드)
- 발견한 경로를 전략 단위로 관리 (Path Watchlist)

---

## 2. 화면 구조

### 2-1. MarketView (메인 진입점) — CS-5-5

3영역 레이아웃:

```
┌─────────────────────────────────────────┐
│ ① 섹터 버튼 바 (증감률 그라데이션)        │
├─────────────────────────────────────────┤
│                                         │
│ ② 그래프 캔버스                          │
│   · 시드 노드 bounce 애니메이션           │
│   · 노드 탭 → 중심 이동 + 1-hop 확장     │
│   · Market 관계 토글 (기본 OFF)          │
│                                         │
├─────────────────────────────────────────┤
│ ③ 탐색 트레일 + [Watch] 버튼            │
└─────────────────────────────────────────┘
```

v1.4 변경: 체인 스토리 피드(④)는 v1.3 이후로 미룸 (Feed API 미구현).

반응형: Mobile(세로 스택) / Tablet(그래프 전폭 + 하단 트레일) / Desktop(좌 트레일 + 중앙 그래프 + 우 상세패널)

### 2-2. Watchlist (경로 관리) — CS-7-2

```
┌─────────────────────────────────────────┐
│ Path Watchlist            [필터] [정렬]  │
├─────────────────────────────────────────┤
│ ┌─────────────────────────────────────┐ │
│ │ NVDA → AMAT → SMCI (+7)             │ │
│ │ 🏷️ 공급망 중심 · 반도체 장비          │ │
│ │ ● watching · 3일 전                  │ │
│ │ [Recheck] [Expand]        [··· 더보기]│ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### 2-3. Full Path View (경로 상세) — CS-7-3

```
┌─────────────────────────────────────────┐
│ ← Watchlist                             │
│ Recheck: "장비 체인 유지, AMAT 거래량 급증"│
│ ▲ AMAT strengthened                     │
│ 추천: Expand                            │
│                                         │
│ [NVDA]──SUPPLY──▶[TSM]──SUPPLY──▶[ASML] │
│     각 노드 탭 → "이 노드 대신?"         │
│                                         │
│ Expand 후보: MU (85), KLAC (65)         │
│ [Recheck] [Expand] [Archive] [Resolve]  │
└─────────────────────────────────────────┘
```

---

## 3. 시드 노드 시스템 — CS-4-4

"지금 탐색할 가치가 있는 노드"를 동적으로 추천.

```
heat_score = 0.25 × price_signal      (5일 수익률 절댓값 percentile)
           + 0.25 × volume_signal     (당일/20일 평균 비율, max 3배)
           + 0.25 × relation_change   (7일 내 RelationConfidence 변경 수)
           + 0.25 × news_activation   (3일 내 CoMention 수)
```

- Celery 일간 배치 → Neo4j :Stock 노드에 heat_score 속성 저장
- 섹터 선택 시 market cap 상위 20개 중 heat_score 상위 3개를 시드 노드로 강조
- MVP: 동일 가중치(0.25). 사용자 클릭 데이터 축적 후 A/B 테스트로 튜닝

---

## 4. Path Watchlist

### 4-1. 정의

사용자가 의미 있다고 판단한 탐색 경로를 저장하여 모니터링·확장·대안 탐색할 수 있는 전략 관리 시스템.

### 4-2. 상태 모델

| 상태 | 의미 | 진입 조건 | MVP |
|------|------|----------|-----|
| watching | 추적 대상으로 저장 | Watch 액션 | ✅ |
| active | 적극 추적 중 | Recheck 2회 + 24시간 경과 | ✅ |
| archived | 비활성화 | Archive 액션 | ✅ |
| resolved | 전략 종료 | Resolve 액션 | ✅ |

v1.3 이후: strengthening / weakening / broken 자동 상태 전환

### 4-3. 전이 규칙

```
watching ──(Recheck 2회 + 24h)──→ active
any ──(Archive)──→ archived
any ──(Resolve)──→ resolved
```

"Recheck 2회 + 24시간 경과" 조건은 우발적 탭 1회로 전이되는 것을 방지하기 위한 보수적 설계.

---

## 5. 액션 중심 UX

| 액션 | 입력 | 출력 | CS 번호 |
|------|------|------|--------|
| **Watch** | 현재 탐색 경로 | SavedPath 생성 + edge_snapshot + path_signature | CS-6-2 |
| **Recheck** | SavedPath id | headline + strengthened/weakened + suggested_action | CS-6-5 |
| **Expand** | SavedPath id | 마지막 노드 1-hop 후보 top 5~10 | CS-6-6 |
| **Alternatives** | SavedPath id + target_ticker | 해당 노드 동일 relation_type 대안 top 3 | CS-6-7 |
| **Archive** | SavedPath id | status=archived | CS-6-2 |
| **Resolve** | SavedPath id | status=resolved | CS-6-2 |

### Recheck 응답 구조

```json
{
  "headline": "장비 체인 관계 유지 중, AMAT 거래량 급증",
  "strengthened": [{"from":"NVDA","to":"TSM","signal":"truth_score 60→85"}],
  "weakened": [],
  "path_intact": true,
  "suggested_action": "expand",
  "suggested_reason": "모든 관계 유지 — 확장 탐색 추천"
}
```

Recheck 로직 6단계:
1. edge_snapshot(저장 시점) vs 현재 상태 비교
2. strengthened / weakened / broken 분류
3. path_intact 판정
4. headline 템플릿 생성
5. suggested_action 결정
6. edge_snapshot + path_signature + summary_path 갱신

### Alternatives (MVP 범위)

MVP에서는 **노드 단위 대안 제안**만 지원. "이 경로에서 이 노드를 바꾸면?" path-level 비교는 v1.3 이후.

---

## 6. Summary Path + Path Signature

### Summary Path

full_path(예: 10개 노드)를 3~5개 landmark로 압축.

선정 규칙:
1. 시작 노드 + 끝 노드는 항상 포함
2. 중간 노드 중 landmark_score 상위 선택
3. landmark_score = why_now(40%) + bridge_score(45%) + revisit(15%) — GDS centrality 없을 때

bridge_score: 전후 sector/industry가 달라지는 전환점이면 높음.

### Path Signature

edge_snapshot의 relation_type 빈도 → 경로 성격 태그.

```
SUPPLIES_TO 50%+ → "공급망 중심"
COMPETES_WITH 50%+ → "경쟁 구도"
PEER_OF 50%+ → "동종 비교"
혼합 → "복합 탐색"
```

+ 대표 sector(최빈값) 결합: `"공급망 중심 · 반도체 장비"`

---

## 7. 데이터 모델

### SavedPath (Canonical: CS-6-1)

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| user | FK (nullable) | MVP 단일 사용자 |
| path_nodes | JSONField | ticker 배열 |
| summary_path | JSONField | landmark 배열 |
| path_signature | CharField(80) | 경로 성격 태그 |
| edge_snapshot | JSONField | 저장 시점 관계 스냅샷 |
| why_now_snapshot | JSONField | 저장 시점 시그널 스냅샷 |
| source_center | CharField(10) | Watch 시 그래프 중심 노드 |
| source_slot | CharField(40) | Watch 발생 UI 위치 |
| status | CharField(20) | watching/active/archived/resolved |
| recheck_count | PositiveInteger | Recheck 누적 횟수 |
| created_at | DateTime | 생성 시각 |
| updated_at | DateTime | 수정 시각 |

### PathAction

| 필드 | 타입 | 설명 |
|------|------|------|
| saved_path | FK | SavedPath 참조 |
| action_type | CharField(20) | watch/recheck/expand/alternatives/archive/resolve |
| metadata | JSONField | 액션별 부가 데이터 |
| created_at | DateTime | 실행 시각 |

### 필드명 통일 결정 (2026-04-17)

- `path_nodes` (O) / `full_path` (X) — 의미 명확
- `action_type` (O) / `action` (X) — Django 충돌 방지
- `path_length` 제거 — SerializerMethodField로 제공
- `primary_intent` 제거 — source_slot으로 충분
- `recheck_count` 추가 — watching→active 전이 효율화

---

## 8. 추천 엔진 연결

### MVP 개인화 원칙

> MVP에서는 PathAction 이벤트를 수집·저장만 하고, 추천 로직이나 heat_score에 반영하지 않는다. 모든 사용자에게 동일한 비개인화 기본값을 적용한다. 개인화 로직 반영은 v1.3 이후.

### 전략 루프

```
Discover (MarketView 탐색)
  → Watch (경로 저장)
    → Monitor (Recheck)
      → Expand (확장) / Alternatives (대안)
        → Resolve (전략 종료)
          → Re-discover (새 탐색)
```

PathAction 데이터가 쌓이면 v1.3에서:
- preferred_relations: 자주 저장하는 관계 유형 → heat_score 보너스
- explorer_type: 깊이 탐색형/넓이 탐색형 분류 → 슬롯 강화
- 활성화 조건: PathAction 50건 이상

---

## 9. 성능 가드레일

| 항목 | 제한 |
|------|------|
| 초기 렌더링 노드 수 | 최대 50개 |
| 그래프 depth | 최대 2 |
| Neo4j 쿼리 LIMIT | 100 paths |
| 엣지 표시 기준 | confirmed 또는 probable |
| Market 관계 표시 | 토글, 기본 OFF |
| path_nodes 최대 길이 | 10개 |

---

## 10. MVP 출시 범위

### 포함

- MarketView 3영역 (섹터바 + 그래프 + 트레일)
- 시드 노드 (heat_score bounce)
- Watch 버튼 (탐색 트레일)
- Path Watchlist 카드 리스트
- Summary path + path_signature 태그
- 상태: watching / active / archived / resolved
- 액션: Recheck / Expand / Alternatives / Archive / Resolve
- Recheck headline + suggested_action
- edge_snapshot 기반 변화 추적
- 이벤트 로깅

### 제외 (v1.3 이후)

- 체인 스토리 피드 (Feed API + 추천 엔진 필요)
- Strengthening / Weakening / Broken 자동 상태 전환
- path-level Compare (대안 경로 탐색)
- 개인화 로직 반영
- Path cluster 그룹핑
- Promote 액션
- LLM 기반 전략 요약

---

## 11. 실패 모드 + 대응

| 실패 모드 | 원인 | 대응 |
|----------|------|------|
| 그래프가 대형주만 순환 | 소형주 관계 부족 | ETF 전체 Holdings, SEC 공급망 |
| "왜 연결됐지?" 모름 | 엣지 설명 없음 | relation_basis_summary |
| Watchlist가 북마크함 | 상태 변화 없음 | Recheck/Expand 루프 |
| Path가 너무 길어 관리 어려움 | full path만 노출 | summary path + 펼침 |
| 상태 문구가 투자 조언 | "Strengthening" 오해 | 중립 문구 + 면책 문구 |

---

## 12. 구현 순서 (로드맵 연결)

```
Phase 4: 그래프 API (CS-4-1~3) + Seed Node (CS-4-4)
Phase 5: 코어 프론트엔드 (CS-5-1~6)
Phase 6: Watchlist 백엔드 (CS-6-1~7) → M4
Phase 7: Watchlist 프론트엔드 (CS-7-1~3) → M5 (MVP 릴리즈)
```

**END OF DOCUMENT**
