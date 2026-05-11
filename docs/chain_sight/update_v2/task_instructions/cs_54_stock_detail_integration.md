# CS-5-4: 종목 상세 페이지 연계

> **작업 번호**: CS-5-4
> **로드맵 버전**: v1.4 (M5 설명 업데이트)
> **목표**: 종목 상세에 Chain Sight 미니 뷰 임베드 + 전용 페이지
> **예상 소요**: 1~2일
> **선행 조건**: CS-5-3 완료
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

## 전용 페이지

`/chainsight/{symbol}`: GraphView + SuggestionCards + TraceView + **MarketView(CS-5-5)** 통합

## 완료 기준

```
□ 종목 상세 Chain Sight 탭 활성화 (Coming Soon 제거)
□ 미니 그래프 렌더링
□ "전체 보기" → 전용 페이지 이동
□ 전용 페이지 통합 동작
```

→ **다음**: cs_55 (마켓뷰 + Watchlist UI 시작)

**END OF DOCUMENT**
