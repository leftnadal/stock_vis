# Chain Sight 프론트엔드 설계 v2

> **작성일**: 2026-04-04
> **기반**: cs_51~54 원안 + UI/UX 에이전트 검토 + 투자 도메인 검토 + 정합성 리뷰
> **목표**: 전문 투자자도 이용할 수 있는 수준의 그래프 탐색 경험

---

## 0. 원안 대비 변경 요약

| 항목 | 원안 (cs_51~54) | v2 변경 | 이유 |
|------|----------------|---------|------|
| 메인 뷰 | 종목 상세 탭 내 인터랙티브 그래프 | **전용 워크스페이스 `/chainsight/[symbol]`** | 탭 공간 제한 → 전문가용 넓은 화면 필요 |
| 종목 상세 탭 | 미니 그래프 + 전체 보기 링크 | **미니 그래프(정적) + 연결 종목 태그 + CTA** | 유지 (역할 축소) |
| 엣지 색상 | confirmed/probable 2색 | **관계 타입별 6색 + 스타일 차등** | 관계 종류가 투자 판단 핵심 |
| 모바일 | 그래프 필수 | **데스크톱 우선, 모바일=카드 리스트 기본** | Data-Heavy SaaS 방향성 |
| Strength dots | ●●● 시각화 | **상위 ticker + "+N" 텍스트** | 직관성 |
| Chain Trace 진입 | from/to 수동 입력 | **그래프 노드 탭 → "경로 찾기" 연동** | 진입 장벽 |
| (신규) CTA | 없음 | **가설 생성 / Watchlist 추가 / Validation 이동** | 액션 연결 부재 해결 |
| (신규) 프로 기능 | 없음 | **Centrality 메트릭, 필터 패널, 멀티 depth** | 전문 투자자 요구 |

---

## 1. 라우팅 구조

```
기존 라우트 (19개) + 신규 1개:

/chainsight/[symbol]        ← 신규 (Chain Sight 전용 워크스페이스)

진입 경로:
  1. 종목 상세 Chain Sight 탭 → "전체 탐색" 버튼
  2. EOD 대시보드 chain_sight_cta → 직접 딥링크
  3. 사이드바/헤더 메뉴 "Chain Sight" 항목
  4. URL 직접 접근: /chainsight/AAPL
  5. Screener 결과 → 종목 클릭 → Chain Sight 이동
```

SCREEN_DATA_STRUCTURE.md에 `/chainsight/[symbol]` 라우트 추가 필요.

---

## 2. 전용 워크스페이스 레이아웃

### 데스크톱 (≥1280px) — 3-panel 분할

```
┌──────────────────────────────────────────────────────────────────────┐
│ ← AAPL Apple Inc.    Chain Sight    [Depth 1▾] [필터 ⚙] [저장 ☆]  │
├────────────┬─────────────────────────────────┬───────────────────────┤
│            │                                 │                       │
│  좌측 패널  │    그래프 캔버스 (메인)          │  우측 패널             │
│  240px     │    flex-1                       │  320px                │
│            │                                 │                       │
│  ┌────────┐│          ◯──PEER──●──CUST──◯   │  ┌─────────────────┐ │
│  │AI Guide││               │                │  │ 선택된 노드      │ │
│  │        ││          ◯────┼────◯           │  │ TSMC             │ │
│  │경쟁사 8 ││               │                │  │ 관계: CUSTOMER_OF│ │
│  │공급망 3 ││              ◉ AAPL            │  │ confidence: high │ │
│  │테마  2 ││               │                │  │                  │ │
│  │동시출현││          ◯────┼────◯           │  │ [가설 생성]      │ │
│  │        ││                                 │  │ [Watchlist 추가] │ │
│  └────────┘│                                 │  │ [Validation 보기]│ │
│            │                                 │  │ [여기서 탐색]    │ │
│  ┌────────┐│                                 │  └─────────────────┘ │
│  │Chain   ││                                 │                       │
│  │Trace   ││                                 │  ┌─────────────────┐ │
│  │        ││                                 │  │ 프로파일 요약    │ │
│  │From:   ││                                 │  │ GrowthStage:    │ │
│  │[AAPL]  ││                                 │  │  mature         │ │
│  │To:     ││                                 │  │ CapitalDNA:     │ │
│  │[     ] ││                                 │  │  balanced       │ │
│  │[찾기]  ││                                 │  │ Insider: neutral│ │
│  └────────┘│                                 │  │ Rate Sens: med  │ │
│            │                                 │  └─────────────────┘ │
│  ┌────────┐│                                 │                       │
│  │범례    ││  ──── PEER_OF (경쟁)            │                       │
│  │        ││  ━━━━ CUSTOMER_OF (공급망)       │                       │
│  │        ││  ╌╌╌╌ CO_MENTIONED (뉴스)       │                       │
│  └────────┘│  ····  HAS_THEME (테마)         │                       │
├────────────┴─────────────────────────────────┴───────────────────────┤
│ 하단 바: 노드 532 | 엣지 1,247 | 현재 depth 1 | 마지막 동기화 2h전  │
└──────────────────────────────────────────────────────────────────────┘
```

