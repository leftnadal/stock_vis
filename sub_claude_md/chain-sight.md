# Chain Sight (연관 종목 발견 시스템)

## Phase 2.2: Chain Sight DNA (스크리너 연관 종목)

### 연관 종목 발견 방식

| 방식 | 설명 | 알고리즘 |
|------|------|----------|
| **섹터 피어** | 같은 섹터의 유사 종목 | 동일 섹터 + 펀더멘탈 유사도 계산 |
| **펀더멘탈 유사** | PER, ROE, 시가총액 유사 | 평균 메트릭 ±20% 범위 |
| **AI 인사이트** | LLM 기반 관계 설명 (옵션) | Gemini 2.5 Flash |

### 유사도 계산

- PER, ROE, 시가총액, 이익률 4개 지표 평균
- 임계값: 섹터 피어 (제한 없음), 펀더멘탈 유사 (0.5+)
- 캐시: 1시간 TTL

### 테스트: `tests/serverless/test_chain_sight_service.py` (14개)

---

## Chain Sight Stock (개별 종목 연관 탐색)

### 모델

- **StockRelationship**: PEER_OF, SAME_INDUSTRY, CO_MENTIONED, SUPPLIED_BY, CUSTOMER_OF
- **CategoryCache**: 카테고리별 관련 종목 캐시

### 서비스

- **RelationshipService**: 관계 CRUD
- **CategoryGenerator**: 카테고리 자동 생성 (suppliers, customers 포함)
- **ChainSightStockService**: Neo4j 우선, PostgreSQL fallback 하이브리드 조회

### API

- `GET /api/v1/serverless/chain-sight/stock/{symbol}` - 종목 연관 탐색
- `GET /api/v1/serverless/chain-sight/stock/{symbol}/category/{id}` - 카테고리별 조회

---

## Phase 3: ETF Holdings 자동화

### 개요

ETF Holdings 기반 테마 관계를 자동 수집. 운용사 공식 CSV/XLSX에서 직접 다운로드 (비용 $0).

### ETF 자동화 현황

| Tier | 자동화 | 수동 필요 | 총 |
|------|--------|----------|-----|
| Tier 1 (섹터) | 11개 | 0개 | 11개 |
| Tier 2 (테마) | 4개 | 6개 | 10개 |
| **합계** | **15개** | **6개** | **21개** |

### 운용사별 파서

| 운용사 | 파서 | 형식 | ETF 예시 |
|--------|------|------|---------|
| State Street (SPDR) | `spdr` | XLSX | XLK, XLV, XLF 등 |
| iShares | `ishares` | CSV | SOXX |
| GlobalX | `globalx` | CSV | BOTZ, LIT |
| ARK Invest | `ark` | CSV | ARKK, ARKG (수동) |
| Invesco | `invesco` | CSV | TAN, KWEB (수동) |

### 수동 수집 필요 ETF

ARKK, ARKG (Cloudflare 차단), TAN, KWEB (403 Forbidden), HACK (서버 연결 실패), BETZ (PDF만 제공)

```bash
python manage.py import_etf_csv ARKK /path/to/ARKK_holdings.csv --parser ark
```

### 모델

- **ETFProfile**: ETF 프로필
- **ETFHolding**: Holdings (ticker, weight)
- **ThemeMatch**: Tier A (high), Tier B (medium), Tier B+ 승격

### 자동화 스케줄 (config/celery.py)

- `sync_etf_holdings`: 매주 월요일 06:00 EST (`config/celery.py`)
- 실패 시 이메일: goid545@naver.com, jinie545@gmail.com

### 주요 파일

| 파일 | 역할 |
|------|------|
| `serverless/services/etf_csv_downloader.py` | CSV/XLSX 다운로드 및 파싱 |
| `serverless/tasks.py` | Celery 태스크 |
| `serverless/management/commands/import_etf_csv.py` | 수동 임포트 |
| `frontend/app/chain-sight/page.tsx` | Chain Sight 전용 페이지 |

### 테스트

- `test_etf_csv_downloader.py`: 27개
- `test_theme_matching_service.py`: 31개
- `test_csv_url_resolver.py`: 28개

---

## Phase 4: Supply Chain (공급망)

### 아키텍처

- **SEC EDGAR Client**: CIK 조회, 10-K 다운로드, Item 1A 추출 (`api_request/sec_edgar_client.py`)
- **Supply Chain Parser**: Regex 패턴 기반 고객/공급사 추출 (`serverless/services/supply_chain_parser.py`)
- **Supply Chain Service**: 동기화 파이프라인, PostgreSQL + Neo4j 저장 (`serverless/services/supply_chain_service.py`)

### 관계 타입

