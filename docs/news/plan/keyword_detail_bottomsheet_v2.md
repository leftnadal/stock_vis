# 키워드 상세 BottomSheet v2 — 가로 스크롤 Strip + 데스크탑 너비 제한

## 배경

키워드 상세 BottomSheet v1이 구현 완료된 상태. 사용성 개선을 위해 두 가지 보완을 진행한다.

### 문제
1. **키워드 전환 비효율**: 다른 키워드를 보려면 시트 닫기 → 카드에서 다른 키워드 클릭 → 시트 열기 (3액션)
2. **데스크탑 가독성**: 와이드스크린(1440px+)에서 시트가 전체 가로를 차지하여 텍스트 줄이 지나치게 김

### 해결
1. 시트 상단에 **가로 스크롤 키워드 Strip** → 1액션(탭)으로 키워드 전환
2. 시트 패널에 **max-w-2xl mx-auto** → 672px 너비 제한

---

## 의사결정 기록

### BottomSheet vs Inline Expand (2026-03-26)
UI/UX, Frontend, Investment 3개 에이전트 협업 분석.
- **BottomSheet 채택** (2:1) — 레이아웃 안정성, 모바일 네이티브 패턴, 현재 카드 구조(max-h 200px) 호환
- Inline Expand의 "맥락 유지" 약점은 시트 내 키워드 네비게이션으로 보완

### 이전/다음 버튼 vs 가로 스크롤 Strip vs 키워드 Grid (2026-03-26)
3개 에이전트 재분석.
- **가로 스크롤 Strip 채택** (2:1) — 공간 효율(1행 ~40px), 콘텐츠 영역 고정, 모바일 엄지 동선
- 이전/다음 버튼: 하나씩 옮기는 것이 불편 (사용자 피드백)
- 키워드 Grid: 2-4행 차지하여 50vh 내 콘텐츠 영역 부족

---

## 구현 설계

### 변경 파일

| 파일 | 변경량 | 내용 |
|------|--------|------|
| `frontend/components/thesis/common/BottomSheet.tsx` | ~1줄 | `max-w-2xl mx-auto` 추가 |
| `frontend/components/news/KeywordDetailSheet.tsx` | ~60줄 | Props 변경 + activeIndex + Strip UI + scrollIntoView |
| `frontend/components/news/DailyKeywordCard.tsx` | ~5줄 | props 전달 변경 |
| `frontend/hooks/useNews.ts` | ~2줄 | `keepPreviousData` 추가 |

### KeywordDetailSheet Props 변경

```
Before: { isOpen, onClose, date, keywordIndex, keyword }
After:  { isOpen, onClose, date, initialIndex, keywords }
```

### Strip pill 디자인

BottomSheet(bg-gray-900) 전용 dark 스타일. KeywordBadge 재활용하지 않음.
- active: `ring-2 ring-{sentiment}-400` + 진한 배경
- inactive: `bg-{sentiment}-900/30` + 연한 테두리
- sentiment 아이콘(TrendingUp/Down/Minus) + 텍스트만 표시

### 콘텐츠 전환

- `keepPreviousData`로 키워드 전환 시 이전 데이터 유지
- 캐시 히트(staleTime 30분): 즉시 전환
- 캐시 미스: 이전 콘텐츠 위에 반투명 로딩 오버레이

### 가로 스크롤 참조 패턴

`frontend/components/eod/SignalFilterTabs.tsx` (line 33):
```
flex items-center gap-2 overflow-x-auto pb-1 scrollbar-hide
```
`scrollbar-hide` 클래스: `frontend/app/globals.css` (line 85)

---

## 검증 체크리스트

- [ ] TypeScript 체크 통과
- [ ] 키워드 Strip 가로 스크롤 (모바일 375px)
- [ ] active 키워드 탭 → 콘텐츠 전환 + 자동 center 스크롤
- [ ] 캐시 히트/미스 양쪽 시나리오
- [ ] 데스크탑 max-w-2xl 너비 제한
- [ ] thesis BottomSheet regression 없음
