# Chain Sight 개발 로드맵 v1.1

> **작성일**: 2026-04-01
> **버전**: v1.1 (v1.0 교차검증 + 데이터 수집 방안 추가)
> **프로젝트**: Stock-Vis / Chain Sight
> **상태**: Phase 0 착수 전

### v1.0 → v1.1 변경 사항

- 개발 Phase(CS-0~5)와 데이터 수집 Phase(DC-1~6)를 명확히 분리
- Supply Chain 6-Phase 로드맵 통합 (서비스 블루프린트에서 확정했던 것)
- API 접근 가능 여부를 확인됨/미확인/불가로 구분하여 명시
- Phase 1에서 Supply Chain 시드를 제거 → DC-3 시점으로 이동 (6-Phase 원칙 준수)
- Finnhub `etfs-holdings` 엔드포인트 발견 사항 반영
- GDS 라이브러리 의존성 주의사항 추가
- Tier A 계산의 실제 데이터 의존성 검증 결과 반영

---

## 1. 제작 원칙

> v1.0과 동일. 변경 없음.

Chain Sight 개발에 참여하는 모든 에이전트(Claude Code 포함)는 아래 6가지 원칙을 반드시 준수한다.

### 원칙 1 — 문서 기반 개발

모든 작업은 `docs/chain_sight/` 디렉토리의 문서를 기반으로 한다.
문서에 정의되지 않은 기능은 구현하지 않는다.
문서와 코드가 불일치하면 문서를 먼저 수정한 뒤 코드를 맞춘다.

```
docs/chain_sight/
├── ROADMAP.md                  ← 이 문서 (전체 로드맵)
├── ONTOLOGY.md                 ← 온톨로지 스키마 정의
├── DATA_COLLECTION.md          ← 데이터 수집 방안 (이 문서의 섹션 4)
├── DATA_ARCHITECTURE.md        ← 4-Layer 데이터 흐름
├── API_SPEC.md                 ← API 엔드포인트 명세
├── task_done/                  ← 완료된 작업 기록
│   ├── CS-0-1_migrations.md
│   ├── CS-0-2_neo4j_driver.md
│   └── ...
└── decisions/                  ← 주요 의사결정 기록
    ├── 001_neo4j_vs_age.md
    ├── 002_supply_chain_strategy.md
    └── ...
```

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

v1.0에서는 개발 Phase에 데이터 수집이 섞여 있었는데, 이 두 가지는 독립된 트랙이다.

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

| 노드        | 주요 속성                                                                                                               | 원천                           |
| ----------- | ----------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| `:Stock`    | ticker, name, sector, industry, market_cap, growth_stage, sensitivity_vector, capital_dna, pagerank_score, community_id | stocks/ + chainsight/          |
| `:Sector`   | name, stock_count                                                                                                       | FMP Profile                    |
| `:Industry` | name, sector_name, stock_count                                                                                          | FMP Profile                    |
| `:Theme`    | name, description, keywords                                                                                             | ETF 기반 + AI 추출 (DC-2 이후) |

#### 관계 타입

| 관계                  | 방향             | 속성                 | 원천                      | 데이터 수집 Phase |
| --------------------- | ---------------- | -------------------- | ------------------------- | ----------------- |
| `BELONGS_TO_SECTOR`   | Stock → Sector   | -                    | FMP Profile               | DC-1              |
| `BELONGS_TO_INDUSTRY` | Stock → Industry | -                    | FMP Profile               | DC-1              |
| `PEER_OF`             | Stock ↔ Stock    | source (finnhub/fmp) | Finnhub + FMP Peers       | DC-1              |
| `SUPPLIES_TO`         | Stock → Stock    | confidence, source   | 수동 시드 → Gemini 확장   | DC-3, DC-4        |
| `CUSTOMER_OF`         | Stock → Stock    | confidence, source   | 수동 시드 → Gemini 확장   | DC-3, DC-4        |
| `CO_MENTIONED`        | Stock ↔ Stock    | count, last_date     | CoMentionEdge (Marketaux) | DC-5              |
| `PRICE_CORRELATED`    | Stock ↔ Stock    | correlation, period  | PriceCoMovement           | CS-2              |
| `HAS_THEME`           | Stock → Theme    | weight               | ETF Holdings              | DC-2              |
| `COMPETES_WITH`       | Stock ↔ Stock    | confidence           | RelationConfidence        | CS-2              |

#### v1.0 교차검증 결과: 수정된 점

- `SUPPLIES_TO`/`CUSTOMER_OF`를 CS-1(개발 Phase 1)이 아닌 DC-3(데이터 수집 Phase 3)으로 이동. 6-Phase 원칙에 따라 MVP 런칭 시에는 PEER_OF + SAME_INDUSTRY만으로 시작.
- `HAS_THEME` Phase를 "3+"에서 DC-2로 변경. ETF Holdings 확보가 Phase 2에 해당.

#### 제약 조건 및 인덱스

```cypher
-- 유니크 제약
CREATE CONSTRAINT stock_ticker IF NOT EXISTS
  FOR (s:Stock) REQUIRE s.ticker IS UNIQUE;

CREATE CONSTRAINT sector_name IF NOT EXISTS
  FOR (s:Sector) REQUIRE s.name IS UNIQUE;

CREATE CONSTRAINT industry_name IF NOT EXISTS
  FOR (i:Industry) REQUIRE i.name IS UNIQUE;

CREATE CONSTRAINT theme_name IF NOT EXISTS
  FOR (t:Theme) REQUIRE t.name IS UNIQUE;

-- 검색 성능 인덱스
CREATE INDEX stock_sector IF NOT EXISTS
  FOR (s:Stock) ON (s.sector);

CREATE INDEX stock_community IF NOT EXISTS
  FOR (s:Stock) ON (s.community_id);
```

### 2.5 PostgreSQL 테이블 요약 (chainsight/ 앱)

