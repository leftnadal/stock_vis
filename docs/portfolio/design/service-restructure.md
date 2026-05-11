# Stock-Vis 서비스 구조 재설계

## 개요

### 핵심 변경
Thesis Control을 독립 탭에서 해체하여, Dashboard / Chain Sight / Portfolio 세 곳에 자연스럽게 녹여내는 구조로 전환한다.

### 변경 배경
- Thesis Control이 "관제탑"이라는 이미지가 강해 사용자에게 실질적 가치 전달이 어려움
- 실제로는 성격이 다른 세 가지 기능(매크로 시나리오, 종목 가설 수립, 보유 가설 모니터링)을 하나의 탭에 억지로 담고 있었음
- 기존 6단계 플로우가 사용자에게 불필요하게 복잡함
- Node Monitoring 역시 Chain Sight의 자연스러운 연장선이므로 흡수

### 구조 변경 요약

**기존 플로우 (6단계)**
```
Dashboard → Chain Sight → Node Monitoring → 1차 검증 → Thesis Control → 포트폴리오 변화
```

**변경 플로우 (3단계)**
```
Dashboard(매크로) → Chain Sight(발견/검증/가설) → Portfolio(보유/관리/코치)
```

---

## 1. 탭 구조

### 1-1. Dashboard — "세상이 어떻게 움직이나"

시장 전체 흐름 조감 + 매크로 시나리오 모니터링.
기존의 단순 시장 요약에서 **매크로 관제탑**으로 역할 확장.

**핵심 기능**
- 시장 전체 브리핑 (기존 유지)
- Market Breadth Indicators (Tier A/B 지표)
- 매크로 Thesis 시나리오 모니터링

**매크로 Thesis 구성**
- 프리셋 시나리오: 서비스 기본 제공 (콜드스타트용)
  - 예: 금리 인상 사이클, 중국 경기 둔화, AI 인프라 투자 확대, 지정학 리스크 확대
- 커스텀 시나리오: 사용자 직접 생성
  - 예: "미국-이란 전쟁 가능성" → 원유 가격, VIX, 방산 ETF, 금 가격, 해운 운임 등 지표 매핑

**Portfolio 연결**
- 매크로 시나리오 신호 변화 시 → Portfolio Coach가 "당신의 포트폴리오 중 이 시나리오에 민감한 종목은 X, Y, Z" 알림 제공
- 매크로 ↔ 종목 양방향 연결

**Thesis Engine 연동**
- scope: `macro`
- 기존 premise-indicator 매핑 구조 동일 적용
- Market Environment Premise 레이어와 연결

**MVP 범위**
- 프리셋 매크로 시나리오 3~5개 제공
- 커스텀 시나리오는 후속 확장


### 1-2. Chain Sight — "어떤 종목이 왜 흥미로운가"

발견 + 추적(Node Monitoring 흡수) + 종목 레벨 가설 수립.
Chain Sight가 **2차 검증** 역할을 겸한다.

**핵심 기능**
- 관계 그래프 탐색 (기존 Chain Sight 핵심 — 공급망, ETF 동반보유, 비즈니스 연결)
- Node Watching (기존 Node Monitoring 흡수)
- 종목 레벨 Thesis 수립
- 1차 검증 연결 (종목 상세 페이지로의 진입점)

**두 가지 모드**
- Explore 모드: 그래프 자유 탐색
- Watching 모드: 핀 꽂아둔 노드들의 변화 추적. 하이라이트 + 변화 알림

**사용자 동선**
```
그래프 탐색 → 노드 핀 꽂기(watch) → 변화 감지 
→ 종목 클릭 시 1차 검증 확인 (종목 상세 페이지)
→ "여기에 thesis 세울까?" → thesis 수립 (전제 설정, 지표 매핑)
→ 확신 생기면 매수 → Portfolio로 이동
```

**Thesis Engine 연동**
- scope: `stock`, status: `watching`
- Chain Sight 내에서 thesis 생성 시 Thesis Engine에 저장
- 매수 전환 시 status: `watching` → `holding`으로 변경, Portfolio에서 표시