### 태블릿 (768~1279px)

- 좌측 패널 → 접기/펼치기 토글 (기본 접힘)
- 우측 패널 → 노드 선택 시 바텀 시트로 전환

### 모바일 (<768px)

```
┌─────────────────────────────────┐
│ ← AAPL Chain Sight  [AI ▼] [⚙] │
├─────────────────────────────────┤
│ [경쟁사] [공급망] [테마] [전체]  │  ← 탭 바 (카테고리)
├─────────────────────────────────┤
│                                 │
│  1. AMD   경쟁사   +2.3%        │  ← 카드 리스트 (기본)
│     PER 12 vs AAPL PER 29       │
│     [가설 생성] [상세]           │
│  ─────────────────────────────  │
│  2. MSFT  경쟁사   -0.4%        │
│     PER 33 vs AAPL PER 29       │
│     ...                         │
├─────────────────────────────────┤
│        [✨ 그래프로 보기]        │  ← 풀스크린 오버레이 진입
└─────────────────────────────────┘
```

모바일 그래프 오버레이:
- 풀스크린 Canvas (viewport 100%)
- 핀치 줌 전용 (한 손가락 = 노드 탭)
- X 버튼으로 카드 뷰 복귀

---

## 3. 관계 타입별 시각 체계

### 엣지 색상 + 스타일

```
비즈니스 관계 (실선, 굵음 3px)
  SUPPLIES_TO / CUSTOMER_OF   → #F97316 (오렌지)     — "공급망"
  COMPETES_WITH               → #EF4444 (빨강)       — "경쟁"

구조적 관계 (실선, 보통 2px)
  PEER_OF                     → #3B82F6 (파랑)       — "경쟁사"
  BELONGS_TO_INDUSTRY         → #6B7280 (회색, 1px)  — "같은 산업"

시장 신호 관계 (점선, 2px)
  CO_MENTIONED                → #A855F7 (보라)       — "뉴스 동시출현"
  HAS_THEME                   → #14B8A6 (틸)         — "테마"
```

### 노드 시각 체계

```
크기: 3단계
  중심 노드:     r=24    (고정)
  1-depth 이웃:  r=12~20 (pagerank 비례)
  2-depth 이웃:  r=8~12  (pagerank 비례)

색상: 섹터별
  Technology      → #3B82F6
  Healthcare      → #10B981
  Financials      → #F59E0B
  Energy          → #EF4444
  Industrials     → #8B5CF6
  Consumer Disc.  → #EC4899
  Consumer Staples→ #84CC16
  기타            → #6B7280

테두리: 프로파일 신호
  InsiderSignal strong_buy/buy  → 테두리 초록 2px
  InsiderSignal strong_sell/sell→ 테두리 빨강 2px
  기본                          → 테두리 없음

라벨: ticker (항상 표시) + company_name (hover/select 시)
```

---

## 4. 컴포넌트 구조

```
frontend/
├── app/chainsight/[symbol]/page.tsx        ← 전용 워크스페이스 (신규)
├── components/chainsight/
│   ├── GraphCanvas.tsx                     ← ForceGraph2D (dynamic import)
│   ├── GraphControls.tsx                   ← depth, 관계 필터, 리셋
│   ├── NodeDetailPanel.tsx                 ← 우측 패널 (선택 노드 상세 + CTA)
│   ├── AIGuidePanel.tsx                    ← 좌측 패널 (카테고리 + Trace)
│   ├── CategoryCard.tsx                    ← AI Guide 카테고리 카드
│   ├── TracePanel.tsx                      ← Chain Trace (좌측 패널 하단)
│   ├── TracePathView.tsx                   ← Trace 결과 경로 표시
│   ├── RelationLegend.tsx                  ← 관계 타입 범례
│   ├── GraphMiniView.tsx                   ← 종목 상세 탭용 미니 그래프
│   ├── MobileCardList.tsx                  ← 모바일용 카드 리스트
│   └── FilterPanel.tsx                     ← 프로 필터 (관계 타입, confidence, 섹터)
├── hooks/
│   └── useChainsight.ts                    ← API 호출 (graph, suggestions, trace)
├── services/
│   └── chainsightService.ts               ← API 클라이언트
└── types/
    └── chainsight.ts                       ← 타입 정의
```