> v1.0과 동일. 변경 없음.
> 13개 테이블: Tier A 4개, Tier B 3개, 관계 발견 4개, 집약 1개, 뉴스 이벤트 1개

#### Tier A — 완전 자동 계산 (주 1회)

| 테이블                                   | 역할               | 핵심 필드                                                                                           |
| ---------------------------------------- | ------------------ | --------------------------------------------------------------------------------------------------- |
| `chainsight_company_sensitivity_profile` | 이벤트 민감도 벡터 | symbol, interest_rate_sensitivity, forex_sensitivity, commodity_sensitivity, regulation_sensitivity |
| `chainsight_company_growth_stage`        | 성장 스테이지 분류 | symbol, stage (startup/growth/mature/decline), confidence                                           |
| `chainsight_company_capital_dna`         | 자본 배분 성향     | symbol, buyback_tendency, dividend_tendency, capex_tendency, ma_tendency                            |
| `chainsight_company_insider_signal`      | 내부자/기관 신호   | symbol, insider_buy_ratio, institutional_change                                                     |

⚠️ **v1.1 검증 노트**: Tier A 4개 테이블의 실제 계산에 필요한 원천 데이터를 검증해야 함.

- `SensitivityProfile`: debt_to_equity(BS), foreign_revenue_pct(IS 세그먼트) 필요 → IS 세그먼트 데이터는 FMP Starter에서 못 받을 수 있음. FMP에서 `revenueGeographicSegmentation` 엔드포인트 접근 가능 여부 확인 필요.
- `GrowthStage`: revenue_growth, rd_ratio, capex_ratio → metrics/ 앱에서 계산 가능 ✅
- `CapitalDNA`: buyback, dividend, capex 비율 → CF Statement + BS에서 계산 가능 ✅
- `InsiderSignal`: insider transactions 데이터 필요 → Finnhub `insider-transactions` API 무료 여부 확인 필요 ⚠️

#### Tier B — 반자동 (분기~주 1회)

| 테이블                                 | 역할               | 핵심 필드                                        |
| -------------------------------------- | ------------------ | ------------------------------------------------ |
| `chainsight_company_revenue_structure` | 매출 구조          | symbol, segments (JSONB), geographic_mix (JSONB) |
| `chainsight_company_narrative_tag`     | 뉴스 내러티브 태그 | symbol, tags (JSONB), dominant_narrative         |
| `chainsight_company_event_reaction`    | 이벤트별 주가 반응 | symbol, event_type, avg_reaction, sample_count   |

⚠️ **v1.1 검증 노트**: Tier B는 데이터 소스가 더 까다로움.

- `RevenueStructure`: 10-K에서 segment 추출 필요 → Gemini Flash로 SEC EDGAR 파싱 or FMP에서 segment 데이터 받아야 함. MVP에서는 빈 상태로 시작하고 점진 채워넣기.
- `NarrativeTag`: Marketaux 뉴스에서 LLM 추출 → 실행 가능하나 Phase 2 이후.
- `EventReaction`: earnings/macro 이벤트 전후 주가 변동 계산 → 실행 가능 ✅

#### 관계 발견

| 테이블                           | 역할             | 핵심 필드                                                                                           |
| -------------------------------- | ---------------- | --------------------------------------------------------------------------------------------------- |
| `chainsight_news_event`          | 전용 뉴스 이벤트 | event_id, title, symbols (JSONB), event_type, published_at                                          |
| `chainsight_co_mention_edge`     | 뉴스 동시출현    | symbol_a, symbol_b, co_mention_count, last_co_mention_date                                          |
| `chainsight_price_co_movement`   | 주가 동조 분석   | symbol_a, symbol_b, correlation, period, calculated_at                                              |
| `chainsight_relation_confidence` | 관계 신뢰도 종합 | symbol_a, symbol_b, 6개 소스 bool, source_count, relation_status, confidence_score, synced_to_neo4j |

#### 집약

| 테이블                             | 역할                        | 핵심 필드                                                   |
| ---------------------------------- | --------------------------- | ----------------------------------------------------------- |
| `chainsight_company_chain_profile` | 종합 요약 → Neo4j 투영 원천 | symbol, profile_data (JSONB), neo4j_synced, neo4j_synced_at |

---

## 3. 개발 Phase (트랙 A: 시스템 구축)

### Phase 0: 인프라 기반

> 목표: Neo4j 연결 가능, 테이블 존재, 기본 도구 작동
> 예상 기간: 1~2일
> 의존성: 없음

| 번호   | 작업                          | 산출물                                            | 완료 기준                                             |
| ------ | ----------------------------- | ------------------------------------------------- | ----------------------------------------------------- |
| CS-0-1 | Django migrations 실행 + 검증 | chainsight/ 테이블 13개 생성 확인                 | `python manage.py showmigrations chainsight` 전체 [X] |
| CS-0-2 | Neo4j 연결 레이어 구현        | `chainsight/graph/repository.py`                  | Neo4j 연결 + 간단한 읽기/쓰기 테스트 통과             |
| CS-0-3 | Neo4j 온톨로지 스키마 초기화  | `chainsight/graph/schema.py` + management command | constraint/index 생성 확인                            |

#### CS-0-2 상세: Neo4j 연결 구조