- SUPPLIED_BY, CUSTOMER_OF (StockRelationship 모델)
- 신뢰도: high (10%+ 매출), medium-high (qualifier), medium (단순 언급)

### 스케줄: 매월 15일 03:00 EST 배치 동기화

### 테스트: 54개 (SEC EDGAR 12개, Parser 24개, Service 18개)

---

## Phase 5: LLM Relation Extraction (Gemini)

### 모델

- **LLMExtractedRelation**: 30일 TTL, 5가지 관계 타입, 신뢰도 레벨

### 관계 타입

ACQUIRED, INVESTED_IN, PARTNER_OF, SPIN_OFF, SUED_BY

### 서비스

- **RelationPreFilter**: Regex 사전 필터링 (~80% LLM 호출 절감)
- **SymbolMatcher**: 회사명 → 티커 매칭 (100+ 하드코딩 + DB)
- **LLMRelationExtractor**: Gemini 2.5 Flash 기반 관계 추출

### 비용: 사전 필터링 + 배치 + 캐싱으로 월 ~$5

### 테스트: 70개 (PreFilter 25, SymbolMatcher 26, Extractor 19)

---

## Neo4j 온톨로지

- **Neo4jChainSightService**: 노드/관계 CRUD, N-depth 그래프 탐색
- **하이브리드 조회**: Neo4j 우선, PostgreSQL fallback
- **그래프 API**: `/chain-sight/graph/{symbol}`, `/chain-sight/graph/stats`
- **마이그레이션**: `python manage.py migrate_chain_sight_to_neo4j --all`
- **테스트**: 19개 (18 passed, 1 skipped)

---

---

## Phase 6: 키워드 Enrichment + 뉴스 패턴 매칭

### 구현 내용

- **관계 태그 표시** (Phase 6A): RelationshipTagBadge 컴포넌트
- **뉴스 패턴 매칭** (Phase 6B): NewsRelationMatcher 서비스
- **클릭 트래킹** (Phase 6C): 사용자 행동 Edge Weight
- **키워드 Enrichment** (Phase 6D): Gemini로 관계 키워드 사전 생성

### 서비스

- **RelationshipKeywordEnricher** (`serverless/services/relationship_keyword_enricher.py`): 관계별 키워드 3개 생성
- 저장: `StockRelationship.context["keywords"]`
- 스케줄: 매일 05:30 EST

### 관련 파일

- `serverless/services/news_relation_matcher.py`
- `serverless/services/relationship_keyword_enricher.py`
- `frontend/components/chain-sight/RelationshipTagBadge.tsx`

---

## Phase 7: Institutional Holdings (SEC 13F)

### 모델

- **InstitutionalHolding**: 기관 보유 현황 (CIK, 종목, 주식수, 가치)

### 관계 타입

- **HELD_BY_SAME_FUND**: 동일 기관 보유 종목 간 관계

### 서비스

- **InstitutionalHoldingsService** (`serverless/services/institutional_holdings_service.py`): 13F 수집 + 관계 생성
- **CUSIPMapper** (`serverless/services/cusip_mapper.py`): CUSIP → 티커 변환

### API

- `GET /institutional/<symbol>` - 기관 보유 현황
- `GET /institutional/<symbol>/peers` - 같은 펀드 보유 종목
- `POST /institutional/sync` - 수동 동기화

### 스케줄: 분기별 (2/5/8/11월 16일)

---

## Phase 8: Regulatory + Patent Network

### 8.1 Regulatory (규제 공유)

- **RegulatoryService** (`serverless/services/regulatory_service.py`)
- 8개 규제 카테고리: 반독점, FDA, 중국 제재, 데이터 프라이버시 등
- 관계 타입: **SAME_REGULATION**
- 소스: 뉴스 키워드 + SEC 8-K + Gemini LLM
- 스케줄: 주간 (월요일 04:00)

### 8.2 Patent Network (특허)

- **USPTOClient** (`serverless/services/uspto_client.py`): USPTO PatentsView API
- **PatentNetworkService** (`serverless/services/patent_network_service.py`)
- 관계 타입: **PATENT_CITED**, **PATENT_DISPUTE**
- 스케줄: 월간 (1일 04:30)

### 비용: $0 (SEC + USPTO 모두 무료)

---

## 로드맵

상세: `docs/features/chain-sight/CHAIN_SIGHT_ROADMAP.md`

- ✅ Phase 3: ETF Holdings
- ✅ Phase 4: Supply Chain (SEC 10-K)
- ✅ Phase 5: LLM 관계 추출 (Gemini)
- ✅ Phase 6: 키워드 Enrichment + 뉴스 패턴 매칭 + 클릭 트래킹
- ✅ Phase 7: Institutional Holdings (SEC 13F)
- ✅ Phase 8: Regulatory + Patent Network (SEC 8-K, USPTO)
