# CS-5-5: MarketView 3영역 레이아웃

> **작업 번호**: CS-5-5
> **목표**: Chain Sight의 메인 진입점이 되는 MarketView 화면 구축. 섹터 버튼바 + 그래프 캔버스 + 탐색 트레일의 3영역 반응형 레이아웃.
> **예상 소요**: 3~5일
> **선행 조건**:
> - CS-4-1 (그래프 탐색 API)
> - CS-4-4 (Seed Node heat_score 배치)
> - CS-5-1 (GraphView 컴포넌트)
> **산출물**:
> - `frontend/components/chainsight/MarketView.tsx`
> - `frontend/components/chainsight/SectorButtonBar.tsx`
> - `frontend/components/chainsight/ExplorationTrail.tsx`
> - `frontend/app/chainsight/page.tsx` (라우팅)
> - `frontend/hooks/useMarketView.ts`

---

## 배경

**Chain Sight 진입점 부재 문제**: Phase 4 API가 완성되어도 사용자가 "어디서부터 탐색을 시작할지" 모른다. 종목 상세 페이지에서 들어오는 딥링크(`/chainsight?focus=NVDA`)만으로는 부족하다.

**해결 방향**: MarketView는 섹터 선택 → 시드 노드 3개 강조 → 그래프 캔버스에서 자유 탐색 → 탐색 트레일에서 경로 확인/Watch의 흐름을 제공한다.

**v1.4 변경 (v1.2 → v1.4)**:
- 원래 PM_DESIGN.md v1.2는 4영역 레이아웃이었음 (①섹터바 / ②그래프 / ③트레일 / ④체인 스토리 피드)
- **v1.4는 3영역으로 축소**: 체인 스토리 피드(④)는 v1.3 이후로 미룸
- 이유: Feed API (CS-4-11)가 아직 없음. Feed를 만들려면 Why Now/Next Best Chain/Hidden Hub/Ripple 추천 엔진이 필요한데 MVP 범위를 초과함.
- 체인 스토리 피드 자리는 CS-5-2 AI 가이드 카드(SuggestionCards)로 대체 가능하나, 본 작업에서는 생략하고 CS-5-2가 별도 컴포넌트로 존재.

---

## 화면 구조 (3영역)

### 데스크탑 (≥1024px)

```
┌─────────────────────────────────────────────────────────────────┐
│  ① 섹터 버튼 바                                                  │
│  [Tech +1.2%] [Healthcare -0.3%] [Financial +0.5%] ...          │
│  (증감률 기반 그라데이션: 초록 ↔ 빨강)                             │
├──────────────┬──────────────────────────────────┬───────────────┤
│              │                                  │               │
│ ③ 탐색 트레일│  ② 그래프 캔버스                 │  노드 상세     │
│  (세로 스택) │                                  │   패널 (우측) │
│              │  섹터 선택 시:                   │               │
│  NVDA →      │  - market cap 상위 20개 노드     │  (CS-5-1에서  │
│  TSM →       │  - 그중 heat_score 상위 3개는    │   구현된      │
│  ASML →      │    bounce 애니메이션 (시드)      │   NodeDetail  │
│  AMAT →      │                                  │   Panel 사용) │
│  ...         │  노드 클릭:                      │               │
│              │  - 중심 이동 + 1-hop 확장        │               │
│  [📌 Watch]  │  - 탐색 트레일에 추가            │               │
│              │                                  │               │
└──────────────┴──────────────────────────────────┴───────────────┘
```

### 태블릿 (768~1024px)

```
┌─────────────────────────────────────────┐
│ ① 섹터 버튼 바 (가로 스크롤)             │
├─────────────────────────────────────────┤
│                                         │
│ ② 그래프 캔버스 (전체 너비)              │
│                                         │
│                                         │
├─────────────────────────────────────────┤
│ ③ 탐색 트레일 (가로 스크롤)  [Watch]     │
└─────────────────────────────────────────┘

노드 클릭 시 상세 패널은 bottom sheet로 올라옴
```

### 모바일 (<768px)

```
┌─────────────────────┐
│ ① 섹터바 (가로 스크롤)│
├─────────────────────┤
│                     │
│ ② 그래프 (풀스크린) │
│                     │
├─────────────────────┤
│ ③ 트레일 [Watch]    │
└─────────────────────┘
 [하단 고정 네비게이션]

노드 상세는 full-screen modal
터치 타겟 44px+
```

---

## 구현

### 1. 디렉토리 구조