```python
# chainsight/graph/repository.py

from typing import Protocol, List, Dict, Any

class GraphRepository(Protocol):
    """그래프 DB 접근 인터페이스. 백엔드 교체 가능."""
    def get_node(self, ticker: str) -> Dict[str, Any]: ...
    def get_neighbors(self, ticker: str, depth: int = 1,
                      rel_types: List[str] | None = None) -> Dict: ...
    def upsert_node(self, label: str, properties: Dict) -> None: ...
    def upsert_edge(self, from_ticker: str, to_ticker: str,
                    rel_type: str, properties: Dict) -> None: ...
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

| 번호   | 작업                           | 산출물                                     | 완료 기준                                                |
| ------ | ------------------------------ | ------------------------------------------ | -------------------------------------------------------- |
| CS-1-1 | Stock 노드 벌크 로드           | management command `load_stocks_to_neo4j`  | S&P 500 :Stock 노드 500개 확인                           |
| CS-1-2 | Sector/Industry 노드 + 관계    | management command `load_sectors_to_neo4j` | :Sector ~11개, :Industry ~70개, BELONGS_TO 관계 ~1,000개 |
| CS-1-3 | Peer 관계 로드 (Finnhub + FMP) | Celery task `fetch_and_load_peers`         | PEER_OF 2,500~3,500개                                    |

⚠️ **v1.0 대비 변경**: CS-1-3에 있던 "Supply Chain 시드 로드"를 제거함. 6-Phase 데이터 수집 원칙에 따라, MVP 런칭은 PEER_OF + SAME_INDUSTRY만으로 시작하고, Supply Chain은 DC-3(런칭 +2주)에서 추가.

#### Phase 1 완료 시 Neo4j 상태

```
노드: ~580개 (Stock 500 + Sector 11 + Industry 70)
관계: ~4,500개 (BELONGS_TO ~1,000 + PEER_OF ~3,500)

가능한 쿼리 예시:
"AAPL의 1-depth 관계" → peers + 같은 산업 종목
"Technology 섹터 내 모든 종목" → BELONGS_TO_SECTOR 탐색
"NVDA의 peer 중 같은 industry인 종목" → PEER_OF ∩ BELONGS_TO_INDUSTRY
```

★ 이 시점이 최소 데모 가능 지점. 파도타기 핵심 경험은 이것만으로 작동함.

---

### Phase 2: 파생 데이터 계산 파이프라인

> 목표: PostgreSQL에서 기업 프로파일 + 관계 발견 자동 계산
> 예상 기간: 1~2주
> 의존성: Phase 1 완료 + metrics/ 앱 작동

| 번호   | 작업                                   | 산출물                               | 완료 기준                           |
| ------ | -------------------------------------- | ------------------------------------ | ----------------------------------- |
| CS-2-1 | Tier A 계산 tasks (데이터 확보된 것만) | `chainsight/tasks/profile_tasks.py`  | GrowthStage, CapitalDNA 테이블 적재 |
| CS-2-2 | CoMentionEdge 추출                     | `chainsight/tasks/relation_tasks.py` | Marketaux 뉴스에서 동시출현 쌍 추출 |
| CS-2-3 | PriceCoMovement 계산                   | 같은 파일 내 task                    | 90일 rolling correlation 계산       |
| CS-2-4 | RelationConfidence 종합                | 같은 파일 내 task                    | 교차검증 + status 판정              |
| CS-2-5 | CompanyChainProfile 집약               | `chainsight/tasks/sync_tasks.py`     | 프로파일 + 관계 → 집약 테이블       |

⚠️ **v1.1 수정**: CS-2-1에서 Tier A 4개 전부가 아닌 "데이터 확보된 것만" 먼저 구현.

- `GrowthStage`: ✅ metrics/ 데이터로 즉시 가능
- `CapitalDNA`: ✅ CF + BS 데이터로 즉시 가능
- `SensitivityProfile`: ⚠️ segment 데이터 확보 후 (FMP API 확인 필요)
- `InsiderSignal`: ⚠️ Finnhub insider API 확인 후

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

| 번호   | 작업                                   | 산출물                          | 완료 기준                                     |
| ------ | -------------------------------------- | ------------------------------- | --------------------------------------------- |
| CS-3-1 | ChainProfile → Neo4j 속성 동기화       | sync task                       | :Stock 노드에 프로파일 속성 반영              |
| CS-3-2 | RelationConfidence → Neo4j 엣지 동기화 | sync task                       | confirmed 관계만 엣지 생성                    |
| CS-3-3 | GDS 알고리즘 배치                      | `chainsight/tasks/gds_tasks.py` | pagerank, community_id, betweenness 노드 속성 |

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
- Neo4j Community Edition: GDS 무료 사용 가능 (Apache 2.0 라이센스)
- Neo4j AuraDB Free: GDS 미지원
- Self-hosted: neo4j-community + GDS 플러그인 설치

현재 환경 (MacBook self-hosted)에서는 문제없음.
프로덕션 배포 시 GDS 플러그인 포함된 Docker 이미지 사용 필요.

실행 순서 (의존 관계):
1. PageRank → 노드 중요도
2. Louvain Community Detection → 클러스터링
3. Betweenness Centrality → 브릿지 노드 식별
```

---

### Phase 4: API 엔드포인트

> v1.0과 동일. 변경 없음.

| 번호   | 작업            | 엔드포인트                                         | 완료 기준                                       |
| ------ | --------------- | -------------------------------------------------- | ----------------------------------------------- |
| CS-4-1 | 그래프 탐색 API | `GET /api/stocks/{symbol}/chainsight/graph/`       | depth 파라미터로 N-depth 조회, nodes+edges 응답 |
| CS-4-2 | 탐색 제안 API   | `GET /api/stocks/{symbol}/chainsight/suggestions/` | 맥락화된 카테고리 목록 반환                     |
| CS-4-3 | 경로 탐색 API   | `GET /api/chainsight/trace/`                       | 두 종목 간 최단 경로 반환                       |

API 응답 형식은 v1.0 섹션 참조 (변경 없음).

---

### Phase 5: 프론트엔드

> v1.0과 동일. 변경 없음.

| 번호   | 작업                   | 산출물                                      | 완료 기준                       |
| ------ | ---------------------- | ------------------------------------------- | ------------------------------- |
| CS-5-1 | 그래프 시각화 컴포넌트 | `components/chainsight/GraphView.tsx`       | Spotlight 모드 + lazy expansion |
| CS-5-2 | AI 가이드 탐색 UI      | `components/chainsight/SuggestionCards.tsx` | 카테고리 선택 → 그래프 필터링   |
| CS-5-3 | Chain Trace 시각화     | `components/chainsight/TraceView.tsx`       | 경로 하이라이트 + 단계별 설명   |
| CS-5-4 | 종목 상세 페이지 연계  | 기존 종목 상세 수정                         | Chain Sight 미니 뷰 임베드      |

