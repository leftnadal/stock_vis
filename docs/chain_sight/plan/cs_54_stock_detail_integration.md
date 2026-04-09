# CS-5-4: 종목 상세 페이지 연계

> **작업 번호**: CS-5-4
> **목표**: 종목 상세에 Chain Sight 미니 뷰 임베드 + 전용 페이지
> **예상 소요**: 1~2일
> **선행 조건**: CS-5-1~5-3 완료
> **산출물**: ChainSightMiniView.tsx, 종목 상세 수정, 전용 페이지

---

## 연계 구조

```
종목 상세 페이지
├── 기본 정보 (기존)
├── 재무제표 (기존)
├── 1차 검증 (기존)
└── Chain Sight 탭 ← CS-0-0에서 "Coming Soon" → 여기서 활성화
    ├── 미니 그래프 (1-depth, 축소, 인터랙션 비활성)
    ├── 연결 종목 태그 (상위 6개)
    └── "전체 보기 →" → /chainsight/{symbol}
```

## ChainSightMiniView

- ForceGraph2D height=256, zoom/pan 비활성
- 연결 종목 수 표시 ("12개 종목과 연결")
- 상위 6개 ticker 태그 (링크)

## 전용 페이지

`/chainsight/{symbol}`: GraphView + SuggestionCards + TraceView 통합

## 완료 기준

```
□ 종목 상세 Chain Sight 탭 활성화 (Coming Soon 제거)
□ 미니 그래프 렌더링
□ "전체 보기" → 전용 페이지 이동
□ 전용 페이지 통합 동작

★ M5 달성: "사용자 경험 가능" — Chain Sight MVP 릴리즈
```

---

## MVP 이후

- DC-5: Marketaux 뉴스 자연 축적
- DC-6: 수익화 이후 Finnhub Premium
- 서비스 연계: Thesis Control, Portfolio 등 각 MVP 이후

**END OF DOCUMENT**
