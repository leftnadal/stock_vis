# CS-5-1: Chain Sight 프론트엔드 — 그래프 시각화 + 전용 페이지

> **완료일**: 2026-04-04

## 생성된 파일 (12개)

| 파일 | 역할 |
|------|------|
| `frontend/types/chainsight.ts` | 타입 정의 (GraphResponse, SuggestionCategory, TraceResponse, ForceNode, ForceLink 등) |
| `frontend/services/chainsightService.ts` | API 클라이언트 (fetchGraph, fetchSuggestions, fetchTrace) |
| `frontend/hooks/useChainsight.ts` | TanStack Query 훅 (useGraphData, useSuggestions, useTrace) |
| `frontend/components/chainsight/graphStyles.ts` | 관계 타입 6색 + 섹터 11색 + 노드 크기 계산 |
| `frontend/components/chainsight/GraphCanvas.tsx` | ForceGraph2D 메인 캔버스 (Spotlight + Lazy expansion) |
| `frontend/components/chainsight/RelationLegend.tsx` | 관계 타입 범례 패널 |
| `frontend/components/chainsight/NodeDetailPanel.tsx` | 우측 패널 (노드 상세 + CTA 4개) |
| `frontend/components/chainsight/AIGuidePanel.tsx` | 좌측 패널 (카테고리 카드 + Chain Trace 입력) |
| `frontend/components/chainsight/TracePathView.tsx` | Trace 경로 시각화 + 단계별 설명 |
| `frontend/components/chainsight/GraphMiniView.tsx` | 종목 상세 탭용 미니 그래프 (정적) |
| `frontend/app/chainsight/[symbol]/page.tsx` | 전용 워크스페이스 (3-panel: AI Guide + 그래프 + 노드 상세) |

## 수정된 파일

| 파일 | 변경 |
|------|------|
| `frontend/app/stocks/[symbol]/page.tsx` | Chain Sight 탭 플레이스홀더 → GraphMiniView 교체 |

## 라이브러리 추가

- `react-force-graph-2d` (npm install)

## 아키텍처

```
/chainsight/[symbol] 전용 워크스페이스
├── 좌측 240px: AIGuidePanel (카테고리 필터 + Chain Trace)
├── 중앙 flex-1: GraphCanvas (ForceGraph2D, dynamic import)
│   ├── 관계 타입별 6색 엣지 (실선/점선/굵기 차등)
│   ├── 섹터별 11색 노드
│   ├── Spotlight 모드 + cooldownTicks 80
│   └── 카테고리 필터링 (비활성 노드 투명도 조절)
├── 우측 320px: NodeDetailPanel (프로파일 + CTA)
│   ├── 가설 생성 → /thesis/new?symbol=...&from=...
│   ├── Validation 보기 → /stocks/...?tab=validation
│   ├── 여기서 탐색 시작 → /chainsight/...
│   └── 경로 찾기 → Trace 패널 연동
└── 하단: RelationLegend + 메타 정보

/stocks/[symbol]?tab=chain-sight 미니 뷰
├── GraphMiniView (360px, 정적 스냅샷)
├── 연결 종목 태그 (상위 6개)
└── "전체 탐색" → /chainsight/[symbol]
```

## TypeScript 에러

- Chain Sight 관련: **0건**
- 기존 thesis mock 에러 3건 (이번 작업 무관)

## 다음 작업

→ CS-5-2~4: 프로 기능 (필터 패널, 오버레이, 노드 비교), 모바일 카드 리스트
  또는 브라우저 테스트 후 후속 작업 결정