---

## 4. 데이터 수집 방안 (트랙 B: 그래프 데이터 확보)

### 4.1 현재 API 스택 + 접근 가능 여부

```
확정된 API 스택 (현재 사용 중):
  FMP Starter     $22/월  — Profile, Peers, Quote, Financials (US, Annual)
  Finnhub Free    $0/월   — Peers, News, Quote, Sentiment
  Marketaux       $9/월   — News + Entity Tagging
  FRED            $0/월   — 거시경제 지표
  yfinance        $0/월   — 지수, 섹터 ETF, 환율
  ─────────────────────────
  합계:           $31/월
```

#### 엔드포인트별 접근 가능 여부 (교차검증 결과)

| 엔드포인트                                   | 상태                | 근거                                                                      |
| -------------------------------------------- | ------------------- | ------------------------------------------------------------------------- |
| Finnhub Peers (`/stock/peers`)               | ✅ 확인됨 (무료)    | 실사용 중, 문서 명시                                                      |
| FMP Profile (`/stable/profile`)              | ✅ 확인됨 (Starter) | 실사용 중, sector/industry 포함                                           |
| FMP Stock Peers (`/stable/stock-peers`)      | ⚠️ 미확인           | Starter 접근 여부 테스트 필요                                             |
| Finnhub Supply Chain (`/stock/supply-chain`) | ❌ 불가 추정        | "alternative data" 카테고리, Premium 이동 전력 있음. 실제 403 가능성 높음 |
| Finnhub ETF Holdings (`/etf/holdings`)       | ⚠️ 미확인           | 문서에 존재하나 플랜 제한 미확인. 테스트 필요                             |
| FMP ETF Holdings (`/stable/etf-holder`)      | ❌ 불가 추정        | Starter에서 403/404, Professional 이상 필요 추정                          |
| Finnhub Insider Transactions                 | ⚠️ 미확인           | Tier A InsiderSignal 계산에 필요                                          |
| FMP Revenue Segmentation                     | ⚠️ 미확인           | Tier A SensitivityProfile 계산에 필요                                     |

#### 🚨 착수 전 반드시 실행할 API 테스트

```
아래 4개를 실제 호출해서 200/403 여부 확인 (Claude Code 프롬프트 이미 작성됨):
1. FMP Stock Peers → Starter에서 되면 PEER_OF 보강
2. Finnhub Supply Chain → 무료면 DC-6 불필요 (대행운)
3. Finnhub ETF Holdings → 무료면 DC-2 간단 해결
4. Finnhub Insider Transactions → 무료면 CS-2-1 InsiderSignal 바로 구현
```

### 4.2 데이터 수집 6-Phase 로드맵

핵심 원칙: **PEER_OF + SAME_INDUSTRY만으로도 파도타기는 작동한다. 나머지는 성장하면서 붙인다.**

```
DC-1 (MVP 런칭)
│  PEER_OF + SAME_INDUSTRY ~6,500개만으로 런칭
│  Chain Sight의 "파도타기" 핵심 경험은 이것만으로 완전히 동작
│  비용: $0 추가
│
DC-2 (런칭 +1주)
│  ETF Holdings 추가 → HAS_THEME 관계 생성
│  13 ETF × top 30 종목 = ~390개 HAS_THEME 관계
│  비용: $0, 작업 30분~반나절
│
DC-3 (런칭 +2주)
│  수동 시드 JSON → Supply Chain
│  Mag7 + 반도체 + EV + 클라우드 핵심 50~100종목
│  ~300~500개 SUPPLIES_TO / CUSTOMER_OF 관계
│  비용: $0, 작업 2시간
│
DC-4 (런칭 +3주)
│  Gemini Flash 배치 추출 → 나머지 S&P 500
│  ~400~600개 Supply Chain 관계 추가 (검증 통과분)
│  비용: ~$0.03~$5 (1회성)
│
DC-5 (런칭 +1개월~)
│  Marketaux 뉴스 자연 축적
│  CO_MENTIONED에서 공급망 관계 자연 발견
│  월 ~50~80개 Supply Chain, 월 ~200~300개 CO_MENTIONED
│  비용: $0 추가 (기존 Marketaux $9 내)
│
DC-6 (수익화 이후)
│  유료 사용자 매출 $200/월 이상 달성 시
│  Finnhub Supply Chain API ($200/월) 결제
│  가장 정확하고 포괄적인 데이터로 업그레이드
│  기존 수동 시드 + Gemini 데이터와 병합 (Finnhub 우선)
```

#### Phase별 누적 관계 수

| Phase | 시점      | PEER/INDUSTRY | Supply Chain | ETF Theme | CO_MENTIONED | 누적 총  |
| ----- | --------- | ------------- | ------------ | --------- | ------------ | -------- |
| DC-1  | MVP 런칭  | ~6,500        | 0            | 0         | 0            | ~6,500   |
| DC-2  | +1주      | ~6,500        | 0            | ~390      | ~50          | ~6,940   |
| DC-3  | +2주      | ~6,500        | ~500         | ~390      | ~100         | ~7,490   |
| DC-4  | +3주      | ~6,500        | ~1,100       | ~390      | ~200         | ~8,190   |
| DC-5  | +3개월    | ~6,500        | ~1,340       | ~390      | ~1,000       | ~9,230   |
| DC-6  | 수익화 후 | ~6,500        | ~2,500+      | ~390      | ~2,000+      | ~11,390+ |

### 4.3 DC-1 상세: 확보 완료 데이터 (Peers + Industry)

#### Finnhub Peers

