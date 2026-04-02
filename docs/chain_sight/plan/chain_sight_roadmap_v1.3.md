# Chain Sight 개발 로드맵 v1.3

> **작성일**: 2026-04-02
> **버전**: v1.3 (관계 신뢰도 엔진 설계서 반영)
> **프로젝트**: Stock-Vis / Chain Sight
> **상태**: Phase 1 완료 (M1 마일스톤) — Neo4j 1,528 노드 + 6,217 관계
> **다음**: Phase 2 (CS-2-1~2-5) 파생 데이터 계산 파이프라인

### v1.2 → v1.3 변경 사항

- 관계 신뢰도 엔진 설계서(RELATION_CONFIDENCE.md v1.1) 결과를 로드맵에 반영
- RelationConfidence 스키마 v2.1 반영: truth_score/market_score/investment_relevance 3단 점수, evidence_tier_best, evidence_sources JSONB, relation_basis_summary, 5단계 상태(hidden/weak/probable/confirmed/stale)
- CUSTOMER_OF 별도 저장 제거 — SUPPLIES_TO만 canonical, API에서 역방향 파생
- 관계 타입을 Truth 관계 / Market 관계로 분류
- CS-0-0에 RelationConfidence v2.1 마이그레이션 추가
- CS-2-4를 RELATION_CONFIDENCE.md 기반 구현으로 명시
- CS-3-2 동기화 기준을 "confirmed 또는 probable"로 명확화
- 문서 디렉토리에 RELATION_CONFIDENCE.md 추가

---

## 1. 제작 원칙

> v1.1과 동일. 변경 없음.

Chain Sight 개발에 참여하는 모든 에이전트(Claude Code 포함)는 아래 6가지 원칙을 반드시 준수한다.

### 원칙 1 — 문서 기반 개발

모든 작업은 `docs/chain_sight/` 디렉토리의 문서를 기반으로 한다.
문서에 정의되지 않은 기능은 구현하지 않는다.
문서와 코드가 불일치하면 문서를 먼저 수정한 뒤 코드를 맞춘다.

```
docs/chain_sight/
├── plan/                       ← 설계 문서 + 작업별 계획서
│   ├── chain_sight_roadmap_v1.3.md   ← 이 문서 (전체 로드맵)
│   ├── relation_confidence_design_v1.md ← 관계 신뢰도 엔진 설계서
│   ├── cs_01_migrations.md            ← 작업별 상세 계획
│   ├── cs_02_neo4j_layer.md
│   ├── cs_03_neo4j_schema.md
│   ├── cs_11_node_bulk.md
│   ├── cs_12_sector_industry.md
│   └── cs_13_peer_relation_road.md
├── task_done/                  ← 완료된 작업 기록
│   ├── CS-0-1_migrations.md
│   ├── CS-0-2_neo4j_driver.md
│   ├── CS-0-3_neo4j_schema.md
│   ├── CS-1-1_stock_nodes.md
│   ├── CS-1-2_sectors.md
│   └── CS-1-3_peers.md
└── decisions/                  ← 주요 의사결정 기록
    └── 003_api_access_test.md
```
※ ONTOLOGY.md, DATA_COLLECTION.md, DATA_ARCHITECTURE.md, API_SPEC.md는 Phase 2~4 진행 시 필요한 시점에 생성.
  현재는 로드맵 + 작업별 plan 문서로 충분.

### 원칙 2 — 작업 완료 기록

모든 완료된 작업은 `docs/chain_sight/task_done/`에 기록한다.
파일명 규칙: `{작업번호}_{간단설명}.md`

각 기록에 포함할 내용:
- 작업 번호 및 제목
- 변경된 파일 목록
- 생성/수정된 테이블 또는 스키마
- 테스트 결과
- 발견된 이슈 및 해결 방법
- 다음 작업과의 연결점

### 원칙 3 — 개발 매니저가 파악 가능한 문서

개발 문서는 개발 매니저(병진)가 코드를 열어보지 않아도 전체 구조를 파악할 수 있어야 한다.

필수 포함 사항:
- 데이터 흐름도 (어디서 → 어디로)
- 테이블/모델 스키마 (필드명, 타입, 용도)
- Neo4j 노드/관계 속성 전체 목록
- API 요청/응답 예시
- Celery task 스케줄 및 의존 관계

### 원칙 4 — 1인 개발 원칙

1인 개발자가 유지보수할 수 있는 단순한 구조를 유지한다.

적용 규칙:
- 추상화 레이어는 최소화 (필요할 때만 추가)
- 설정보다 관습 (Convention over Configuration)
- 한 파일에서 한 가지 역할
- 외부 의존성은 검증된 것만 사용 (neo4j-driver, celery, redis)
- 마이크로서비스 금지 — Django 모놀리스 내에서 앱 분리로 해결
- "나중에 필요할 수도 있는" 기능은 만들지 않는다

### 원칙 5 — 확장 가능한 연계 구조

Chain Sight는 Stock-Vis 내 다른 서비스들과 양방향으로 연계된다.
연계 설계 시 직접 import가 아닌, 명확한 인터페이스를 통해 연결한다.

```
연계 서비스 맵:

Chain Sight ←→ Thesis Control
  · Chain Sight에서 발견한 관계 → Thesis Control 가설의 전제(premise)로 활용
  · Thesis Control 검증 결과 → Chain Sight 관계 신뢰도(confidence) 피드백

Chain Sight ←→ 1차 검증 (First Validation)
  · 1차 검증의 재무 프로파일 → Chain Sight 노드 속성 강화
  · Chain Sight의 peer 관계 → 1차 검증의 peer group 선정에 활용

Chain Sight ←→ Portfolio
  · 보유 종목 기반 Chain Sight 자동 탐색
  · Chain Sight 발견 종목 → 관심 종목/워치리스트 추가

Chain Sight ←→ News Intelligence Pipeline
  · 뉴스 이벤트 → CoMentionEdge 생성 (관계 발견)
  · 뉴스 파급 경로 → Chain Trace 시각화 데이터

Chain Sight ←→ EOD Screening
  · 스크리너 결과 종목 → Chain Sight 그래프 진입점
  · Chain Sight 클러스터 → 스크리너 필터 조건
```

연계 인터페이스 패턴:
```python
# 다른 앱에서 Chain Sight 데이터를 읽을 때
from chainsight.services import ChainSightService

# Chain Sight에서 다른 앱 데이터를 읽을 때
from metrics.services import MetricsService
from validation.services import ValidationService
```

### 원칙 6 — 사용자 경험 목표

Chain Sight의 UX 목표는 "분석에 시간을 쓰지 않는 것"이다.