**Neo4j 그래프 + DQS**
- 기존 설계한 Neo4j GDS 알고리즘 (PageRank, Louvain, Betweenness Centrality 등) 그대로 활용
- Data Quality Score는 edge property로 유지


### 1-3. 종목 상세 페이지 — "이 종목 자체가 괜찮은가"

독립 탭이 아닌, 어디서든 접근 가능한 페이지.

**핵심 기능**
- 1차 검증 (34개 지표, 7개 카테고리)
- 기본 정보 (가격, 재무, 섹터)
- Overview 탭 (정적 + 동적 레이어)

**검증 역할 분담**
- 1차 검증 (여기): "이 종목이 재무적으로 건강한가?" — 정적, 종목 단위, 스냅샷
- 2차 검증 (Chain Sight): "이 종목의 관계와 맥락이 투자 근거를 뒷받침하는가?" — 동적, 관계 단위, 흐름

**접근 경로**
- Chain Sight에서 노드 클릭
- Portfolio에서 보유 종목 클릭
- Dashboard에서 언급된 종목 클릭
- 검색


### 1-4. Portfolio — "내 돈이 잘 있나"

보유 관리 + 가설 추적 + Coach + Review.
사용자 락인 효과의 핵심 기능.

**핵심 설계 원칙**
- 초보자: 프리셋 기반 쉬운 진단
- 전문가: 커스터마이징 가능한 심층 분석
- LLM Coach가 이 스펙트럼을 연결

**3-Layer 구조**
- Layer 1 — 현황(What): 보유 종목, 수익률, 비중, 섹터. 기본 뷰에서 항상 표시
- Layer 2 — 근거(Why): 각 포지션의 Thesis 상태. 종목 클릭 시 펼침
  - 예: "AI 인프라 확장 thesis — 건강도 78%, 전제 3개 중 2개 유효, 1개 약화 중"