```
엔드포인트: GET https://finnhub.io/api/v1/stock/peers?symbol={SYMBOL}&token={KEY}
비용: $0 (무료)
Rate limit: 60회/분
응답 예시: ["MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"]

수집 전략:
- S&P 500 전체 (500종목 × 1호출 = 500호출)
- Rate limit 고려 → ~9분 소요
- Redis 캐시 TTL: 7일 (peers는 자주 안 바뀜)

저장:
- Neo4j: PEER_OF 관계 (양방향, source="finnhub")
- PostgreSQL: 원본 응답 캐시 (chainsight_relation_confidence.has_co_mention 등에 반영)

예상 관계: ~2,500개 (종목당 평균 5개 peer × 500종목, 중복 제거)
```

#### FMP Profile → Sector/Industry

```
엔드포인트: GET https://financialmodelingprep.com/stable/profile?symbol={SYMBOL}&apikey={KEY}
비용: Starter($22/월) 내 포함
Rate limit: 300회/분
응답에서 사용하는 필드: sector, industry, mktCap, companyName

수집 전략:
- S&P 500 전체 (500호출, ~2분)
- 응답에서 sector, industry 추출
- 같은 industry인 종목끼리 Neo4j 내부에서 관계 생성

저장:
- Neo4j: :Sector 노드 (~11개), :Industry 노드 (~70개)
- Neo4j: BELONGS_TO_SECTOR, BELONGS_TO_INDUSTRY 관계 (~1,000개)
- Neo4j 내부 쿼리로 SAME_INDUSTRY 관계 도출 (~3,000개)
  ※ 실제 엣지로 저장하지 않고, 쿼리 시 "같은 Industry에 BELONGS_TO인 종목" 패턴으로 처리
  ※ industry 내 종목이 20개 넘으면 시총 상위 20개로 제한

예상 관계: BELONGS_TO ~1,000개 + 쿼리 기반 SAME_INDUSTRY ~3,000개
```

#### FMP Stock Peers (보조, 미확인)

```
엔드포인트: GET https://financialmodelingprep.com/stable/stock-peers?symbol={SYMBOL}&apikey={KEY}
비용: Starter 내 포함 여부 미확인
테스트 필요: 200이면 Finnhub Peers와 병합 (source="fmp"), 403이면 skip

병합 로직:
- Finnhub과 FMP 양쪽에 나오는 peer → confidence 상승
- 한쪽에만 나오는 peer → confidence 기본값
```

### 4.4 DC-2 상세: ETF Holdings → HAS_THEME

#### 의사결정 순서 (최단거리)

```
1. Finnhub etfs-holdings 호출 테스트 → 되면 끝 ($0)
2. 안 되면 → 운용사 CSV 반자동 다운로드 ($0)
3. CUSIP→Ticker 매핑 필요 시 → 상위 30개만 OpenFIGI ($0)
4. 장기적으로 → SEC N-PORT 파싱 서비스 고려
```

#### 대상 ETF 목록 (13개)

| ETF  | 테마                  | 운용사      |
| ---- | --------------------- | ----------- |
| QQQ  | Big Tech / Nasdaq 100 | Invesco     |
| SOXX | 반도체                | iShares     |
| ARKK | 혁신 기술             | ARK         |
| ARKG | 유전체학              | ARK         |
| ICLN | 클린에너지            | iShares     |
| LIT  | 리튬/배터리           | Global X    |
| BOTZ | 로봇/AI               | Global X    |
| HACK | 사이버보안            | ETFMG       |
| XBI  | 바이오텍              | SPDR        |
| KWEB | 중국 인터넷           | KraneShares |
| DRIV | 자율주행/EV           | Global X    |
| XLF  | 금융                  | SPDR        |
| XLE  | 에너지                | SPDR        |

#### 옵션 A: Finnhub ETF Holdings (최우선 테스트)

```
엔드포인트: GET https://finnhub.io/api/v1/etf/holdings?symbol={ETF}&token={KEY}
테스트 방법: 13개 ETF 각각 호출 → 200이면 채택
200일 경우:
  - 13호출로 모든 holdings 확보
  - ticker가 바로 나오면 매핑 불필요
  - Celery task로 월 1회 자동 갱신
  - management command로 초기 로드
```

#### 옵션 B: 운용사 CSV 반자동 다운로드 (Finnhub 실패 시)

```
접근 방식:
  HTML 스크래핑이 아닌, 운용사가 제공하는 공식 CSV 다운로드 URL을 직접 호출.
  CSV 포맷은 HTML보다 훨씬 안정적 (사이트 리디자인에 영향 안 받음).

운용사별 CSV URL 패턴:
  iShares: https://www.ishares.com/us/products/{FUND_ID}/fund/1467271812596.ajax?fileType=csv
  SPDR:    https://www.ssga.com/us/en/intermediary/etfs/library-content/products/fund-data/etfs/us/holdings-daily-us-en-{TICKER}.xlsx
  ARK:     https://ark-funds.com/wp-content/uploads/funds-etf-csv/ARK_{TYPE}_ETF_{TICKER}_HOLDINGS.csv
  Global X: 공식 페이지에서 CSV 제공

구현:
  Celery task (월 1회):
    1. 정해진 URL에서 CSV 다운로드
    2. row count 체크 (0줄이면 알람)
    3. 해시 비교 (변경 없으면 skip)
    4. 파싱 → ticker + weight 추출
    5. Neo4j HAS_THEME 관계 업데이트

CUSIP→Ticker 매핑 (필요 시):
  대부분의 운용사 CSV는 ticker를 제공하지만, CUSIP만 있는 경우:
  - 상위 30개만 OpenFIGI API로 매핑 (무료, 100req/sec)
  - GET https://api.openfigi.com/v3/mapping
  - 13 ETF × 30 = 390건 → 4초 소요
```

#### 옵션 C: 테마 2단 구조 (Holdings 부족 시 보완)