핵심 경험:
- 기업 간 관계를 한눈에 파악 (그래프 시각화)
- 뉴스 흐름이 어떤 종목에 영향을 주는지 즉시 확인 (이벤트 전파 경로)
- 시장 흐름 속에서 숨겨진 연결을 자연스럽게 발견 (AI 가이드 제안)

설계 기준:
- 종목 하나의 관계 파악: 3초 이내 (1-depth 로드)
- 연쇄 경로 탐색 (A→B→C): 탭 3번 이내
- 새로운 종목 발견: 의도적 검색 없이 탐색 흐름에서 자연 발생
- 모바일에서도 핵심 탐색 가능 (Spotlight 모드)

---

## 2. 전체 아키텍처

### 2.1 4-Layer 데이터 아키텍처

```
Layer 1 — 원천 데이터 (기존 Django 앱, 변경 없음)
  stocks/     : Stock, IncomeStatement, BalanceSheet, CashFlowStatement
  news/       : NewsArticle, NewsKeyword
  screening/  : EOD 시그널 데이터

Layer 2 — 공유 파생 지표 (metrics/ 앱)
  MetricDefinition        : 34개 지표 정의 (single source of truth)
  CompanyMetricSnapshot    : 지표 스냅샷
  CompanyMetricLatest      : 최신값 캐시

Layer 3 — 읽기 전용 캐시 (validation/, chainsight/ 앱)
  validation/  : 1차 검증 전용 뷰
  chainsight/  : 기업 프로파일 + 관계 발견 결과

Layer 4 — 그래프 DB (Neo4j)
  Layer 3의 CompanyChainProfile → :Stock 노드 속성
  Layer 3의 RelationConfidence  → 엣지 (관계)
  GDS 알고리즘 결과            → 노드 속성 (pagerank, community 등)
```

### 2.2 두 트랙 구조: 개발 vs 데이터 수집

```
[트랙 A: 시스템 개발] ────────────────────────────────────────
  CS-0 인프라 → CS-1 시드로드 → CS-2 파이프라인 → CS-3 동기화 → CS-4 API → CS-5 프론트

[트랙 B: 데이터 수집] ────────────────────────────────────────
  DC-1 확보 완료     DC-2 ETF    DC-3 수동시드   DC-4 Gemini   DC-5 축적   DC-6 유료API
  (Peer+Industry)   (Holdings)  (Supply Chain)  (SC 확장)     (뉴스)      (수익화 후)

의존 관계:
  CS-0 완료 → DC-1 실행 가능 (Peer/Industry를 Neo4j에 넣으려면 연결이 먼저)
  CS-1 = DC-1의 실행 (시스템 개발 Phase 1에서 확보된 데이터를 넣는 것)
  DC-2~6은 CS-1 이후 서비스 성장에 따라 진행
```

### 2.3 데이터 흐름도

```
[외부 API]
  FMP Starter ($22/월) ─────┐
  Finnhub (무료) ───────────┤
  Marketaux ($9/월) ────────┤
  수동 시드 JSON ($0) ──────┤
  Gemini Flash ($0.03/1회) ─┘
        │
        ▼
[Layer 1: stocks/, news/]  ──읽기──▶  [Layer 2: metrics/]
        │                                      │
        │                                      ▼
        │                            [Layer 3: chainsight/]
        │                              ┌───────┴───────┐
        │                              │               │
        │                     기업 프로파일        관계 발견
        │                     (Tier A/B)       (CoMention,
        │                              │        PriceCoMove,
        │                              │        Confidence)
        │                              └───────┬───────┘
        │                                      │
        │                                      ▼
        │                              CompanyChainProfile
        │                              (집약 테이블)
        │                                      │
        │                               delta sync
        │                                      │
        │                                      ▼
        └────── 시드 데이터 ──────▶    [Layer 4: Neo4j]
          (Peers, Supply Chain,         :Stock 노드
           Sector/Industry)             :Sector, :Industry 노드
                                        관계 엣지
                                        GDS 결과
                                              │
                                              ▼
                                        [Chain Sight API]
                                              │
                                              ▼
                                        [Frontend 그래프 UI]
```

### 2.4 Neo4j 온톨로지 스키마

#### 노드 타입

| 노드 | 주요 속성 | 원천 |
|------|----------|------|
| `:Stock` | ticker, name, sector, industry, market_cap, growth_stage, sensitivity_vector, capital_dna, pagerank_score, community_id | stocks/ + chainsight/ |
| `:Sector` | name, stock_count | FMP Profile |
| `:Industry` | name, sector_name, stock_count | FMP Profile |
| `:Theme` | name, description, keywords | ETF 기반 + AI 추출 (DC-2 이후) |

#### 관계 타입

관계는 Truth 관계(사업 구조 기반)와 Market 관계(시장 현상 기반)로 분류된다.
판정 철학 상세는 `RELATION_CONFIDENCE.md` 참조.

**Truth 관계** — truth_score 계산 대상, confirmed 가능

| 관계 | 방향 | 속성 | 원천 | 데이터 수집 Phase |
|------|------|------|------|-----------------|
| `BELONGS_TO_SECTOR` | Stock → Sector | - | FMP Profile | DC-1 |
| `BELONGS_TO_INDUSTRY` | Stock → Industry | - | FMP Profile | DC-1 |
| `PEER_OF` | Stock ↔ Stock | source (finnhub/fmp) | Finnhub + FMP Peers | DC-1 |
| `SUPPLIES_TO` | Stock → Stock | confidence, source | 수동 시드 → Gemini 확장 | DC-3, DC-4 |
| `COMPETES_WITH` | Stock ↔ Stock | confidence | RelationConfidence | CS-2 |
| `HAS_THEME` | Stock → Theme | weight | ETF Holdings | DC-2 |

**Market 관계** — truth_score 비대상, confirmed 불가, 보조 라벨용

| 관계 | 방향 | 속성 | 원천 | 데이터 수집 Phase |
|------|------|------|------|-----------------|
| `CO_MENTIONED` | Stock ↔ Stock | count, last_date | CoMentionEdge (Marketaux) | DC-5 |
| `PRICE_CORRELATED` | Stock ↔ Stock | correlation, period | PriceCoMovement | CS-2 |

⚠️ **v1.3 변경**:
- `CUSTOMER_OF` 별도 저장 제거. `SUPPLIES_TO`만 canonical 저장, API에서 역방향 view로 `CUSTOMER_OF` 파생.
- undirected 관계(PEER_OF, COMPETES_WITH, CO_MENTIONED, PRICE_CORRELATED)는 저장 시 symbol_a < symbol_b 사전순 강제.

#### 제약 조건 및 인덱스