```
frontend/
├── app/
│   └── chainsight/
│       └── page.tsx                     ← 라우팅 진입점
├── components/
│   └── chainsight/
│       ├── MarketView.tsx               ← 3영역 컨테이너 (본 작업)
│       ├── SectorButtonBar.tsx          ← ① 섹터 버튼 바
│       ├── ExplorationTrail.tsx         ← ③ 탐색 트레일
│       ├── GraphView.tsx                ← ② (CS-5-1에서 구현)
│       ├── NodeDetailPanel.tsx          ← (CS-5-1에서 구현)
│       └── WatchButton.tsx              ← (CS-7-1에서 구현, 본 작업에서는 placeholder)
└── hooks/
    ├── useMarketView.ts                 ← 상태 관리 (본 작업)
    └── useSectorList.ts                 ← 섹터 목록 + 증감률 (본 작업)
```

### 2. 타입 정의

```typescript
// frontend/types/chainsight.ts

export interface Sector {
  name: string;                // "Technology"
  stockCount: number;
  dailyChangePercent: number;  // -3.2 ~ +3.2 (%)
}

export interface GraphNode {
  ticker: string;
  name: string;
  sector: string;
  industry: string;
  marketCap: number;
  heatScore?: number;          // CS-4-4 결과
  pagerankScore?: number;      // CS-3-3 결과
  communityId?: number;
  isSeed?: boolean;            // heatScore 기반 프론트엔드 결정
  dailyChangePercent?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  relationType: string;        // PEER_OF, SUPPLIES_TO, COMPETES_WITH, HAS_THEME, CO_MENTIONED, PRICE_CORRELATED
  truthScore?: number;
  relationStatus?: 'confirmed' | 'probable' | 'weak' | 'hidden' | 'stale';
  relationCategory?: 'truth' | 'market';
  basisSummary?: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface TrailNode {
  ticker: string;
  name: string;
  timestamp: number;           // 추가된 시각 (Date.now())
}
```

### 3. useMarketView 훅

```typescript
// frontend/hooks/useMarketView.ts

import { useState, useCallback, useEffect } from 'react';
import { GraphData, GraphNode, TrailNode } from '@/types/chainsight';

const MARKET_RELATION_TOGGLE_KEY = 'chainsight_market_relation_toggle';

export function useMarketView(initialSector?: string, initialFocus?: string) {
  const [activeSector, setActiveSector] = useState<string | null>(initialSector ?? null);
  const [focusTicker, setFocusTicker] = useState<string | null>(initialFocus ?? null);
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], edges: [] });
  const [trail, setTrail] = useState<TrailNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [showMarketRelations, setShowMarketRelations] = useState(false);

  // 섹터 선택 시 market cap 상위 + heat_score 시드 로드
  useEffect(() => {
    if (!activeSector) return;
    setLoading(true);

    fetch(`/api/chainsight/sectors/${activeSector}/overview/?limit=20`)
      .then(res => res.json())
      .then((data: GraphData) => {
        // heat_score 상위 3개를 isSeed=true로 마킹
        const sortedByHeat = [...data.nodes]
          .filter(n => n.heatScore !== undefined)
          .sort((a, b) => (b.heatScore ?? 0) - (a.heatScore ?? 0))
          .slice(0, 3)
          .map(n => n.ticker);

        const enriched = {
          ...data,
          nodes: data.nodes.map(n => ({
            ...n,
            isSeed: sortedByHeat.includes(n.ticker),
          })),
        };
        setGraphData(enriched);
        setTrail([]);  // 섹터 전환 시 trail 초기화
      })
      .finally(() => setLoading(false));
  }, [activeSector]);

  // 노드 클릭: 중심 이동 + 1-hop 확장
  const navigateToNode = useCallback((ticker: string, name: string) => {
    setFocusTicker(ticker);
    setLoading(true);

    const relTypes = showMarketRelations
      ? ['PEER_OF', 'SUPPLIES_TO', 'COMPETES_WITH', 'HAS_THEME', 'CO_MENTIONED', 'PRICE_CORRELATED']
      : ['PEER_OF', 'SUPPLIES_TO', 'COMPETES_WITH', 'HAS_THEME'];

    fetch(`/api/stocks/${ticker}/chainsight/graph/?depth=1&rel_types=${relTypes.join(',')}`)
      .then(res => res.json())
      .then((data: GraphData) => {
        setGraphData(data);
        setTrail(prev => [...prev, { ticker, name, timestamp: Date.now() }]);
      })
      .finally(() => setLoading(false));
  }, [showMarketRelations]);

  // 트레일 undo
  const undoToTrailNode = useCallback((ticker: string) => {
    const idx = trail.findIndex(t => t.ticker === ticker);
    if (idx === -1) return;
    setTrail(prev => prev.slice(0, idx + 1));
    navigateToNode(ticker, trail[idx].name);
  }, [trail, navigateToNode]);

  return {
    activeSector,
    setActiveSector,
    focusTicker,
    graphData,
    trail,
    loading,
    showMarketRelations,
    setShowMarketRelations,
    navigateToNode,
    undoToTrailNode,
  };
}
```