```
ETF Holdings가 완전하지 않을 때를 대비한 보완 구조:

Tier A — 확정 테마 (Holdings 기반): confidence = high
  ETF에 실제로 포함된 종목 → HAS_THEME 관계

Tier B — 추정 테마 (Holdings 없이): confidence = medium/low
  종목의 industry 키워드 + ETF 이름/설명으로 테마 매칭
  예: industry="Semiconductors" → 반도체 테마 추정
  UI에서 ✅(확정) / ⚠️(추정)으로 구분

이렇게 하면 ETF Holdings가 부족해도 테마 탐색 카테고리가 빠지지 않음.
```

### 4.5 DC-3 상세: 수동 시드 JSON (Supply Chain)

```
대상: 잘 알려진 대형주 50~100개의 공급망 관계
작업 시간: ~2시간
산출물: data/seed/supply_chain.json
정확도: 100% (공개적으로 알려진 사실만)

JSON 구조:
{
  "version": "1.0",
  "updated": "2026-04-XX",
  "clusters": {
    "magnificent_7": {
      "description": "Mag7 핵심 공급망",
      "relationships": [
        {"from": "TSM", "to": "AAPL", "type": "SUPPLIES_TO",
         "category": "semiconductor_foundry", "confidence": 0.95},
        {"from": "AAPL", "to": "TSM", "type": "CUSTOMER_OF",
         "category": "semiconductor_foundry", "confidence": 0.95}
      ]
    },
    "semiconductor_chain": { ... },
    "ev_battery": { ... },
    "cloud_infrastructure": { ... }
  }
}

클러스터별 예상 관계 수:
  Magnificent 7 공급망:   ~80개
  반도체 체인 (TSM/ASML/LRCX/KLAC/AMAT): ~60개
  EV/배터리 (TSLA/RIVN + ALB/SQM/PANASONIC): ~50개
  클라우드 인프라 (AMZN/MSFT/GOOGL + CSCO/HPE): ~50개
  기타 대형주 주요 관계: ~60개
  합계: ~300~500개

로딩 방법:
  python manage.py load_supply_chain_seed --file=data/seed/supply_chain.json
  중복 체크: Neo4j MERGE로 idempotent하게 처리
```

### 4.6 DC-4 상세: Gemini Flash 배치 추출

```
입력: S&P 500 중 수동 시드에 없는 ~420개 종목의 FMP company description
LLM: Gemini 2.5 Flash (Structured Output)

프롬프트:
  "다음 기업 설명에서 supplier와 customer를 추출하세요.
   각 관계에 대해 ticker, 관계 유형, confidence(high/medium/low)를 제공하세요.
   확실하지 않은 관계는 confidence=low로 표시하세요."

검증 레이어 (필수):
  1. FMP S&P 500 목록에서 ticker 실존 확인
  2. confidence=low 제거
  3. 자기참조 필터링 (A→A)
  4. 비상장 기업 매칭 제거
  5. 관계 방향 오류 검출 (프롬프트에 방향 명시)

비용 계산:
  입력: ~420종목 × ~350토큰 = ~147,000 토큰
  출력: ~420종목 × ~100토큰 = ~42,000 토큰
  Gemini 2.5 Flash: 입력 $0.15/M + 출력 $0.60/M
  합계: ~$0.05 (무료 티어로도 충분)

예상 결과:
  추출: ~600~800개 raw 관계
  검증 후 생존: ~400~600개
  정확도 (검증 통과분): ~90%

실행 스크립트: chainsight/scripts/gemini_supply_chain_extract.py
결과 저장: data/generated/gemini_supply_chain.json → Neo4j 로드
```

### 4.7 DC-5 상세: 뉴스 자연 축적

```
소스: Marketaux API ($9/월, 이미 사용 중)
방식: 기존 뉴스 파이프라인의 entity 태깅에서 동시 출현 종목쌍 추출

로직:
  뉴스 기사 하나에 2개 이상 종목이 태깅되어 있으면:
    → 모든 쌍(pair)에 대해 CoMentionEdge 카운트 증가
    → 예: 기사에 [AAPL, TSM, NVDA] → (AAPL,TSM), (AAPL,NVDA), (TSM,NVDA) 3쌍

Celery task: chainsight.tasks.extract_co_mentions (일 1회)

Supply Chain 발견 로직:
  CO_MENTIONED 중 특정 패턴이면 Supply Chain 후보로 추천:
  - 동일 기사에서 "supplier", "supply", "customer", "order" 등 키워드 동시 존재
  - 해당 쌍의 CO_MENTIONED count가 5회 이상 누적
  → RelationConfidence 테이블에 has_co_mention=True로 기록

예상 축적량:
  월 ~200~300개 CO_MENTIONED 쌍
  그 중 Supply Chain 관련: ~20~30% → 월 ~50~80개 후보
```

### 4.8 DC-6 상세: 유료 API 업그레이드 (수익화 이후)

```
트리거 조건:
  - 유료 사용자 매출 ≥ $200/월
  - 또는 그래프 커버리지가 사용자 기대에 못 미칠 때

Finnhub Supply Chain API:
  엔드포인트: GET /stock/supply-chain?symbol={SYMBOL}
  비용: ~$200/월 (개인 Premium 또는 Pro)
  데이터: 공식 공급망 관계, 매출 비중, 지리적 분포 포함
  예상 관계: ~1,500개 (S&P 500 기준)

병합 전략:
  Finnhub 데이터를 최상위 우선순위로 설정
  기존 수동 시드 / Gemini 추출 데이터는 Finnhub에 없는 것만 유지
  RelationConfidence 테이블에 source="finnhub_premium" 추가

선택적 추가: Earnings Call Transcript
  FMP Professional 이상에서 접근 가능
  Gemini Flash로 transcript에서 supplier/customer 추출
  수동 시드보다 최신 + 명시적 관계 발견 가능
  단, 토큰 비용 50~150배 증가 → 주요 20개 종목만 선별 실행
```

