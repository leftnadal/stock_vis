# Phase 7 완료 보고서: CS-7-1, CS-7-2, CS-7-3

> **완료일**: 2026-04-18
> **브랜치**: `tier1/code-quality-fixes`
> **마일스톤**: M5 달성 — "사용자 경험 가능" Chain Sight MVP 릴리즈

---

## 커밋 이력 (Phase 6 + Phase 7)

| SHA | 메시지 | Phase |
|-----|--------|-------|
| `1c62a16` | CS-6-1 SavedPath/PathAction 모델 검증 + admin 등록 | 6 |
| `dd8f2cf` | CS-6-2 Watchlist CRUD API + archive/resolve | 6 |
| `750746a` | CS-6-3 Summary path landmark 압축 알고리즘 | 6 |
| `e610cd5` | CS-6-5 Recheck API 6단계 로직 | 6 |
| `0edf4aa` | CS-6-6 Expand API (1-hop 확장 후보 + 종합 점수 정렬) | 6 |
| `c6836bd` | CS-6-7 Alternatives API (노드 대안 탐색) — M4 달성 | 6 |
| `ee0f722` | CS-7-1 Watch 버튼 + 탐색 흐름 통합 | 7 |
| `ec6d562` | CS-7-2 Watchlist 카드 리스트 | 7 |
| `61d8c91` | CS-7-3 Full Path View + 액션 UX — M5 달성 | 7 |

---

## CS-7-1: Watch 버튼 + 탐색 흐름 통합

### 산출물

| 파일 | 역할 |
|------|------|
| `frontend/types/pathWatchlist.ts` | 17개 TypeScript 인터페이스 (SavedPath, Recheck, Expand, Alternatives) |
| `frontend/services/pathWatchlistService.ts` | 9개 API 함수 (authAxios 사용) |
| `frontend/hooks/usePathWatchlist.ts` | 9개 TanStack Query 훅 (query + mutation) |
| `frontend/components/chainsight/WatchButton.tsx` | 핀 아이콘 Watch 버튼 + 토스트 |
| `frontend/components/chainsight/ExplorationTrail.tsx` (수정) | WatchButton 통합 (오른쪽 고정) |

### 완료 기준 확인

- [x] 탐색 트레일 바에 Watch 버튼 노출 (stock 노드 2개 이상일 때)
- [x] 탭 → API 호출 → 토스트 → 아이콘 상태 변경 (PinOff → Pin + "Watching")
- [x] 토스트 secondary action: "Watchlist 열기" → `/chainsight/watchlist` 이동
- [x] 이미 저장된 path는 "Watching" 표시 (로컬 state)

---

## CS-7-2: Watchlist 카드 리스트 화면

### 산출물

| 파일 | 역할 |
|------|------|
| `frontend/lib/utils/pathStatus.ts` | PATH_STATUS_BADGE, formatRelativeTime 유틸 |
| `frontend/components/chainsight/PathCard.tsx` | 경로 카드 (summary_path + signature + 액션) |
| `frontend/app/chainsight/watchlist/page.tsx` | Watchlist 페이지 (필터 + 카드 리스트 + 빈 상태) |

### 완료 기준 확인

- [x] 카드 리스트 렌더링 (summary_path → 화살표 체인, +N 표시)
- [x] path_signature 태그 + status 뱃지 + 상대 시간
- [x] Quick actions: Recheck/Expand 버튼 + ⋮ 메뉴(Archive/Resolve)
- [x] status 필터 드롭다운 (전체/Watching/Active/Archived/Resolved)
- [x] -updated_at 정렬 (서버 기본값)
- [x] 빈 상태 UI: "아직 저장한 경로가 없어요" + Chain Sight 링크

---

## CS-7-3: Full Path View + 액션 UX

### 산출물

| 파일 | 역할 |
|------|------|
| `frontend/components/chainsight/FullPathView.tsx` | Full Path View (248줄) |
| `frontend/app/chainsight/watchlist/[id]/page.tsx` | 라우트 페이지 |

### 완료 기준 확인

- [x] full_path 전체 노드 체인 표시 (가로 스크롤, 엣지 라벨)
- [x] Recheck headline + strengthened/weakened/broken 시각화 (▲/▼/— 아이콘)
- [x] suggested_action + suggested_reason 표시
- [x] 노드 탭 → Alternatives API 호출 + 인라인 결과 표시
- [x] Expand 후보 표시 (ticker, name, relation_type, truth_score, why_summary)
- [x] 액션 버튼 4개: Recheck/Expand/Archive/Resolve
- [x] Recheck 후 로컬 상태 직접 갱신 (fetchPath 재호출 없음)
- [x] archived/resolved 상태에서 액션 버튼 비활성화
- [x] 모바일 가로 스크롤 (overflow-x-auto)

---

## Watchlist API 엔드포인트 전체 목록

| # | Method | URL | 기능 | FE 연동 |
|---|--------|-----|------|---------|
| 1 | POST | `/api/v1/chainsight/watchlist/` | Watch (경로 저장) | WatchButton |
| 2 | GET | `/api/v1/chainsight/watchlist/` | 목록 (status 필터) | WatchlistPage |
| 3 | GET | `/api/v1/chainsight/watchlist/{uuid}/` | 상세 | FullPathView |
| 4 | DELETE | `/api/v1/chainsight/watchlist/{uuid}/` | 삭제 | useDeletePath |
| 5 | POST | `/api/v1/chainsight/watchlist/{uuid}/archive/` | Archive | PathCard/FullPathView |
| 6 | POST | `/api/v1/chainsight/watchlist/{uuid}/resolve/` | Resolve | PathCard/FullPathView |
| 7 | POST | `/api/v1/chainsight/watchlist/{uuid}/recheck/` | Recheck | FullPathView |
| 8 | POST | `/api/v1/chainsight/watchlist/{uuid}/expand/` | Expand | FullPathView |
| 9 | POST | `/api/v1/chainsight/watchlist/{uuid}/alternatives/` | Alternatives | FullPathView |

---

## 테스트 결과

### 백엔드 (54 passed)

| 테스트 파일 | 수 |
|------------|-----|
| test_path_watchlist_models.py | 6 |
| test_watchlist_api.py | 11 |
| test_summary_path.py | 7 |
| test_recheck.py | 18 |
| test_expand.py | 6 |
| test_alternatives.py | 6 |
| **합계** | **54 passed (1.81s)** |

### 프론트엔드

- TypeScript 컴파일: 성공 (Compiled successfully)
- 빌드 에러: `/chainsight` 페이지 기존 `useSearchParams` prerender 에러 (Phase 7 변경과 무관)

---

## MVP 플로우

```
1. /chainsight 에서 탐색 → stock 노드 2개 이상 선택
2. ExplorationTrail 오른쪽 📌 Watch 버튼 클릭
3. 토스트: "경로가 저장되었습니다" + "Watchlist 열기" 액션
4. /chainsight/watchlist 에서 카드 리스트 확인
5. 카드 클릭 → /chainsight/watchlist/{id} Full Path View
6. Recheck 버튼 → headline + strengthened/weakened 시각화
7. 노드 탭 → Alternatives 탐색
8. Expand 버튼 → 확장 후보 표시
9. Archive/Resolve → 상태 변경
```

---

## ★ M5 달성: "사용자 경험 가능" — Chain Sight MVP 릴리즈