---

## 5. CTA (Call to Action) 체계

리뷰에서 지적된 "액션 연결 부재" 해결.

### NodeDetailPanel CTA 버튼

```
노드 선택 시 우측 패널 상단:

┌─────────────────────────────┐
│ TSMC                   ↗️   │  ← 외부 링크 (종목 상세)
│ Taiwan Semiconductor        │
│ 관계: CUSTOMER_OF (공급망)  │
│ confidence: high            │
├─────────────────────────────┤
│ [📋 가설 생성]              │  ← /thesis/new?symbol=TSM&from=AAPL
│ [⭐ Watchlist 추가]         │  ← POST /api/v1/users/watchlist/
│ [📊 Validation 보기]        │  ← /stocks/TSM?tab=validation
│ [🔍 여기서 탐색 시작]       │  ← /chainsight/TSM (중심 전환)
│ [🔗 경로 찾기]              │  ← Trace 패널 to 자동 채움
└─────────────────────────────┘
```

### Trace 완성 시 CTA

```
경로 완성 후 하단:

AAPL → MSFT → TSLA (2단계)

[이 경로 기반 가설 생성]
  → /thesis/new?trace=AAPL,MSFT,TSLA&type=chain_reaction
```

---

## 6. 프로 투자자 기능 (Advanced)

### 6-1. 필터 패널

```
[⚙ 필터] 클릭 시 드롭다운:

관계 타입:
  ☑ PEER_OF         ☑ CUSTOMER_OF
  ☑ CO_MENTIONED    ☐ HAS_THEME
  ☐ BELONGS_TO      ☑ COMPETES_WITH

Confidence:
  ☑ high  ☑ medium  ☐ low

섹터:
  ☑ Technology  ☑ Healthcare  ☐ 전체 선택

Depth: [1] [2] [3]

[적용] [초기화]
```

### 6-2. 노드 메트릭 오버레이 (토글)

```
[오버레이 ▾] 드롭다운:

  ○ 기본 (섹터 색상)
  ● PER 히트맵 (파랑=저PER, 빨강=고PER)
  ○ 시총 크기 (노드 크기 = market_cap)
  ○ Centrality (PageRank 비례 크기)
  ○ 커뮤니티 (Louvain 커뮤니티별 색상)
```

전문 투자자용: PER 히트맵 + Centrality를 겹치면
"같은 경쟁사 내에서 저PER + 높은 중심성 = 저평가 허브" 발견 가능.

### 6-3. 노드 비교 모드

```
두 노드를 Ctrl+Click으로 선택 시:

┌─────────────────────────────────────┐
│ 비교: NVDA vs AMD                   │
├──────────────┬──────────────────────┤
│              │  NVDA    │   AMD     │
│ PER          │  28.5    │   12.1    │
│ ROE          │  31.1%   │   22.4%   │
│ Growth Stage │ accelerating│ mature  │
│ Capital DNA  │ heavy_inv│ balanced  │
│ Insider      │ neutral  │ buy      │
│ Rate Sens.   │ low      │ medium   │
│ Peers 수     │ 12       │   8      │
│ Supply Chain │ TSMC,SKH │ TSMC,GF  │
├──────────────┴──────────────────────┤
│ [두 종목 Trace] [병렬 Validation]  │
└─────────────────────────────────────┘
```

---

## 7. 종목 상세 탭 — 미니 뷰 (CS-5-4)

종목 상세 `chain-sight` 탭 내용 (현재 "재구축 중" 플레이스홀더 교체):

```
┌──────────────────────────────────────────────────┐
│ Chain Sight 관계 탐색       [전체 탐색 →]         │
├──────────────────────────────────────────────────┤
│                                                  │
│  [미니 그래프 — 360px 높이, 정적 스냅샷]         │
│  Depth 1, 인터랙션 없음 (cooldown 후 freeze)     │
│  노드 탭 → 해당 종목 상세 이동                    │
│                                                  │
├──────────────────────────────────────────────────┤
│ 연결 종목 (12)                                   │
│ [AMD 경쟁사] [TSMC 공급망] [MSFT 동시출현] +9   │
├──────────────────────────────────────────────────┤
│ 프로파일                                         │
│ GrowthStage: mature | CapitalDNA: balanced       │
│ Rate: medium | Forex: high | Insider: neutral    │
└──────────────────────────────────────────────────┘
```