```cypher
CREATE CONSTRAINT stock_ticker IF NOT EXISTS
  FOR (s:Stock) REQUIRE s.ticker IS UNIQUE;

CREATE CONSTRAINT sector_name IF NOT EXISTS
  FOR (s:Sector) REQUIRE s.name IS UNIQUE;

CREATE CONSTRAINT industry_name IF NOT EXISTS
  FOR (i:Industry) REQUIRE i.name IS UNIQUE;

CREATE CONSTRAINT theme_name IF NOT EXISTS
  FOR (t:Theme) REQUIRE t.name IS UNIQUE;

CREATE INDEX stock_sector IF NOT EXISTS
  FOR (s:Stock) ON (s.sector);

CREATE INDEX stock_community IF NOT EXISTS
  FOR (s:Stock) ON (s.community_id);
```

### 2.5 PostgreSQL 테이블 요약 (chainsight/ 앱)

> 12개 테이블 확인 완료 (부록 A 참조). CS-0-1에서 showmigrations로 최종 검증.

#### Tier A — 완전 자동 계산 (주 1회)

| 테이블 | 역할 | 핵심 필드 |
|--------|------|----------|
| `chainsight_sensitivity_profile` | 이벤트 민감도 벡터 | symbol, interest_rate_sensitivity, forex_sensitivity, commodity_sensitivity, regulation_sensitivity |
| `chainsight_growth_stage` | 성장 스테이지 분류 | symbol, stage (startup/growth/mature/decline), confidence |
| `chainsight_capital_dna` | 자본 배분 성향 | symbol, buyback_tendency, dividend_tendency, capex_tendency, ma_tendency |
| `chainsight_insider_signal` | 내부자/기관 신호 | symbol, insider_buy_ratio, institutional_change |

⚠️ **데이터 의존성 검증**:
- `SensitivityProfile`: segment 데이터 필요 → FMP API 확인 후 ⚠️
- `GrowthStage`: metrics/ 데이터로 즉시 가능 ✅
- `CapitalDNA`: CF + BS에서 계산 가능 ✅
- `InsiderSignal`: Finnhub insider API 확인 후 ⚠️

#### Tier B — 반자동 (분기~주 1회)

| 테이블 | 역할 | 핵심 필드 |
|--------|------|----------|
| `chainsight_revenue_structure` | 매출 구조 | symbol, segments (JSONB), geographic_mix (JSONB) |
| `chainsight_narrative_tag` | 뉴스 내러티브 태그 | symbol, tags (JSONB), dominant_narrative |
| `chainsight_event_reaction` | 이벤트별 주가 반응 | symbol, event_type, avg_reaction, sample_count |

⚠️ **데이터 의존성 검증**:
- `RevenueStructure`: MVP에서는 빈 상태로 시작, 점진 채움
- `NarrativeTag`: Marketaux 뉴스에서 LLM 추출 → Phase 2 이후
- `EventReaction`: earnings 전후 주가 변동 계산 → 실행 가능 ✅

#### 관계 발견

| 테이블 | 역할 | 핵심 필드 |
|--------|------|----------|
| `chainsight_news_event` | 전용 뉴스 이벤트 | event_id, title, symbols (JSONB), event_type, published_at |
| `chainsight_co_mention_edge` | 뉴스 동시출현 | symbol_a, symbol_b, co_mention_count, last_co_mention_date |
| `chainsight_price_co_movement` | 주가 동조 분석 | symbol_a, symbol_b, correlation, period, calculated_at |
| `chainsight_relation_confidence` | 관계 신뢰도 종합 (v2.1) | symbol_a, symbol_b, relation_type, relation_category(truth/market), canonical_direction, relation_status(5단계), truth_score, market_score(null), investment_relevance(null), evidence_tier_best, evidence_count_total, evidence_count_independent, evidence_sources(JSONB), has_peer_source, has_industry_source, has_supply_chain_source, has_news_source, has_price_source, has_etf_source, has_llm_source, relation_basis_summary, first_observed_at, last_observed_at, last_verified_at, stale_threshold_days, synced_to_neo4j, score_version |

⚠️ **v1.3 변경 — RelationConfidence v2.1 적용**:
- 상태: `hidden / weak / probable / confirmed / stale` 5단계 (기존 confirmed/candidate/rejected에서 변경)
- 점수: truth_score(상태 대표값 85/60/35/15) + market_score(MVP null) + investment_relevance(MVP null)
- 증거: evidence_tier_best(1/2/3) + evidence_sources(JSONB 상세) + 7개 bool 빠른 필터
- 설명: relation_basis_summary (템플릿 기반)
- 시간: first/last_observed_at + last_verified_at (stale 판정용)
- 방향: canonical_direction + undirected 사전순 정규화
- 분류: relation_category(truth/market) — Market 관계는 truth_score 비대상
- 상세 설계: `RELATION_CONFIDENCE.md` 참조

#### 집약

| 테이블 | 역할 | 핵심 필드 |
|--------|------|----------|
| `chainsight_chain_profile` | 종합 요약 → Neo4j 투영 원천 | symbol + 개별 점수 필드 30개 (score_profitability, score_growth, ... ) + neo4j_synced (bool) + neo4j_synced_at (datetime) |

⚠️ **v1.2 수정**: v1.1에서 `profile_data (JSONB)` 단일 필드로 기술했으나, 실제 구현은 30개 개별 필드 구조. 개별 필드가 SQL 쿼리(WHERE, ORDER BY)에 직접 사용 가능하고, Django ORM 필터링이 JSONB보다 단순하므로 **현재 구조 유지**. 이 결정은 원칙 4(1인 개발, 단순 구조)에 부합.

---

## 3. 개발 Phase (트랙 A: 시스템 구축)

### Phase 0: 인프라 기반

> 목표: Neo4j 연결 가능, 테이블 존재, 기존 레거시 정리, 기본 도구 작동
> 예상 기간: 1~2일
> 의존성: 없음

| 번호 | 작업 | 산출물 | 완료 기준 |
|------|------|--------|----------|
| CS-0-0 | 레거시 정리 + API 테스트 | 부록 G 체크리스트 완료 | 기존 Chain Sight 코드 제거, API 테스트 5개 완료 |
| CS-0-1 | Django migrations 실행 + 검증 | chainsight/ 테이블 12개 생성 확인 | `python manage.py showmigrations chainsight` 전체 [X] |
| CS-0-2 | Neo4j 연결 레이어 구현 | `chainsight/graph/repository.py` | Neo4j 연결 + 간단한 읽기/쓰기 테스트 통과 |
| CS-0-3 | Neo4j 온톨로지 스키마 초기화 | `chainsight/graph/schema.py` + management command | constraint/index 생성 확인 |

