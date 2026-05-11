# CS-5-3: Chain Trace 시각화

> **작업 번호**: CS-5-3
> **목표**: 두 종목 간 경로 하이라이트 + 단계별 설명 UI
> **예상 소요**: 2~3일
> **선행 조건**: CS-4-3 + CS-5-1
> **산출물**: `components/chainsight/TraceView.tsx`

---

## UI 구조

```
From: [AAPL]  →  To: [TSLA]  [Trace!]

AAPL ──PEER_OF──▶ MSFT ──PEER_OF──▶ TSLA

Step 1: AAPL → MSFT — Peer relationship (finnhub, fmp)
Step 2: MSFT → TSLA — News co-mention (12 articles)

경로 길이: 2단계 | 대안 경로: 3개
```

## 핵심 동작

- from/to 입력 → Trace API 호출
- 노드 체인 시각화 (가로 스크롤)
- 각 step: 관계 타입 한글 라벨 + basis_summary
- 경로 없는 경우 안내 메시지

## 완료 기준

```
□ Trace 실행 → 경로 표시
□ 단계별 설명
□ 경로 없음 안내
□ 모바일 가로 스크롤
```

→ **다음**: cs_54

**END OF DOCUMENT**