### 4. SectorButtonBar 컴포넌트

```typescript
// frontend/components/chainsight/SectorButtonBar.tsx

import { Sector } from '@/types/chainsight';

interface Props {
  sectors: Sector[];
  activeSector: string | null;
  onSelect: (name: string) => void;
}

function getColorForChange(change: number): string {
  // -3% ~ +3% 범위를 초록/빨강 그라데이션
  const clamped = Math.max(-3, Math.min(3, change));
  if (clamped > 0) {
    const intensity = clamped / 3;  // 0 ~ 1
    return `rgba(34, 197, 94, ${0.2 + intensity * 0.6})`;  // green-500
  } else {
    const intensity = Math.abs(clamped) / 3;
    return `rgba(239, 68, 68, ${0.2 + intensity * 0.6})`;  // red-500
  }
}

export function SectorButtonBar({ sectors, activeSector, onSelect }: Props) {
  return (
    <div className="overflow-x-auto whitespace-nowrap border-b border-gray-200 bg-white px-4 py-3">
      <div className="inline-flex gap-2">
        {sectors.map(sector => {
          const isActive = activeSector === sector.name;
          const bg = getColorForChange(sector.dailyChangePercent);
          const sign = sector.dailyChangePercent >= 0 ? '+' : '';

          return (
            <button
              key={sector.name}
              onClick={() => onSelect(sector.name)}
              style={{ backgroundColor: isActive ? bg : 'transparent' }}
              className={`
                min-h-[44px] px-4 py-2 rounded-full text-sm font-medium
                border transition-all
                ${isActive
                  ? 'border-gray-800 text-gray-900'
                  : 'border-gray-300 text-gray-700 hover:border-gray-400'}
              `}
            >
              {sector.name}{' '}
              <span className={sector.dailyChangePercent >= 0 ? 'text-green-700' : 'text-red-700'}>
                {sign}{sector.dailyChangePercent.toFixed(1)}%
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
```

### 5. ExplorationTrail 컴포넌트

```typescript
// frontend/components/chainsight/ExplorationTrail.tsx

import { TrailNode } from '@/types/chainsight';
import { Pin } from 'lucide-react';

interface Props {
  trail: TrailNode[];
  onUndo: (ticker: string) => void;
  onWatch: () => void;
}

export function ExplorationTrail({ trail, onUndo, onWatch }: Props) {
  if (trail.length === 0) {
    return (
      <div className="border-t border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-500">
        노드를 탭하면 탐색 경로가 여기에 추가됩니다.
      </div>
    );
  }

  return (
    <div className="border-t border-gray-200 bg-gray-50 px-4 py-3 flex items-center gap-2">
      <div className="overflow-x-auto flex-1">
        <div className="inline-flex items-center gap-2 whitespace-nowrap">
          {trail.map((node, idx) => (
            <div key={`${node.ticker}-${node.timestamp}`} className="inline-flex items-center gap-2">
              <button
                onClick={() => onUndo(node.ticker)}
                className="min-h-[44px] px-3 py-1.5 rounded-full bg-white border border-gray-300
                           text-sm font-medium hover:border-gray-500"
                title={`${node.ticker}로 되돌리기`}
              >
                {node.ticker}
              </button>
              {idx < trail.length - 1 && <span className="text-gray-400">→</span>}
            </div>
          ))}
        </div>
      </div>

      {trail.length >= 2 && (
        <button
          onClick={onWatch}
          className="min-h-[44px] px-4 py-2 rounded-full bg-blue-600 text-white text-sm font-medium
                     hover:bg-blue-700 flex items-center gap-1 flex-shrink-0"
        >
          <Pin size={16} />
          Watch
        </button>
      )}
    </div>
  );
}
```

### 6. MarketView 컨테이너