### 4.9 데이터 수집 비용 요약

| 항목                  | 초기 비용    | 월 비용                          | 비고                |
| --------------------- | ------------ | -------------------------------- | ------------------- |
| DC-1 Peers + Industry | $0           | $31 (기존 FMP+Finnhub+Marketaux) | 이미 구독 중        |
| DC-2 ETF Holdings     | $0           | $0                               | Finnhub 무료 or CSV |
| DC-3 수동 시드        | $0           | $0                               | 2시간 작업          |
| DC-4 Gemini Flash     | ~$0.05 (1회) | $0                               | 무료 티어 가능      |
| DC-5 뉴스 축적        | $0           | $0                               | 기존 Marketaux 내   |
| DC-6 Finnhub Premium  | -            | $200                             | 수익화 이후         |
| **MVP 합계**          | **~$0.05**   | **$31**                          |                     |

---

## 5. 마일스톤 요약

```
M0 (CS Phase 0 완료): "Neo4j 연결됨, 테이블 있음"
  → 데모 불가, 하지만 이후 모든 작업의 전제

M1 (CS Phase 1 + DC-1 완료): "그래프에 데이터가 있음"
  → PEER_OF + SAME_INDUSTRY ~6,500개
  → Neo4j Browser에서 Cypher로 관계 탐색 가능
  ★ 최소 데모 가능 지점 — 파도타기 핵심 경험 확인

M1.5 (DC-2 + DC-3 완료): "관계가 풍부해짐"
  → +ETF Theme ~390개 + Supply Chain ~500개 = ~7,390개
  → 공급망 + 테마 탐색 카테고리 활성화

M2 (CS Phase 2 완료): "자동 계산 파이프라인 작동"
  → 기업 프로파일 + 관계 발견이 자동으로 돌아감
  → DC-4 (Gemini Flash) 실행으로 Supply Chain ~1,100개 도달

M3 (CS Phase 3 완료): "Neo4j가 풍부해짐"
  → GDS 알고리즘으로 중요도/클러스터 식별
  → API 응답에 pagerank, community 정보 포함

M4 (CS Phase 4 완료): "API 완성"
  → 프론트엔드 개발 시작 가능

M5 (CS Phase 5 완료): "사용자 경험 가능"
  → Chain Sight MVP 릴리즈
  → DC-5 자연 축적이 시간이 지남에 따라 그래프를 풍부하게 함
```

---

## 6. 미해결 사항 + 선행 확인 필요 사항

### 🚨 착수 전 선행 확인 (API 테스트)

| 테스트                           | 결과별 영향                                       | 우선순위 |
| -------------------------------- | ------------------------------------------------- | -------- |
| FMP Stock Peers (Starter 접근)   | 200 → DC-1 보강 / 403 → Finnhub만 사용            | ★★★      |
| Finnhub Supply Chain (무료 접근) | 200 → DC-6 불필요! / 403 → 6-Phase 유지           | ★★★      |
| Finnhub ETF Holdings (무료 접근) | 200 → DC-2 간단 해결 / 403 → CSV 방식             | ★★★      |
| Finnhub Insider Transactions     | 200 → CS-2-1 InsiderSignal 구현 / 403 → 보류      | ★★       |
| FMP Revenue Segmentation         | 200 → CS-2-1 SensitivityProfile 구현 / 403 → 보류 | ★★       |

### 미해결 의사결정

| 항목                               | 상태                                        | 결정 시점          |
| ---------------------------------- | ------------------------------------------- | ------------------ |
| ETF Holdings 소싱 방식 최종        | API 테스트 결과에 따라 결정                 | CS-0 완료 직후     |
| Theme 노드 생성 방식               | ETF 기반 (DC-2) + AI 추출 (추후)            | DC-2 진입 시       |
| Tier A/B 중 데이터 확보 안 되는 것 | API 테스트 후 가능한 것만 먼저              | CS-2 진입 시       |
| GDS 프로덕션 배포                  | Self-hosted에서는 OK, 클라우드 시 별도 검토 | CS-3 진입 시       |
| 모바일 그래프 UX 상세              | Spotlight 모드 개념만 확정                  | CS-5 진입 시       |
| 다른 서비스 연계 API 구현          | 인터페이스 설계만 완료                      | 각 서비스 MVP 이후 |

---

## 7. 참고 링크 (과거 대화)

---

## 부록: 현재 구현 현황 대조 (2026-04-01 기준)

> 로드맵 v1.1과 실제 코드베이스의 차이를 분석하고, 수정/보완 사항을 기록한다.
> 이 섹션은 CS-0 착수 전 반드시 읽고 확인할 것.

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

**총 12개 테이블. 로드맵의 13개 중 12개 완성. 나머지 1개 차이:**

로드맵에서는 CompanyChainProfile.profile_data를 JSONB 단일 필드로 제안했으나, 현재 구현은 30개 개별 필드로 되어 있음.
→ **현재 구조 유지 결정**. 이유: 개별 필드가 SQL 쿼리(WHERE, ORDER BY)에 직접 사용 가능하고, Django ORM 필터링이 JSONB보다 훨씬 단순. JSONB는 스키마 유연성이 장점이지만 1인 개발에서는 명시적 필드가 유지보수에 유리.

### B. 기존 serverless 앱 Chain Sight 코드 (제거 대상)

**판단: 제로베이스 재구축. 기존 코드는 CS-0 착수 시 제거.**