⚠️ **v1.2 추가**: CS-0-0을 신규 삽입. 레거시 코드가 남아있으면 CS-0-1 이후 작업에서 혼란 발생. "정리 먼저, 구축 다음"이 원칙 4에 부합.

#### CS-0-0 상세: 레거시 정리 + API 테스트

```
실행 체크리스트 (부록 G 참조):
□ 1. serverless/ Chain Sight 코드 일괄 제거
     - views: chain_sight_*_api 6개 뷰
     - services: chain_sight_stock_service.py, category_generator.py, relationship_service.py
     - models: StockRelationship, CategoryCache — ⚠️ 실행 결과: 6개 서비스에서 참조 중이므로 모델 자체는 유지, LEGACY_KEEP 태그 처리
     - urls: chain-sight/* 라우트
     ※ ETF 모델(ETFProfile/ETFHolding/ThemeMatch)은 DC-2까지 보관 (태그: # LEGACY_KEEP_UNTIL_DC2)
     ※ StockRelationship/CategoryCache도 참조 서비스(supply_chain, institutional, regulatory, theme_matching, keyword_enricher)가 존재하므로 모델 삭제 보류. 서비스 마이그레이션 시 순차 제거 예정.

□ 2. frontend/ Chain Sight 코드 일괄 제거 + 탭 비활성화
     - components/chain-sight/ (8개 파일)
     - hooks/useChainSight*.ts (3개)
     - services/chainSightService.ts
     - types/chainSight.ts
     - utils/relationshipTagStyles.ts
     - app/chain-sight/page.tsx
     - 종목 상세 페이지에서 Chain Sight 탭을 "Coming Soon" 또는 숨김 처리

□ 3. API 테스트 5개 실행 (결과를 decisions/003_api_access_test.md에 기록)
     - FMP Stock Peers → 200/403
     - Finnhub Supply Chain → 200/403
     - Finnhub ETF Holdings → 200/403
     - Finnhub Insider Transactions → 200/403
     - FMP Revenue Segmentation → 200/403

□ 4. RelationConfidence v2.1 스키마 마이그레이션 준비
     - 기존 RelationConfidence 모델을 v2.1로 업데이트 (RELATION_CONFIDENCE.md 섹션 7 참조)
     - normalize_pair 유틸 함수 추가 (undirected 사전순 정규화)
     - CUSTOMER_OF 관련 코드가 있으면 제거

□ 5. showmigrations chainsight로 테이블 수 확인 (12개 예상)
```

#### CS-0-2 상세: Neo4j 연결 구조

```python
# chainsight/graph/repository.py

from typing import Protocol, List, Dict, Any

class GraphRepository(Protocol):
    """그래프 DB 접근 인터페이스. 백엔드 교체 가능."""
    def get_node(self, ticker: str) -> Dict[str, Any]: ...
    def get_neighbors(self, ticker: str, depth: int = 1,
                      rel_types: List[str] | None = None) -> Dict: ...
    def upsert_node(self, label: str, key_field: str, key_value: str, properties: Dict) -> None: ...
    def upsert_edge(self, from_ticker: str, to_ticker: str,
                    rel_type: str, properties: Dict) -> None: ...
    def bulk_upsert_nodes(self, label: str, key_field: str, nodes_data: List[Dict]) -> int: ...
    def bulk_upsert_edges(self, rel_type: str, edges_data: List[Dict]) -> int: ...
    def run_query(self, cypher: str, params: Dict) -> List[Dict]: ...


class Neo4jGraphRepository:
    """
    실제 Neo4j 구현체.

    ⚠️ Celery prefork 환경에서 driver를 global singleton으로
    캐싱하면 SIGSEGV 발생 (이전에 분석 완료).
    PID 기반 lazy initialization으로 fork 안전하게 처리.
    """
    def __init__(self, uri: str, user: str, password: str):
        self._uri = uri
        self._user = user
        self._password = password
        self._driver = None
        self._pid = None

    @property
    def driver(self):
        import os
        if self._driver is None or self._pid != os.getpid():
            from neo4j import GraphDatabase
            self._driver = GraphDatabase.driver(
                self._uri, auth=(self._user, self._password)
            )
            self._pid = os.getpid()
        return self._driver
```

설정:
```python
# config/settings.py 추가
NEO4J_URI = env('NEO4J_URI', default='bolt://localhost:7687')
NEO4J_USER = env('NEO4J_USER', default='neo4j')
NEO4J_PASSWORD = env('NEO4J_PASSWORD', default='password')
```

---

### Phase 1: 초기 데이터 로드 (DC-1 실행)

> 목표: Neo4j에 탐색 가능한 최소 데이터 존재 (PEER_OF + SAME_INDUSTRY)
> 예상 기간: 3~5일
> 의존성: Phase 0 완료

| 번호 | 작업 | 산출물 | 완료 기준 |
|------|------|--------|----------|
| CS-1-1 | Stock 노드 벌크 로드 | management command `load_stocks_to_neo4j` | S&P 500 :Stock 노드 500개 확인 |
| CS-1-2 | Sector/Industry 노드 + 관계 | management command `load_sectors_to_neo4j` | :Sector ~11개, :Industry ~70개, BELONGS_TO 관계 ~1,000개 |
| CS-1-3 | Peer 관계 로드 (Finnhub + FMP) | Celery task `fetch_and_load_peers` | PEER_OF 2,500~3,500개 |

#### Phase 1 완료 시 Neo4j 상태

```
노드: ~580개 (Stock 500 + Sector 11 + Industry 70)
관계: ~4,500개 (BELONGS_TO ~1,000 + PEER_OF ~3,500)

★ 최소 데모 가능 지점. 파도타기 핵심 경험은 이것만으로 작동.
```

---

### Phase 2: 파생 데이터 계산 파이프라인

> 목표: PostgreSQL에서 기업 프로파일 + 관계 발견 자동 계산
> 예상 기간: 1~2주
> 의존성: Phase 1 완료 + metrics/ 앱 작동

| 번호 | 작업 | 산출물 | 완료 기준 |
|------|------|--------|----------|
| CS-2-1 | Tier A 계산 tasks (데이터 확보된 것만) | `chainsight/tasks/profile_tasks.py` | GrowthStage, CapitalDNA 테이블 적재 |
| CS-2-2 | CoMentionEdge 추출 | `chainsight/tasks/relation_tasks.py` | Marketaux 뉴스에서 동시출현 쌍 추출 |
| CS-2-3 | PriceCoMovement 계산 | 같은 파일 내 task | 90일 rolling correlation 계산 |
| CS-2-4 | RelationConfidence 종합 | 같은 파일 내 task | `RELATION_CONFIDENCE.md` 정책표 기반 판정: Tier 1/2/3 증거 등급 분류, truth_score 계산, 5단계 상태 판정, relation_basis_summary 생성 |
| CS-2-5 | CompanyChainProfile 집약 | `chainsight/tasks/sync_tasks.py` | 프로파일 + 관계 → 집약 테이블 |