```typescript
// frontend/components/chainsight/MarketView.tsx

'use client';

import { useSearchParams } from 'next/navigation';
import { useMarketView } from '@/hooks/useMarketView';
import { useSectorList } from '@/hooks/useSectorList';
import { SectorButtonBar } from './SectorButtonBar';
import { ExplorationTrail } from './ExplorationTrail';
import { GraphView } from './GraphView';
import { NodeDetailPanel } from './NodeDetailPanel';

export function MarketView() {
  const searchParams = useSearchParams();
  const initialFocus = searchParams.get('focus') ?? undefined;

  const { sectors, loading: sectorsLoading } = useSectorList();
  const {
    activeSector,
    setActiveSector,
    focusTicker,
    graphData,
    trail,
    loading,
    showMarketRelations,
    setShowMarketRelations,
    navigateToNode,
    undoToTrailNode,
  } = useMarketView(undefined, initialFocus);

  const handleWatch = () => {
    // CS-7-1에서 구현. 일단 placeholder.
    alert(`Watchlist에 경로 저장: ${trail.map(t => t.ticker).join(' → ')}`);
  };

  return (
    <div className="flex flex-col h-screen">
      {/* ① 섹터 버튼 바 */}
      {sectorsLoading ? (
        <div className="px-4 py-3 text-gray-400">섹터 로딩 중...</div>
      ) : (
        <SectorButtonBar
          sectors={sectors}
          activeSector={activeSector}
          onSelect={setActiveSector}
        />
      )}

      {/* ② 그래프 캔버스 + 노드 상세 */}
      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 relative">
          <GraphView
            data={graphData}
            centerTicker={focusTicker}
            onNodeClick={(node) => navigateToNode(node.ticker, node.name)}
            loading={loading}
            showMarketRelations={showMarketRelations}
          />

          {/* Market 관계 토글 (v1.4 성능 가드레일 — 기본 OFF) */}
          <div className="absolute top-3 right-3">
            <label className="inline-flex items-center gap-2 bg-white rounded-full px-3 py-2 shadow-sm border border-gray-200 cursor-pointer">
              <input
                type="checkbox"
                checked={showMarketRelations}
                onChange={(e) => setShowMarketRelations(e.target.checked)}
                className="w-4 h-4"
              />
              <span className="text-sm">Market 관계 표시</span>
            </label>
          </div>
        </div>

        {/* 데스크탑에서만 우측 상세 패널 */}
        <div className="hidden lg:block w-80 border-l border-gray-200 overflow-y-auto">
          {focusTicker ? (
            <NodeDetailPanel ticker={focusTicker} />
          ) : (
            <div className="p-4 text-sm text-gray-500">
              노드를 선택하면 상세 정보가 표시됩니다.
            </div>
          )}
        </div>
      </div>

      {/* ③ 탐색 트레일 */}
      <ExplorationTrail
        trail={trail}
        onUndo={undoToTrailNode}
        onWatch={handleWatch}
      />
    </div>
  );
}
```

### 7. 라우팅 진입점

```typescript
// frontend/app/chainsight/page.tsx

import { MarketView } from '@/components/chainsight/MarketView';

export default function ChainSightPage() {
  return <MarketView />;
}
```

종목 상세 페이지의 Chain Sight 탭은 `/chainsight?focus=NVDA`로 딥링크한다.

---

## 백엔드 연계 (CS-4-1 확장 필요)

MarketView는 `/api/chainsight/sectors/{sector_name}/overview/?limit=20` 엔드포인트가 필요한데, 이는 CS-4-1의 `GET /api/stocks/{symbol}/chainsight/graph/`와는 다른 섹터 단위 조회다.

### 선택지

**A. CS-4-1에 섹터 overview 엔드포인트 추가 (본 작업에서 백엔드 변경)**

```python
# chainsight/views/graph_views.py 에 추가
@api_view(['GET'])
def sector_overview(request, sector_name):
    limit = int(request.GET.get('limit', 20))
    # Neo4j: MATCH (s:Stock {sector: $sector_name})
    #        RETURN s ORDER BY s.market_cap DESC LIMIT $limit
    # 응답에 heat_score 포함
```

URL: `/api/chainsight/sectors/<str:sector_name>/overview/`

**B. 별도 CS-4-5로 분리**

본 작업은 프론트엔드만 하고, 백엔드는 CS-4-5로 분리.

**→ A 권장**. CS-4-1이 이미 같은 Neo4j repository를 쓰고 있고, 새 작업 번호를 만들 만한 분량이 아님.

### 섹터 목록 + 증감률 API (useSectorList용)

```
GET /api/chainsight/sectors/
응답: [
  { name: "Technology", stockCount: 80, dailyChangePercent: 1.2 },
  ...
]
```

