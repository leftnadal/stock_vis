# PR-5: FE 탐색 상태 + 섹터 바 + 그래프 캔버스

> **완료일**: 2026-04-10
> **브랜치**: `data_structure_remodeling_V1`

## 목표

마켓 뷰 페이지 골격 + 공유 탐색 상태 + ① 섹터 바 + ② 그래프 캔버스 구현.

## 생성된 파일

| 파일 | 역할 |
|------|------|
| `frontend/lib/stores/explorationStore.ts` | Zustand 탐색 상태 (7개 상태 + 8개 액션) |
| `frontend/hooks/useMarketView.ts` | TanStack Query hooks 4종 (seeds, sectorGraph, neighbors, signalFeed) |
| `frontend/components/chainsight/SectorBar.tsx` | ① 섹터 버튼 바 (가로 스크롤, 선택/재탭 토글) |
| `frontend/components/chainsight/MarketGraphCanvas.tsx` | ② 그래프 캔버스 (react-force-graph-2d) |
| `frontend/app/chainsight/page.tsx` | 마켓 뷰 메인 페이지 + `?focus=` 딥링크 |

## 수정된 파일

| 파일 | 변경 |
|------|------|
| `frontend/types/chainsight.ts` | 마켓 뷰 타입 14종 추가 (SeedNode, MarketNode, Neighbor, ChainSignal 등) |
| `frontend/services/chainsightService.ts` | API 클라이언트 4종 추가 (fetchSeeds, fetchSectorGraph, fetchNeighbors, fetchSignals) |
| `frontend/components/layout/Header.tsx` | Chain Sight 네비게이션 추가 (데스크톱 + 모바일) |
| `frontend/app/stocks/[symbol]/page.tsx` | Chain Sight 탭에 "Chain Sight에서 보기" 딥링크 버튼 추가 |

## Zustand 탐색 상태

```typescript
interface ExplorationState {
  selectedSector: string | null;
  centerSymbol: string | null;
  trail: TrailNode[];
  historyNodes: string[];          // 좌측 히스토리 (최근 3개)
  currentNeighbors: Neighbor[];
  selectedRelationGroup: string | null;
  highlightedChain: string | null;
}
```

### 상태 전이 액션

| 액션 | 동작 |
|------|------|
| `selectSector(sector)` | 섹터 선택 → trail 초기화, center null |
| `selectNode(symbol)` | 중심 이동 → trail push, 이전 center → historyNodes |
| `undoToTrailNode(depth)` | trail.slice(0, depth+1), center 복원 |
| `startChainExploration(sector, symbol)` | trail 리셋 → 새 session |
| `initializeFocusExploration(sector, symbol)` | ?focus= 딥링크 전용 원자적 초기화 |
| `reset()` | 전체 초기화 |

## 그래프 캔버스 디자인

### 노드 색상 (시드 타입별)

| 시드 타입 | 배경 | 보더 |
|----------|------|------|
| price | #FCEBEB | #E24B4A |
| volume | #E1F5EE | #1D9E75 |
| relation | #E6F1FB | #378ADD |
| comention | #F3E8FF | #9333EA |

### 엣지 스타일

| 관계 타입 | 색상 | 스타일 |
|----------|------|--------|
| SUPPLIES_TO | #5DCAA5 | 실선, truth_score 비례 굵기 |
| COMPETES_WITH | #F0997B | 실선 |
| PEER_OF | #85B7EB | 점선 (4,3) |
| CO_MENTIONED | #AFA9EC | 점선 (3,3) |
| PRICE_CORRELATED | #D3D1C7 | 점선 (3,3) |

### 데이터 소스 분기

| 상태 | 데이터 | 렌더 |
|------|--------|------|
| selectedSector && !centerSymbol | useSectorGraph | overview graph |
| centerSymbol | useNeighbors | center + 이웃 |

## 네비게이션

```
[대시보드] [포트폴리오] [Chain Sight*] [Thesis Control] [Market Pulse] [뉴스] [스크리너]
```