CS-2-1 범위는 CS-0-0 API 테스트 결과에 따라 결정:
- `GrowthStage`: ✅ 즉시 가능
- `CapitalDNA`: ✅ 즉시 가능
- `SensitivityProfile`: API 테스트 결과에 따라
- `InsiderSignal`: API 테스트 결과에 따라

#### Celery Beat 스케줄

```python
CELERY_BEAT_SCHEDULE = {
    # Chain Sight — 일간
    'chainsight-co-mention-daily': {
        'task': 'chainsight.tasks.extract_co_mentions',
        'schedule': crontab(hour=6, minute=30),
    },
    # Chain Sight — 주간 (일요일)
    'chainsight-profiles-weekly': {
        'task': 'chainsight.tasks.calculate_all_profiles',
        'schedule': crontab(hour=2, minute=0, day_of_week=0),
    },
    'chainsight-price-comovement-weekly': {
        'task': 'chainsight.tasks.calculate_price_co_movement',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),
    },
    'chainsight-relation-confidence-weekly': {
        'task': 'chainsight.tasks.update_relation_confidence',
        'schedule': crontab(hour=4, minute=0, day_of_week=0),
        # RELATION_CONFIDENCE.md 정책표 기반 판정 실행
    },
    'chainsight-stale-decay-weekly': {
        'task': 'chainsight.tasks.check_stale_and_decay',
        'schedule': crontab(hour=4, minute=30, day_of_week=0),
        # confirmed→stale, probable→weak, weak→hidden 하향 전이
    },
    'chainsight-chain-profile-weekly': {
        'task': 'chainsight.tasks.aggregate_chain_profiles',
        'schedule': crontab(hour=5, minute=0, day_of_week=0),
    },
}
```

---

### Phase 3: Neo4j 동기화 + GDS

> 목표: PostgreSQL 파생 데이터 → Neo4j 반영 + 그래프 알고리즘 결과 확보
> 예상 기간: 3~5일
> 의존성: Phase 2 완료

| 번호 | 작업 | 산출물 | 완료 기준 |
|------|------|--------|----------|
| CS-3-1 | ChainProfile → Neo4j 속성 동기화 | sync task | :Stock 노드에 프로파일 속성 반영 |
| CS-3-2 | RelationConfidence → Neo4j 엣지 동기화 | sync task | Truth 관계 중 confirmed 또는 probable만 엣지 생성. Market 관계는 보조 속성으로 첨부. |
| CS-3-3 | GDS 알고리즘 배치 | `chainsight/tasks/gds_tasks.py` | pagerank, community_id, betweenness 노드 속성 |

#### CS-3-1 동기화 전략

```
동기화 방식: Delta Sync (변경분만)
식별 기준: CompanyChainProfile.neo4j_synced == False
주기: 주 1회 (Phase 2 집약 후 실행)
실패 처리: 실패 건 로깅 + 다음 주기에 재시도
```

#### ⚠️ CS-3-3 GDS 의존성 주의

```
Neo4j GDS (Graph Data Science) 라이브러리는 별도 설치 필요.
- Neo4j Community Edition: GDS 무료 사용 가능 (Apache 2.0)
- Neo4j AuraDB Free: GDS 미지원
- Self-hosted: neo4j-community + GDS 플러그인 설치
현재 환경 (MacBook self-hosted)에서는 문제없음.
프로덕션 배포 시 GDS 포함 Docker 이미지 필요.
```

---

### Phase 4: API 엔드포인트

> v1.1과 동일. 변경 없음.

| 번호 | 작업 | 엔드포인트 | 완료 기준 |
|------|------|-----------|----------|
| CS-4-1 | 그래프 탐색 API | `GET /api/stocks/{symbol}/chainsight/graph/` | depth 파라미터로 N-depth 조회, nodes+edges 응답 |
| CS-4-2 | 탐색 제안 API | `GET /api/stocks/{symbol}/chainsight/suggestions/` | 맥락화된 카테고리 목록 반환 |
| CS-4-3 | 경로 탐색 API | `GET /api/chainsight/trace/` | 두 종목 간 최단 경로 반환 |

---

### Phase 5: 프론트엔드

> v1.1과 동일. 변경 없음.

| 번호 | 작업 | 산출물 | 완료 기준 |
|------|------|--------|----------|
| CS-5-1 | 그래프 시각화 컴포넌트 | `components/chainsight/GraphView.tsx` | Spotlight 모드 + lazy expansion |
| CS-5-2 | AI 가이드 탐색 UI | `components/chainsight/SuggestionCards.tsx` | 카테고리 선택 → 그래프 필터링 |
| CS-5-3 | Chain Trace 시각화 | `components/chainsight/TraceView.tsx` | 경로 하이라이트 + 단계별 설명 |
| CS-5-4 | 종목 상세 페이지 연계 | 기존 종목 상세 수정 | Chain Sight 미니 뷰 임베드 |

---

## 4. 데이터 수집 방안 (트랙 B: 그래프 데이터 확보)

> v1.1과 동일. 변경 없음. 섹션 4.1~4.9 전체 유지.

### 4.1 현재 API 스택 + 접근 가능 여부

```
확정된 API 스택 (현재 사용 중):
  FMP Starter     $22/월  — Profile, Peers, Quote, Financials (US, Annual)
  Finnhub Free    $0/월   — Peers, News, Quote, Sentiment
  Marketaux       $9/월   — News + Entity Tagging
  FRED            $0/월   — 거시경제 지표
  yfinance        $0/월   — 지수, 섹터 ETF, 환율
  합계:           $31/월
```

#### 엔드포인트별 접근 가능 여부

| 엔드포인트 | 상태 | 근거 |
|-----------|------|------|
| Finnhub Peers (`/stock/peers`) | ✅ 확인됨 (무료) | 실사용 중 |
| FMP Profile (`/stable/profile`) | ✅ 확인됨 (Starter) | 실사용 중 |
| FMP Stock Peers (`/stable/stock-peers`) | ⚠️ 미확인 | CS-0-0에서 테스트 |
| Finnhub Supply Chain (`/stock/supply-chain`) | ❌ 불가 추정 | CS-0-0에서 테스트 |
| Finnhub ETF Holdings (`/etf/holdings`) | ⚠️ 미확인 | CS-0-0에서 테스트 |
| FMP ETF Holdings (`/stable/etf-holder`) | ❌ 불가 추정 | Starter에서 403/404 |
| Finnhub Insider Transactions | ⚠️ 미확인 | CS-0-0에서 테스트 |
| FMP Revenue Segmentation | ⚠️ 미확인 | CS-0-0에서 테스트 |

