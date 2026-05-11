# CS-7-2: Watchlist 화면 (카드 리스트)

> **작업 번호**: CS-7-2
> **로드맵 버전**: v1.4 (신규)
> **목표**: Path Watchlist 카드 리스트 + path_signature 태그 + 필터/정렬
> **예상 소요**: 2~3일
> **선행 조건**: CS-7-1 완료 + CS-6-2 API 작동
> **산출물**: `components/chainsight/WatchlistView.tsx`

---

## 화면 구조

```
┌────────────────────────────────────────────────────────┐
│ 📋 Path Watchlist                 [필터 ▼] [정렬 ▼]    │
├────────────────────────────────────────────────────────┤
│                                                        │
│ ┌────────────────────────────────────────────────┐     │
│ │ NVDA → AMAT → SMCI (+7)                        │     │
│ │ 🏷️ 공급망 중심 · 반도체 장비                      │     │
│ │ ● watching · 3일 전 저장                        │     │
│ │                                                 │     │
│ │ [Recheck]  [Expand]        [⋮ Archive/Resolve]  │     │
│ └────────────────────────────────────────────────┘     │
│                                                        │
│ ┌────────────────────────────────────────────────┐     │
│ │ AAPL → TSM → ASML                              │     │
│ │ 🏷️ 공급망 중심 · 반도체 제조                      │     │
│ │ ● active · 1일 전 Recheck                      │     │
│ │                                                 │     │
│ │ [Recheck]  [Expand]        [⋮ Archive/Resolve]  │     │
│ └────────────────────────────────────────────────┘     │
│                                                        │
│ ┌─ 빈 상태 ──────────────────────────────────────┐     │
│ │ 아직 저장한 경로가 없어요.                        │     │
│ │ Chain Sight에서 탐색하며 📌 Watch 버튼을 눌러보세요 │     │
│ └────────────────────────────────────────────────┘     │
└────────────────────────────────────────────────────────┘
```

## 카드 구성 요소

- summary_path 표시 (path_length - summary_path 길이 = "+N" 표시)
- path_signature 태그 라인 (🏷️)
- status 뱃지 + 시간 (상대 시간)
- Quick actions: [Recheck] [Expand] (primary), [⋮] → Archive/Resolve (secondary)
- Alternatives: Full path view에서만 접근 (CS-5-9)

## 필터/정렬

- 필터: status만 (watching, active, archived, resolved)
- 정렬: -updated_at 고정
- ⚠️ MVP: 위 2개만. intent별/path_length별/sector별 필터는 v1.3 이후.
- CS-4-5 API query params 활용

## 카드 탭 → Full path view (CS-5-9)

## 완료 기준

```
□ 카드 리스트 렌더링
□ summary_path + path_signature + status 표시
□ Quick actions 버튼 동작 (Recheck/Expand → API 호출)
□ 필터/정렬 동작
□ 빈 상태 UI
□ 무한 스크롤 또는 페이지네이션
```

→ **다음**: cs_73 (Full Path View)

**END OF DOCUMENT**