| 위치 | 파일/코드 | 역할 | 처리 |
|------|----------|------|------|
| serverless/models.py | StockRelationship | 관계 저장 | ❌ 제거 → RelationConfidence로 대체 |
| serverless/models.py | CategoryCache | AI 카테고리 캐시 | ❌ 제거 → CompanyNarrativeTag로 대체 |
| serverless/models.py | ETFProfile, ETFHolding, ThemeMatch | ETF 데이터 | ⚠️ DC-2까지 보류, 이후 chainsight로 이전 검토 |
| serverless/views.py | chain_sight_*_api (6개 뷰) | Chain Sight API | ❌ 제거 → CS-4에서 새로 구현 |
| serverless/services/ | chain_sight_stock_service.py | 메인 서비스 | ❌ 제거 |
| serverless/services/ | category_generator.py | 카테고리 생성 | ❌ 제거 |
| serverless/services/ | relationship_service.py | 관계 조회 | ❌ 제거 |
| serverless/urls.py | chain-sight/* 라우트 | URL 라우팅 | ❌ 제거 |

**제거 이유:**
1. 기존 코드는 serverless 앱에 Chain Sight 로직이 섞여 있어서 앱 분리 원칙에 위배
2. StockRelationship 모델이 chainsight/의 RelationConfidence와 역할 중복
3. 기존 코드는 Neo4j fallback 구조인데, 로드맵은 Neo4j를 primary로 사용
4. CategoryCache(LLM 캐시)는 CompanyNarrativeTag.theme_tags로 대체 가능

**제거 시점:** CS-0-1 착수 시 일괄 제거. 단, ETF 관련 모델(ETFProfile/ETFHolding/ThemeMatch)은 DC-2 시점까지 보류.

### C. 프론트엔드 기존 코드 (제거 대상)

**판단: 전체 제거 후 CS-5에서 제로베이스 재구축.**

| 위치 | 파일 수 | 역할 | 처리 |
|------|---------|------|------|
| frontend/components/chain-sight/ | 8개 | Explorer, CategorySelector, StockGrid 등 | ❌ 전체 제거 |
| frontend/hooks/useChainSight*.ts | 3개 | 카테고리/종목/ETF hooks | ❌ 전체 제거 |
| frontend/services/chainSightService.ts | 1개 | API 클라이언트 | ❌ 제거 |
| frontend/types/chainSight.ts | 1개 | 타입 정의 | ❌ 제거 |
| frontend/utils/relationshipTagStyles.ts | 1개 | 태그 스타일 | ❌ 제거 |
| frontend/app/chain-sight/page.tsx | 1개 | 진입점 (리다이렉트) | ❌ 제거 |

**제거 이유:**
1. 기존 UI는 serverless API 기반 — Neo4j 기반 API(CS-4)와 호환 불가
2. 기존 타입(ChainSightCategory, ChainSightStock)이 로드맵의 온톨로지 노드(:Stock, :Sector)와 구조가 다름
3. 기존 컴포넌트는 "카테고리 선택 → 종목 그리드" 패턴인데, 로드맵은 "그래프 시각화 → Spotlight 탐색" 패턴
4. 제로베이스가 기존 코드에 맞추는 것보다 빠름 (기존 코드 학습 비용 > 새로 작성 비용)

**제거 시점:** CS-5 착수 시. 단, CS-5 이전에는 기존 UI가 종목 상세 페이지에서 "Chain Sight" 탭으로 동작하므로 유지.

### D. graph_analysis/ 앱과의 관계

**판단: 독립 유지. 겹치지 않음.**

| 항목 | graph_analysis | chainsight |
|------|---------------|------------|
| 목적 | 가격 상관관계 (워치리스트 기반) | 사업/산업/뉴스 기반 관계 발견 |
| 핵심 모델 | CorrelationEdge, CorrelationAnomaly | RelationConfidence, CoMentionEdge |
| 데이터 소스 | DailyPrice | 뉴스, 재무제표, ETF, LLM |
| 사용자 인터페이스 | 워치리스트 상관계수 히트맵 | 종목 중심 그래프 탐색 |

→ 두 앱은 **완전히 독립적**. 향후 chainsight의 PriceCoMovement와 graph_analysis의 CorrelationEdge가 데이터를 공유할 수 있지만, 현재는 별도 계산 유지.

### E. 1차 검증(validation)과의 연계 확인

**현재 연계 포인트:**
1. metrics/CompanyMetricSnapshot → chainsight Tier A 계산의 원천 데이터 ✅
2. validation/CategorySignal → CompanyChainProfile의 score_profitability 등에 반영 예정 (CS-2-5)
3. validation/PeerPreset → Phase 6 thematic 프리셋이 CompanyNarrativeTag.theme_tags 의존

**연계 시 주의사항:**
- chainsight 모델은 validation 모델을 직접 import하지 않고, 집약 시점(CS-2-5)에서만 읽기
- 양방향 import는 순환 참조 위험 → 서비스 레이어에서만 교차 참조

### F. 수정/보완 이력

| 날짜 | 작업 | 이유 |
|------|------|------|
| 2026-04-01 | CompanyChainProfile에 neo4j_synced, neo4j_synced_at 필드 추가 | CS-3-1 Delta Sync에 필수. 로드맵에 명시되어 있으나 모델에 누락되어 있었음 |
| 2026-04-01 | CoMentionEdge, PriceCoMovement, RelationConfidence 모델 신규 생성 | CS-2-2~CS-2-4에서 사용하는 관계 발견 테이블. 로드맵 섹션 2.5에 명시되어 있으나 PostgreSQL 모델이 생성되지 않았음 |
| 2026-04-01 | 기존 serverless Chain Sight 코드 제거 방침 결정 | 로드맵의 chainsight/ 앱 중심 구조와 충돌. CS-0 착수 시 일괄 제거 후 제로베이스 재구축 |
| 2026-04-01 | 기존 프론트엔드 Chain Sight 코드 제거 방침 결정 | serverless API 기반 → Neo4j API 기반 전환. CS-5에서 제로베이스 재구축 |
| 2026-04-01 | CompanyChainProfile.profile_data JSONB → 현재 개별 필드 구조 유지 결정 | SQL 쿼리 직접 사용 가능, Django ORM 필터링 용이, 1인 개발 유지보수 우선 |

---

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