### 4.2 데이터 수집 6-Phase 로드맵

핵심 원칙: **PEER_OF + SAME_INDUSTRY만으로도 파도타기는 작동한다. 나머지는 성장하면서 붙인다.**

```
DC-1 (MVP 런칭)         → PEER_OF + SAME_INDUSTRY ~6,500개, $0
DC-2 (런칭 +1주)        → ETF Holdings → HAS_THEME ~390개, $0
DC-3 (런칭 +2주)        → 수동 시드 JSON → Supply Chain ~500개, $0
DC-4 (런칭 +3주)        → Gemini Flash → Supply Chain 확장 ~1,100개, ~$0.05
DC-5 (런칭 +1개월~)     → Marketaux 뉴스 자연 축적, $0
DC-6 (수익화 이후)       → Finnhub Premium → ~2,500개+, $200/월
```

#### Phase별 누적 관계 수

| Phase | 시점 | PEER/INDUSTRY | Supply Chain | ETF Theme | CO_MENTIONED | 누적 총 |
|-------|------|-------------|-------------|-----------|-------------|--------|
| DC-1 | MVP 런칭 | ~6,500 | 0 | 0 | 0 | ~6,500 |
| DC-2 | +1주 | ~6,500 | 0 | ~390 | ~50 | ~6,940 |
| DC-3 | +2주 | ~6,500 | ~500 | ~390 | ~100 | ~7,490 |
| DC-4 | +3주 | ~6,500 | ~1,100 | ~390 | ~200 | ~8,190 |
| DC-5 | +3개월 | ~6,500 | ~1,340 | ~390 | ~1,000 | ~9,230 |
| DC-6 | 수익화 후 | ~6,500 | ~2,500+ | ~390 | ~2,000+ | ~11,390+ |

### 4.3~4.9 상세

> v1.1 섹션 4.3~4.9와 동일. DC-1(Peers+Industry), DC-2(ETF Holdings 의사결정 트리), DC-3(수동 시드 JSON 구조), DC-4(Gemini Flash 비용 계산 + 검증 레이어), DC-5(뉴스 축적 로직), DC-6(유료 업그레이드 트리거), 비용 요약표 전부 유지.

---

## 5. 마일스톤 요약

```
M0 (CS Phase 0 완료): "레거시 정리됨, Neo4j 연결됨, 테이블 있음"
  → API 테스트 결과가 decisions/에 기록됨
  → 기존 Chain Sight 코드가 제거되어 깨끗한 상태
  → RelationConfidence v2.1 스키마 마이그레이션 완료

M1 (CS Phase 1 + DC-1 완료): "그래프에 데이터가 있음"
  → PEER_OF + SAME_INDUSTRY ~6,500개
  → Neo4j Browser에서 Cypher로 관계 탐색 가능
  ★ 최소 데모 가능 지점 — 파도타기 핵심 경험 확인

M1.5 (DC-2 + DC-3 완료): "관계가 풍부해짐"
  → +ETF Theme ~390개 + Supply Chain ~500개 = ~7,390개
  → 공급망 + 테마 탐색 카테고리 활성화

M2 (CS Phase 2 완료): "관계 신뢰도 엔진 작동"
  ★ 서비스 품질의 핵심 마일스톤
  → RELATION_CONFIDENCE.md 정책표 기반 판정 실행
  → 5단계 상태(hidden/weak/probable/confirmed/stale) 자동 판정
  → relation_basis_summary로 "왜 이 관계인가" 설명 가능
  → DC-4 (Gemini Flash) 실행으로 Supply Chain ~1,100개 도달

M3 (CS Phase 3 완료): "Neo4j가 풍부해짐"
  → GDS 알고리즘으로 중요도/클러스터 식별
  → API 응답에 pagerank, community 정보 포함

M4 (CS Phase 4 완료): "API 완성"
  → 프론트엔드 개발 시작 가능
  → API에 explanation + market_signals 포함

M5 (CS Phase 5 완료): "사용자 경험 가능"
  → Chain Sight MVP 릴리즈
  → DC-5 자연 축적이 시간 경과에 따라 그래프를 풍부하게 함
```

---

## 6. 미해결 사항 + 선행 확인 필요 사항

### 🚨 착수 전 선행 확인 (CS-0-0에서 실행)

| 테스트 | 결과별 영향 | 우선순위 |
|--------|-----------|---------|
| FMP Stock Peers (Starter 접근) | 200 → DC-1 보강 / 403 → Finnhub만 사용 | ★★★ |
| Finnhub Supply Chain (무료 접근) | 200 → DC-6 불필요! / 403 → 6-Phase 유지 | ★★★ |
| Finnhub ETF Holdings (무료 접근) | 200 → DC-2 간단 해결 / 403 → CSV 방식 | ★★★ |
| Finnhub Insider Transactions | 200 → CS-2-1 InsiderSignal 구현 / 403 → 보류 | ★★ |
| FMP Revenue Segmentation | 200 → CS-2-1 SensitivityProfile 구현 / 403 → 보류 | ★★ |

### 미해결 의사결정

| 항목 | 상태 | 결정 시점 |
|------|------|----------|
| ETF Holdings 소싱 방식 최종 | CS-0-0 API 테스트 결과에 따라 | CS-0 완료 직후 |
| Theme 노드 생성 방식 | ETF 기반 (DC-2) + AI 추출 (추후) | DC-2 진입 시 |
| Tier A/B 중 데이터 확보 안 되는 것 | API 테스트 후 가능한 것만 먼저 | CS-2 진입 시 |
| GDS 프로덕션 배포 | Self-hosted OK, 클라우드 시 별도 검토 | CS-3 진입 시 |
| 모바일 그래프 UX 상세 | Spotlight 모드 개념만 확정 | CS-5 진입 시 |
| 다른 서비스 연계 API 구현 | 인터페이스 설계만 완료 | 각 서비스 MVP 이후 |

---

## 7. 참고 링크 (과거 대화)