- Layer 3 — 신호(What's changing): Chain Sight 관계 변화, 뉴스 시그널, 매크로 시나리오 영향

**Thesis Engine 연동**
- scope: `stock`, status: `holding`
- 전제 약화 시 알림 → Coach를 통한 비중 조절 제안
- Dashboard의 매크로 시나리오 변화도 여기로 흘러들어옴

**Coach 기능**
- 대화형 포트폴리오 코치 (LLM 기반)
- 역할 한정: 포트폴리오 **전체의 구조적 균형** 판단
  - O: "AI 인프라 thesis 노출이 60%인데, 리스크 허용 범위를 넘어섰다"
  - X: "NVDA를 팔아라" (개별 종목 매매 판단은 하지 않음)
- 프리셋 기반 해석 → 점진적 개인화 전환
- 과거 판단 기록 기반 패턴 인식

**Coach의 진화 단계**
1. 초기 사용자: 프리셋 기반 일반 진단
2. 2~5회 사용: 프리셋 + 초기 히스토리 기반 조언
3. 장기 사용: 개인화 코치 (프리셋보다 개인화 우선)

**History 기능**
- 날짜별 포트폴리오 스냅샷
- 무엇을 바꿨는지 + 왜 바꿨는지
- 당시 적용 모드/thesis 상태
- 이후 결과 추적
- 의사결정 카드 형태 UI

**Review 기능**
- 월간/분기 복기 리포트
- 반복 패턴 분석 (조기 익절, thesis 중복 과소인식, 하락장 대응 지연 등)
- 프리셋 적합도 변화
- 투자 실력 학습 — 숫자보다 통찰 문장 중심

**Style/프리셋 기능**
- MVP 단계에서는 Portfolio 내 섹션으로 포함
- 프리셋 예: Quality Value, Growth Compounder, Risk Balanced, Dividend, Trend Leader
- 프리셋 vs 개인 실제 성과 비교
- 데이터 축적 후 별도 탭으로 분리 가능

**MVP 탭 구성**
- Portfolio 메인 (현황 + Layer 2/3 펼침)
- Coach (Portfolio 내 진단 카드 + LLM 코멘트, 대화형은 후속)
- Review (History 통합, 이력 + 간단 사후분석)

---

## 2. Thesis Engine 백엔드 설계

### 2-1. 변경 없는 부분
Thesis Control의 수학 엔진은 하나의 백엔드 모듈로 유지. 기존 설계 전부 그대로.

- Layer A: OLS residuals → Kalman filter
- Layer B: Beta-Binomial + z-score weighting (Robust Z/MAD) + decay
- Layer C: Rolling Pearson + MI auxiliary
- Layer D: Weighted average + Noisy-AND + Min
- Layer E: Rule-Based → Change Point detection
- LLM: 주간 관리자 리포트 (보조)

기존 설계 파라미터 유지:
- `MAD_FLOOR=1e-9`
- `effective_window = min(window, len(readings))`
- `asof_date` 스냅샷 키 + `UniqueConstraint(thesis, asof_date)`
- `data_coverage < 0.6` → state-change hold
- `None → 0.0` for inactive premises

### 2-2. 변경되는 부분 — scope 필드 추가

Thesis 모델에 `scope` 필드를 추가하여 프론트엔드 표시 위치를 결정.

```
scope: "macro"                          → Dashboard에서 표시
scope: "stock" + status: "watching"     → Chain Sight에서 표시
scope: "stock" + status: "holding"      → Portfolio에서 표시
```

### 2-3. 데이터 흐름

```
Dashboard (매크로 thesis 표시)
    ↕ scope: macro
Thesis Engine (단일 백엔드 모듈)
    ↕ scope: stock
Chain Sight (thesis 생성, watching)  ←→  Portfolio (thesis 모니터링, holding)
                                            ↑
                                     status 전환: watching → holding (매수 시)
                                     status 전환: holding → closed (매도 시)
```

---

## 3. 기존 시스템과의 관계

### 유지
- 1차 검증 시스템 (v1.4, 34개 지표, 7개 카테고리): 종목 상세 페이지에 그대로
- Chain Sight v1.0/v1.1 로드맵 (Track A/B): 그대로 진행, Node Monitoring 흡수 반영
- EOD Screening: 기존 구조 유지
- News Intelligence Pipeline: 기존 구조 유지
- Thesis Control 수학 모델/DB 스키마: 백엔드 모듈로 유지

### 변경
- Node Monitoring → Chain Sight 내 Watching 모드로 흡수
- Thesis Control 프론트엔드 → Dashboard / Chain Sight / Portfolio에 분산
- Thesis 모델에 scope 필드 추가
- Dashboard 역할 확장 (시장 요약 → 매크로 시나리오 모니터링)

### 신규
- Portfolio 탭 (Coach, History, Review, Style 포함)
- 매크로 Thesis 시나리오 (프리셋 + 커스텀)
- Portfolio 프리셋 모드 (Quality Value, Growth Compounder 등)

---

## 4. 사용자 경험 목표

### 사용자가 느끼는 서비스 인상 변화
- 초기: "시장 흐름 보고, 종목 찾고, 내 포트폴리오 관리하는 서비스구나"
- 중기: "내 판단 기록을 바탕으로 뭘 잘하고 뭘 못하는지 알려주네"
- 장기: "이건 내 투자 방식을 같이 다듬는 코치구나"

### 핵심 차별점 (vs Wealthfront/Betterment 등 로보어드바이저)
- 판단의 주체가 사용자 (로보어드바이저는 알고리즘이 판단)
- 개별 종목 + thesis 기반 분석 (로보어드바이저는 ETF/인덱스 중심)
- Chain Sight 관계 그래프 기반 리스크 분석 (전통적 섹터 분류가 아닌 실제 비즈니스 연결)
- 과거 판단 패턴 학습 기반 개인화 코칭
- "왜" 투자했는지의 맥락이 항상 포트폴리오에 붙어있음

### UI 원칙
- Thesis라는 용어를 사용자에게 전면 노출하지 않음
  - Dashboard: "내 시나리오"
  - Chain Sight: "투자 근거"
  - Portfolio: "보유 이유"
- Portfolio Layer 1(현황)은 기본 표시, Layer 2(근거)/Layer 3(신호)는 펼침 구조
- 초보자는 현황 + 프리셋 진단만, 전문가는 thesis까지 파고드는 구조

---

## 5. MVP 우선순위

### Phase 1 — 최소 기능
1. Dashboard: 시장 브리핑 + 프리셋 매크로 시나리오 3~5개
2. Chain Sight: 기존 v1.0/v1.1 + Watching 모드 (Node Monitoring 흡수)
3. Portfolio: 현황 대시보드 + 프리셋 기반 진단 카드 + LLM 코멘트

### Phase 2 — 핵심 루프 완성
4. Portfolio Coach: 대화형 전환
5. Portfolio History/Review: 판단 기록 + 간단 사후분석
6. Chain Sight 내 Thesis 수립 UI
7. Thesis Engine scope 필드 적용

### Phase 3 — 개인화 확장
8. Dashboard 커스텀 매크로 시나리오
9. Portfolio Style 탭 분리
10. Coach 개인화 (과거 기록 기반 패턴 인식)
11. 매크로 → Portfolio 연동 알림

---

## 부록: 전체 아키텍처 데이터 흐름도

```
┌─────────────────────────────────────────────────────────┐
│                      사용자 인터페이스                       │
│                                                         │
│  ┌───────────┐  ┌───────────┐  ┌──────┐  ┌───────────┐ │
│  │ Dashboard │  │Chain Sight│  │종목상세│  │ Portfolio │ │
│  │           │  │           │  │      │  │           │ │
│  │ 매크로     │  │ Explore   │  │1차검증│  │ 현황      │ │
│  │ 시나리오   │  │ Watching  │  │기본정보│  │ 근거      │ │
│  │ 시장브리핑 │  │ Thesis수립│  │      │  │ 신호      │ │
│  │           │  │           │  │      │  │ Coach     │ │
│  │           │  │           │  │      │  │ History   │ │
│  │           │  │           │  │      │  │ Review    │ │
│  └─────┬─────┘  └─────┬─────┘  └──┬───┘  └─────┬─────┘ │
│        │              │           │             │       │
└────────┼──────────────┼───────────┼─────────────┼───────┘
         │              │           │             │
         ▼              ▼           ▼             ▼
┌─────────────────────────────────────────────────────────┐
│                      백엔드 모듈                         │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Thesis Engine (단일 모듈)              │   │
│  │  scope: macro | stock                            │   │
│  │  status: watching | holding | closed             │   │
│  │  Layer A~E 수학 모델 + LLM 보조                    │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌────────────┐ ┌────────────┐ ┌──────────────────┐    │
│  │ 1차 검증    │ │ Chain Sight│ │  Portfolio Coach  │    │
│  │ (34 지표)   │ │ Graph (Neo4j)│ │  (LLM + 기록)   │    │
│  └────────────┘ └────────────┘ └──────────────────┘    │
│                                                         │
│  ┌────────────┐ ┌────────────┐ ┌──────────────────┐    │
│  │EOD Screening│ │News Pipeline│ │ Market Breadth   │    │
│  └────────────┘ └────────────┘ └──────────────────┘    │
│                                                         │
└─────────────────────────────────────────────────────────┘
         │              │           │             │
         ▼              ▼           ▼             ▼
┌─────────────────────────────────────────────────────────┐
│                      데이터 레이어                        │
│                                                         │
│  PostgreSQL        Neo4j          Redis                 │
│  (Stock/User/Cache) (Graph)       (Cache/Celery)        │
│                                                         │
│  FMP / Finnhub / Marketaux (외부 API)                    │
└─────────────────────────────────────────────────────────┘
```