---

## 8. 데이터 흐름 (API → 컴포넌트)

```
useChainsight.ts
  │
  ├── useGraphData(symbol, depth)
  │     → GET /api/v1/chainsight/{symbol}/graph/?depth=1
  │     → { center, nodes[], edges[], meta }
  │     → GraphCanvas.tsx
  │
  ├── useSuggestions(symbol)
  │     → GET /api/v1/chainsight/{symbol}/suggestions/
  │     → { categories[] }
  │     → AIGuidePanel.tsx → CategoryCard.tsx
  │
  └── useTrace(from, to)
        → GET /api/v1/chainsight/trace/?from=AAPL&to=TSLA
        → { path_nodes[], path_edges[], found, path_length }
        → TracePathView.tsx

추가 필요 API (프로 기능용):
  - GET /api/v1/chainsight/{symbol}/profile/
    → { growth_stage, capital_dna, sensitivity, insider, business_model }
    → NodeDetailPanel 프로파일 요약
```

---

## 9. 라이브러리 선정

```
react-force-graph-2d (확정)
  - 이유: 현재 규모 (화면당 20~50노드)에 적합, 빠른 구현
  - 조건: dynamic import + ssr: false
  - 대안 전환 시점: 노드 200+ 시 Cytoscape.js 고려

설치:
  cd frontend && npm install react-force-graph-2d

SSR 방어:
  const ForceGraph2D = dynamic(
    () => import('react-force-graph-2d'),
    { ssr: false }
  )

시뮬레이션 안정화:
  cooldownTicks={80}
  onEngineStop={() => ref.current?.zoomToFit(400)}
```

---

## 10. 구현 순서

| 순서 | 항목 | 산출물 | 예상 |
|------|------|--------|------|
| **1** | 타입 + 서비스 + 훅 | `types/chainsight.ts`, `services/chainsightService.ts`, `hooks/useChainsight.ts` | 2시간 |
| **2** | 전용 페이지 + GraphCanvas | `app/chainsight/[symbol]/page.tsx`, `GraphCanvas.tsx` | 4시간 |
| **3** | 관계 타입 시각 체계 + 범례 | 노드/엣지 렌더링 + `RelationLegend.tsx` | 2시간 |
| **4** | NodeDetailPanel + CTA | 우측 패널 + 가설/Watchlist/Validation 연결 | 3시간 |
| **5** | AIGuidePanel + CategoryCard | 좌측 패널 + 카테고리 필터링 | 2시간 |
| **6** | TracePanel + TracePathView | Chain Trace + 그래프 하이라이트 | 3시간 |
| **7** | 종목 상세 미니 뷰 | `GraphMiniView.tsx` + 탭 교체 | 2시간 |
| **8** | 프로 기능 (필터, 오버레이, 비교) | `FilterPanel.tsx` + 오버레이 토글 | 3시간 |
| **9** | 모바일 카드 리스트 | `MobileCardList.tsx` + 반응형 | 2시간 |

---

## 11. 반영하지 않은 리뷰 의견 (사유)

| 의견 | 미반영 사유 |
|------|-----------|
| Screener ChainSightPanel 이름 변경 | 기존 컴포넌트 안정성 우선. 역할 구분은 디렉토리 (`screener/` vs `chainsight/`)로 충분 |
| 실시간 CO_MENTIONED 업데이트 | Celery Beat 일 1회로 충분. 실시간은 과도한 복잡성 |
| 섹터 전체 보기 (`/chainsight/sector/Technology`) | API 미존재 + 현재 스코프 밖. Future Path로 예약만 |
| 카드에 미니 수익률 차트 | 컴포넌트 복잡도 증가. PER/ROE 숫자 비교로 충분 |

---

## 12. 성공 기준

```
□ /chainsight/AAPL 접속 → 3초 이내 Depth 1 그래프 렌더링
□ 관계 타입별 색상 + 범례 표시
□ 노드 클릭 → 우측 패널 + CTA 4개 동작
□ AI Guide 카테고리 선택 → 그래프 필터링
□ Chain Trace → 경로 하이라이트 + 단계별 설명
□ 종목 상세 Chain Sight 탭 = 미니 그래프 + "전체 탐색" 링크
□ 모바일 카드 리스트 기본 + 그래프 오버레이
□ 프로 기능: 필터 패널 + PER 오버레이 + 노드 비교
□ CTA: 가설 생성 / Watchlist / Validation 연동
★ M5 달성: "전문 투자자가 사용 가능한 Chain Sight MVP"
```

**END OF DOCUMENT**