- [온톨로지 개념 + 시각화 채널 설계](https://claude.ai/chat/3367db39-1dc2-42a0-af8f-16a83c94ba32)
- [Neo4j 마이그레이션 프롬프트](https://claude.ai/chat/57b5df78-2b18-4e7d-affb-53f9c6b11edf)
- [Chain Sight 서비스 블루프린트 + 6-Phase](https://claude.ai/chat/b6c86492-c576-4bdc-a1e1-9a724869113a)
- [Chain Sight 방향성 + API 접근 테스트](https://claude.ai/chat/695bbcfa-b714-40d9-a9df-59708acfc36f)
- [Supply Chain 3-Layer 전략 + Gemini Flash 상세](https://claude.ai/chat/3becac7b-f011-40c8-a439-77fd72828fad)
- [스키마 작업 + 4-Layer 아키텍처](https://claude.ai/chat/edeb9a23-eb98-4422-8fda-264700c0ac97)
- [FMP Starter 플랜 분석](https://claude.ai/chat/b313b88b-d977-459d-b1e3-1839904b73ac)
- [FMP 비용 비교 분석](https://claude.ai/chat/2e12922a-45ad-4247-bec7-d0bee7201093)
- [API 스택 종합 분석 + SEC EDGAR](https://claude.ai/chat/0b863ff0-ae2d-447e-817d-96488ff8661b)
- [UI/UX Designer 서브에이전트](https://claude.ai/chat/f6a23bb6-fd2b-4cc7-9590-606f73f5d90a)

---

## 부록: 현재 구현 현황 대조 (2026-04-01 기준)

### A. chainsight/ 앱 모델 현황

**완료된 것 (PR-6~8 + 보완 작업에서 생성):**

| 모델 | 테이블명 | 로드맵 매핑 | 데이터 | 상태 |
|------|---------|------------|--------|------|
| CompanySensitivityProfile | chainsight_sensitivity_profile | Tier A | 0건 | ✅ 모델 존재, 데이터 미적재 |
| CompanyGrowthStage | chainsight_growth_stage | Tier A | 0건 | ✅ |
| CompanyCapitalDNA | chainsight_capital_dna | Tier A | 0건 | ✅ |
| CompanyInsiderSignal | chainsight_insider_signal | Tier A | 0건 | ✅ |
| CompanyNarrativeTag | chainsight_narrative_tag | Tier B | 0건 | ✅ |
| CompanyEventReaction | chainsight_event_reaction | Tier B | 0건 | ✅ |
| CompanyRevenueStructure | chainsight_revenue_structure | Tier B | 0건 | ✅ |
| CompanyChainProfile | chainsight_chain_profile | 집약 | 0건 | ✅ neo4j_synced/neo4j_synced_at 추가 완료 |
| ChainNewsEvent | chainsight_news_event | 뉴스 이벤트 | 0건 | ✅ |
| CoMentionEdge | chainsight_co_mention_edge | 관계 발견 | 0건 | ✅ 신규 생성 완료 |
| PriceCoMovement | chainsight_price_co_movement | 관계 발견 | 0건 | ✅ 신규 생성 완료 |
| RelationConfidence | chainsight_relation_confidence | 관계 발견 | 0건 | ✅ 신규 생성 완료 |

**총 12개 테이블.**

⚠️ **v1.2 검증 노트**: v1.1 본문에서 "13개 테이블"이라고 기술한 것은 오류. 실제 모델은 12개. Tier A(4) + Tier B(3) + 관계 발견(3) + 뉴스 이벤트(1) + 집약(1) = 12개. v1.2 본문 섹션 2.5에서 "12개 테이블"로 수정 완료. CS-0-1에서 `showmigrations`로 최종 확인.

**CompanyChainProfile 구조 결정:**

로드맵 v1.1에서 `profile_data (JSONB)` 단일 필드로 제안했으나, 실제 구현은 30개 개별 필드. **현재 구조 유지 결정.**
이유: 개별 필드가 SQL 쿼리(WHERE, ORDER BY)에 직접 사용 가능하고, Django ORM 필터링이 JSONB보다 단순. 원칙 4(1인 개발, 단순 구조)에 부합.

### B. 기존 serverless 앱 Chain Sight 코드 (CS-0-0에서 제거)

| 위치 | 파일/코드 | 역할 | 처리 |
|------|----------|------|------|
| serverless/models.py | StockRelationship | 관계 저장 | ❌ CS-0-0에서 제거 → RelationConfidence로 대체 |
| serverless/models.py | CategoryCache | AI 카테고리 캐시 | ❌ CS-0-0에서 제거 → CompanyNarrativeTag로 대체 |
| serverless/models.py | ETFProfile, ETFHolding, ThemeMatch | ETF 데이터 | ⚠️ DC-2까지 보관 (태그: `# LEGACY_KEEP_UNTIL_DC2`), **DC-2 완료 시 제거** (Neo4j :Theme + HAS_THEME로 대체) |
| serverless/views.py | chain_sight_*_api (6개 뷰) | Chain Sight API | ❌ CS-0-0에서 제거 |
| serverless/services/ | chain_sight 관련 3개 파일 | 서비스 로직 | ❌ CS-0-0에서 제거 |
| serverless/urls.py | chain-sight/* 라우트 | URL 라우팅 | ❌ CS-0-0에서 제거 |

⚠️ **v1.2 수정 (v1.1 모순 해결)**:
- v1.1에서는 백엔드를 CS-0-1에서 제거하지만 프론트엔드는 CS-5까지 유지한다고 했음.
- 문제: 백엔드 API가 없어지면 프론트 Chain Sight 탭은 어차피 깨짐.
- **해결: 백엔드 + 프론트엔드를 CS-0-0에서 동시 제거. 종목 상세의 Chain Sight 탭은 비활성화("Coming Soon" 또는 숨김).**
- 원칙 4 부합: 죽은 코드를 유지하면서 "나중에 지울 것"으로 두는 것보다 깨끗한 상태에서 시작하는 것이 나음.

### C. 프론트엔드 기존 코드 (CS-0-0에서 동시 제거)

| 위치 | 파일 수 | 처리 |
|------|---------|------|
| frontend/components/chain-sight/ | 8개 | ❌ CS-0-0에서 제거 |
| frontend/hooks/useChainSight*.ts | 3개 | ❌ CS-0-0에서 제거 |
| frontend/services/chainSightService.ts | 1개 | ❌ CS-0-0에서 제거 |
| frontend/types/chainSight.ts | 1개 | ❌ CS-0-0에서 제거 |
| frontend/utils/relationshipTagStyles.ts | 1개 | ❌ CS-0-0에서 제거 |
| frontend/app/chain-sight/page.tsx | 1개 | ❌ CS-0-0에서 제거 |
| 종목 상세 페이지 Chain Sight 탭 | - | CS-0-0에서 비활성화 ("Coming Soon" 또는 숨김) |

### D. graph_analysis/ 앱과의 관계

> v1.1과 동일. **독립 유지. 겹치지 않음.**

| 항목 | graph_analysis | chainsight |
|------|---------------|------------|
| 목적 | 가격 상관관계 (워치리스트 기반) | 사업/산업/뉴스 기반 관계 발견 |
| 핵심 모델 | CorrelationEdge, CorrelationAnomaly | RelationConfidence, CoMentionEdge |
| 데이터 소스 | DailyPrice | 뉴스, 재무제표, ETF, LLM |
| 사용자 인터페이스 | 워치리스트 상관계수 히트맵 | 종목 중심 그래프 탐색 |

→ 향후 chainsight의 PriceCoMovement와 graph_analysis의 CorrelationEdge가 데이터를 공유할 수 있지만, 현재는 별도 계산 유지.

### E. 1차 검증(validation)과의 연계 확인

**현재 연계 포인트:**
1. metrics/CompanyMetricSnapshot → chainsight Tier A 계산의 원천 데이터 ✅
2. validation/CategorySignal → CompanyChainProfile의 score_profitability 등에 반영 예정 (CS-2-5)
3. validation/PeerPreset → Phase 6 thematic 프리셋이 CompanyNarrativeTag.theme_tags 의존

⚠️ **v1.2 추가: 의존 방향 규칙**

```
허용되는 방향:
  metrics/    → chainsight/  (chainsight가 metrics 읽기)     ✅
  validation/ → chainsight/  (validation이 chainsight 읽기)  ✅
  chainsight/ → metrics/     (chainsight가 metrics 읽기)     ✅
  chainsight/ → validation/  (chainsight가 validation 읽기)  ✅

금지:
  양방향 직접 import (순환 참조 위험)

원칙:
  - 모든 교차 참조는 서비스 레이어(services.py)에서만 수행
  - models.py에서 다른 앱의 모델을 직접 ForeignKey하지 않음
  - 연계가 필요한 경우 symbol(CharField)로 느슨하게 연결
```

구체적으로:
- validation/PeerPreset이 chainsight/CompanyNarrativeTag.theme_tags를 참조할 때:
  `from chainsight.services import ChainSightService` → `service.get_theme_tags(symbol)`
- chainsight/가 validation/CategorySignal을 읽을 때:
  `from validation.services import ValidationService` → `service.get_category_scores(symbol)`

### F. 수정/보완 이력

| 날짜 | 작업 | 이유 |
|------|------|------|
| 2026-04-01 | CompanyChainProfile에 neo4j_synced, neo4j_synced_at 필드 추가 | CS-3-1 Delta Sync에 필수 |
| 2026-04-01 | CoMentionEdge, PriceCoMovement, RelationConfidence 모델 신규 생성 | CS-2-2~CS-2-4 관계 발견 테이블 |
| 2026-04-01 | 기존 serverless/frontend Chain Sight 코드 제거 방침 결정 | chainsight/ 앱 중심 구조와 충돌 |
| 2026-04-01 | CompanyChainProfile JSONB → 개별 필드 구조 유지 결정 | 원칙 4 부합 |
| 2026-04-01 (v1.2) | 백엔드+프론트 동시 제거로 방침 통일 | v1.1 부록 B/C 제거 시점 모순 해결 |
| 2026-04-01 (v1.2) | ETF 모델 "DC-2 완료 시 제거" 명확화 | v1.1 "보류"에서 종료 조건 명시 |
| 2026-04-01 (v1.2) | 테이블 수 13개→12개 수정 | 부록 A 실 카운트와 본문 불일치 해결 |
| 2026-04-01 (v1.2) | 의존 방향 규칙 추가 | 순환 참조 방지, 연계 패턴 표준화 |
| 2026-04-02 (v1.3) | RelationConfidence v2.1 스키마 반영 | 관계 신뢰도 엔진 설계서 결과 |
| 2026-04-02 (v1.3) | CUSTOMER_OF 별도 저장 제거 | SUPPLIES_TO canonical + API 역방향 파생 |
| 2026-04-02 (v1.3) | 관계 타입 Truth/Market 분류 추가 | PRICE_CORRELATED, CO_MENTIONED는 Market 관계 |
| 2026-04-02 (v1.3) | 5단계 상태 체계 적용 | hidden/weak/probable/confirmed/stale |

### G. CS-0 착수 시 실행 체크리스트

```
━━━ 0단계: 레거시 정리 ━━━
□ serverless/ Chain Sight 코드 일괄 제거
    - views: chain_sight_*_api 6개
    - services: chain_sight_stock_service.py, category_generator.py, relationship_service.py
    - models: StockRelationship, CategoryCache
    - urls: chain-sight/* 라우트
    ※ ETFProfile/ETFHolding/ThemeMatch는 # LEGACY_KEEP_UNTIL_DC2 태그 후 보관

□ frontend/ Chain Sight 코드 일괄 제거
    - components/chain-sight/ (8개)
    - hooks/useChainSight*.ts (3개)
    - services/chainSightService.ts
    - types/chainSight.ts
    - utils/relationshipTagStyles.ts
    - app/chain-sight/page.tsx
    - 종목 상세 Chain Sight 탭 → "Coming Soon" 또는 숨김

━━━ 1단계: API 접근 테스트 ━━━
□ FMP Stock Peers → 200 / 403       → 결과 기록
□ Finnhub Supply Chain → 200 / 403  → 결과 기록
□ Finnhub ETF Holdings → 200 / 403  → 결과 기록
□ Finnhub Insider Transactions → 200 / 403  → 결과 기록
□ FMP Revenue Segmentation → 200 / 403      → 결과 기록
□ 결과를 docs/chain_sight/decisions/003_api_access_test.md에 기록

━━━ 2단계: 스키마 + 인프라 ━━━
□ RelationConfidence v2.1 모델 업데이트 (RELATION_CONFIDENCE.md 섹션 7 참조)
□ normalize_pair 유틸 함수 추가 (undirected 사전순 정규화)
□ CUSTOMER_OF 관련 코드 제거 (있으면)
□ python manage.py makemigrations chainsight
□ python manage.py migrate
□ python manage.py showmigrations chainsight → 12개 테이블 [X] 확인
□ Neo4j 서버 구동 확인 (bolt://localhost:7687 접속)
□ neo4j-driver 패키지 설치 확인

━━━ 3단계: 다음 작업 결정 ━━━
□ API 테스트 결과 기반으로 DC-2 방식 결정 (Finnhub / CSV / 2단 구조)
□ API 테스트 결과 기반으로 CS-2-1 범위 결정 (어떤 Tier A가 가능한지)
□ CS-0-1 착수
```

---

**END OF DOCUMENT**