dailyChangePercent는 섹터 내 종목들의 시총 가중평균 수익률. 계산 소스는 stocks/DailyPrice.

---

## 성능 가드레일 (PM_DESIGN.md 섹션 5-5 준수)

| 항목 | 제한 |
|------|------|
| 초기 렌더링 노드 수 | 최대 50개 (백엔드 limit 파라미터로 강제) |
| 그래프 depth | 최대 2 (hop 파라미터 기본 1, 최대 2) |
| Neo4j 쿼리 LIMIT | 100 paths |
| 엣지 표시 기준 | confirmed 또는 probable (백엔드에서 필터) |
| Market 관계 표시 | 토글, 기본 OFF (relTypes 파라미터 제어) |

---

## 완료 기준

```
□ /chainsight 라우트 진입 시 섹터 버튼 바 표시
□ 섹터 선택 → market cap 상위 20개 노드 로드
□ heat_score 상위 3개 노드에 bounce 애니메이션 (CS-5-1 GraphView에서 구현된 isSeed prop)
□ 노드 클릭 → 중심 이동 + 1-hop 확장 + 탐색 트레일 추가
□ 탐색 트레일 노드 탭 → 해당 지점으로 undo
□ Watch 버튼: 2개 이상 노드 시 활성화 (실제 동작은 CS-7-1)
□ Market 관계 토글 기본 OFF, 켜면 CO_MENTIONED/PRICE_CORRELATED 표시
□ 반응형 3개 환경 확인 (Mobile/Tablet/Desktop)
□ 종목 상세에서 /chainsight?focus=NVDA 진입 시 해당 노드 중심 로드
□ heat_score가 없는 섹터(전체 null)의 fallback — market cap만으로 표시
```

---

## 주의사항

### 체인 스토리 피드 제외 (v1.4 변경)

PM_DESIGN.md v1.2의 4영역 중 ④ 체인 스토리 피드는 본 작업에서 **제외**. v1.3 이후 CS-4-11 Feed API와 함께 추가 예정. 그 자리는 데스크탑에서 노드 상세 패널이 차지하고, 모바일/태블릿에서는 영역 자체가 없다.

### CS-5-2 (AI 가이드 카드)와의 관계

PM_DESIGN.md의 체인 스토리 피드와 CS-5-2의 SuggestionCards는 다른 것이다:
- CS-5-2 SuggestionCards: 현재 중심 노드 기준 카테고리 탐색 (경쟁사/공급망/섹터)
- Chain Story Feed (v1.3 이후): 시장 전체 기반 추천 피드 (Why Now/Next Best Chain/Hidden Hub)

MarketView에 CS-5-2를 embed할지 여부는 본 작업에서 결정하지 않음. 기본은 MarketView가 그래프 중심, CS-5-2는 종목 상세 페이지 중심으로 분리. 필요 시 후속 PR에서 MarketView 우측 패널에 SuggestionCards를 추가.

### Watch 버튼 UI만 구현 (기능은 CS-7-1)

본 작업에서는 Watch 버튼을 ExplorationTrail에 노출하되, 클릭 시 `alert()` placeholder. 실제 POST /api/chainsight/watchlist/ 호출은 CS-7-1에서 구현. 이렇게 분리하는 이유는 CS-7-1이 Phase 7이라 Phase 6 완료(CS-6-2 Watchlist CRUD API) 이후 가능하기 때문.

### 섹터 전환 시 trail 초기화

섹터가 바뀌면 이전 탐색 경로는 의미가 없으므로 trail을 초기화한다. 다만 사용자가 혼란을 겪을 수 있으므로, 향후 "섹터 전환하시겠어요? 현재 경로는 초기화됩니다" 확인 다이얼로그 추가를 고려. MVP는 단순하게 진행.

### 모바일 제스처 충돌

ForceGraph2D의 핀치 줌과 페이지 스크롤이 충돌할 수 있음. CS-5-1에서 이미 `touch-action: none`으로 그래프 영역만 제스처 격리했는지 확인. 아니면 본 작업에서 보강.

### 초기 렌더링 전 상태

페이지 진입 직후 섹터 미선택 상태에서는 그래프 영역에 "섹터를 선택하세요" 빈 상태 UI 노출. initialFocus(딥링크)가 있으면 그 종목 중심 그래프 로드.

---

→ **다음**: cs_56 (시드 노드 표시) — Phase 5 마지막 작업은 cs_56

**END OF DOCUMENT**
