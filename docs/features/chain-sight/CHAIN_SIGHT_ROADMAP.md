# Chain Sight 로드맵

## 개요

Chain Sight는 주식 간 다양한 관계를 그래프로 시각화하여 "숨겨진 연결고리"를 발견하는 시스템입니다.

---

## Phase 현황

| Phase | 기능 | 상태 | 비용 |
|-------|------|------|------|
| 1 (MVP) | 기본 관계 (PEER_OF, SAME_INDUSTRY, CO_MENTIONED) | ✅ 완료 | $0 |
| 1.5 | Neo4j 온톨로지 통합 | ✅ 완료 | $0 |
| 3 | ETF Holdings (HAS_THEME) | ✅ 완료 | $0 |
| 4 | Supply Chain (SUPPLIED_BY, CUSTOMER_OF) | ✅ 완료 | $0 |
| 5 | Gemini LLM 관계 추출 | ✅ 완료 | ~$5/월 |
| 6 | 키워드 Enrichment + 뉴스 패턴 매칭 + 클릭 트래킹 | ✅ 완료 | $0 |
| 7 | Institutional Holdings (SEC 13F) | ✅ 완료 | $0 |
| 8 | Regulatory + Patent Network (SEC 8-K, USPTO) | ✅ 완료 | $0 |

---

## Phase 1: 기본 관계 (MVP) ✅ 완료

### 관계 타입

| 타입 | 설명 | 데이터 소스 |
|------|------|-------------|
| **PEER_OF** | 경쟁사 | FMP `/stable/stock-peers` |
| **SAME_INDUSTRY** | 동일 산업 | FMP `/stable/company-screener` |
| **CO_MENTIONED** | 뉴스 동시언급 | NewsEntity 모델 |

### 구현 파일
- `serverless/services/relationship_service.py`
- `serverless/services/category_generator.py`
- `serverless/services/chain_sight_stock_service.py`

---

## Phase 1.5: Neo4j 온톨로지 통합 ✅ 완료

### 아키텍처
```
ChainSightStockService
    └── Neo4j 우선 조회 → PostgreSQL fallback
```

### 구현 파일
- `serverless/services/neo4j_chain_sight_service.py`
- `serverless/management/commands/migrate_chain_sight_to_neo4j.py`

---

## Phase 3: ETF Holdings (HAS_THEME) ✅ 완료

### 관계 타입

| 타입 | 설명 | 데이터 소스 |
|------|------|-------------|
| **HELD_BY** | ETF 보유 | 운용사 CSV/XLSX |
| **HAS_THEME** | 테마 소속 | ETF Holdings 기반 |

### ETF 자동화 현황
- **자동 수집**: 15/21 ETF (SPDR, iShares, GlobalX)
- **수동 필요**: 6개 (ARKK, ARKG, TAN, KWEB, HACK, BETZ)

### Celery 스케줄
- 매주 월요일 06:00 EST 자동 수집
- 실패 시 이메일 알림

### 구현 파일
- `serverless/services/etf_csv_downloader.py`
- `serverless/services/theme_matching_service.py`
- `frontend/app/chain-sight/page.tsx`

---

## Phase 4: Supply Chain ✅ 완료

### 목표
SEC 10-K에서 공급망 관계 추출 (SUPPLIED_BY, CUSTOMER_OF)

### 관계 타입

| 타입 | 설명 | 예시 |
|------|------|------|
| **SUPPLIED_BY** | 공급사 | NVDA ← TSMC (파운드리) |
| **CUSTOMER_OF** | 고객사 | NVDA → MSFT (Azure) |

### 구현 내용

1. **SEC EDGAR Client** (`api_request/sec_edgar_client.py`)
   - CIK 조회 (티커 → CIK 변환)
   - 10-K 파일링 목록 조회
   - 10-K 본문 다운로드 (HTML → 텍스트)
   - Item 1A (Risk Factors) 추출

2. **Supply Chain Parser** (`serverless/services/supply_chain_parser.py`)
   - Regex 패턴 기반 고객/공급사 추출
   - 엄격한 회사명 검증 (1-5 단어, suffix 필수)
   - PREFIX/SUFFIX 정리, INVALID_WORDS 필터링
   - 신뢰도 계산 (high/medium-high/medium)

3. **Supply Chain Service** (`serverless/services/supply_chain_service.py`)
   - 동기화 파이프라인
   - PostgreSQL + Neo4j 저장
   - 캐싱 전략

### Celery 스케줄
- 매월 15일 03:00 EST 배치 동기화

### 테스트
- 54개 테스트 (SEC EDGAR 12개, Parser 24개, Service 18개)

---

## Phase 5: Gemini LLM 관계 추출 ✅ 완료

**상세 설계**: `docs/features/chain-sight/CHAIN_SIGHT_PHASE5_LLM_DESIGN.md`

### 목표
뉴스/SEC 보고서에서 Gemini 2.5 Flash로 복잡한 기업 간 관계 자동 추출

### 구현 파일
- `serverless/models.py` - LLMExtractedRelation 모델 (30일 TTL)
- `serverless/services/relation_pre_filter.py` - Regex 사전 필터링
- `serverless/services/symbol_matcher.py` - 회사명 → 티커 매칭
- `serverless/services/llm_relation_extractor.py` - Gemini 관계 추출
- `serverless/tasks.py` - Celery 태스크 (배치 처리, 동기화)
- `serverless/views.py` - REST API 엔드포인트

### API 엔드포인트
- `POST /llm-relations/extract` - LLM 관계 추출 트리거
- `GET /llm-relations/{symbol}` - 종목의 추출 관계 조회
- `POST /llm-relations/sync` - StockRelationship/Neo4j 동기화
- `GET /llm-relations/stats` - 추출 통계

### 테스트
- **총 66개 테스트** (4 skipped)
- RelationPreFilter: 30개
- SymbolMatcher: 22개
- LLMRelationExtractor: 14개

### 아키텍처
```
NewsEntity / SEC Filing
        │
        ▼
   Pre-filter (Regex)  ◄── 비용 절감 (20%만 LLM 호출)
        │
        ▼
   Gemini 2.5 Flash (동기 API)
        │
        ▼
   LLMExtractedRelation 모델
        │
        ├── StockRelationship (PostgreSQL)
        └── Neo4j Graph
```

### 추출 가능 관계

| 관계 | 트리거 예시 | 우선순위 |
|------|------------|---------|
| **ACQUIRED** | "NVDA acquired Mellanox for $6.9B" | P0 |
| **INVESTED_IN** | "SoftBank invested $1B in ARM" | P0 |
| **PARTNER_OF** | "AAPL partnered with Goldman Sachs" | P0 |
| **SPIN_OFF** | "eBay spun off PayPal" | P1 |
| **SUED_BY** | "Epic Games sued Apple" | P1 |
| **SUPPLIED_BY** | (Phase 4 보강) | P0 |
| **CUSTOMER_OF** | (Phase 4 보강) | P0 |

### 비용 최적화

| 전략 | 효과 |
|------|------|
| Pre-filter (Regex) | ~80% LLM 호출 절감 |
| 배치 처리 (5개/요청) | API 호출 수 감소 |
| 캐싱 (7일) | 중복 처리 방지 |

### 월간 비용 추정: ~$5
- 뉴스 처리: ~$0.07/월
- SEC 10-K 처리 (월 1회): ~$3.15/월
- 버퍼 포함: ~$5/월

### 신규 모델
- `LLMExtractedRelation`: LLM 추출 관계 + 메타데이터
- TTL: 30일 (자동 만료)

### 구현 순서 (6주)
1. Week 1: 기반 구축 (모델, 마이그레이션)
2. Week 2: 핵심 서비스 (Pre-filter, SymbolMatcher)
3. Week 3: LLM 통합 (Gemini API, 배치 처리)
4. Week 4: 파이프라인 (Celery, API)
5. Week 5: 테스트 및 최적화
6. Week 6: 문서화 및 배포

---

## Phase 6: 키워드 Enrichment + 뉴스 패턴 매칭 + 클릭 트래킹 ✅ 완료

### 구현 내용

#### 6A: 관계 태그 표시
- `RelationshipTagBadge.tsx` 컴포넌트 - 관계 타입별 색상 태그
- `relationshipTagStyles.ts` - 태그 스타일 매핑

#### 6B: 뉴스 패턴 매칭
- `NewsRelationMatcher` 서비스 - 뉴스에서 관계 키워드 자동 추출
- 매일 09:00 EST Celery 태스크

#### 6C: 클릭 트래킹
- `/chain-sight/stock/{symbol}/track` API - 사용자 행동 Edge Weight 강화

#### 6D: 키워드 Enrichment
- `RelationshipKeywordEnricher` 서비스 - Gemini로 관계 키워드 3개 생성
- `StockRelationship.context["keywords"]`에 저장
- 매일 05:30 EST Celery 태스크

### 구현 파일
- `serverless/services/relationship_keyword_enricher.py`
- `serverless/services/news_relation_matcher.py`
- `frontend/components/chain-sight/RelationshipTagBadge.tsx`

---

## Phase 7: Institutional Holdings (SEC 13F) ✅ 완료

### 목표
SEC 13F 공시에서 기관투자자 보유 현황 수집 → HELD_BY_SAME_FUND 관계 생성

### 모델
- **InstitutionalHolding**: institution_cik, stock_symbol, shares, value_thousands, position_change

### 관계 타입
| 타입 | 설명 | 예시 |
|------|------|------|
| **HELD_BY_SAME_FUND** | 같은 펀드 보유 | AAPL, MSFT (ARK Innovation) |

### 구현 파일
- `serverless/services/institutional_holdings_service.py` - 13F 수집 + 관계 생성
- `serverless/services/cusip_mapper.py` - CUSIP → 티커 변환 (500+ 하드코딩 + FMP fallback)
- `api_request/sec_edgar_client.py` - 13F 파서 확장 (Filing13F, download_13f_holdings)

### API
- `GET /institutional/<symbol>` - 기관 보유 현황
- `GET /institutional/<symbol>/peers` - 같은 펀드 보유 종목
- `POST /institutional/sync` - 수동 동기화

### Celery 스케줄
- 분기별 (매월 16일 04:00, 태스크 내에서 2/5/8/11월 체크)

### 비용: $0 (SEC EDGAR 무료)

---

## Phase 8: Regulatory + Patent Network ✅ 완료

### 8.1 Regulatory (규제 공유)

| 타입 | 설명 | 예시 |
|------|------|------|
| **SAME_REGULATION** | 같은 규제 영향 | GOOGL, META (반독점) |

#### 규제 카테고리 (8개)
반독점, FDA, 중국 제재, 데이터 프라이버시, 금융 규제, 환경 규제, 암호화폐 규제, AI 규제

#### 구현 파일
- `serverless/services/regulatory_service.py` - 뉴스 + 8-K + LLM 규제 그룹 탐지
- `api_request/sec_edgar_client.py` - 8-K 파서 확장 (Filing8K, download_8k_text)

### 8.2 Patent Network (특허)

| 타입 | 설명 | 예시 |
|------|------|------|
| **PATENT_CITED** | 특허 인용 | AAPL → Qualcomm 특허 인용 |
| **PATENT_DISPUTE** | 특허 분쟁 | AAPL ↔ Samsung |

#### 구현 파일
- `serverless/services/uspto_client.py` - USPTO PatentsView API (무료, 키 불필요)
- `serverless/services/patent_network_service.py` - 인용/분쟁 네트워크 빌더

### Celery 스케줄
- 규제 스캔: 주간 (월요일 04:00)
- 특허 네트워크: 월간 (1일 04:30)

### 비용: $0 (SEC + USPTO 모두 무료)

---

## 비용 요약

| Phase | 추가 비용 | 누적 비용 |
|-------|----------|----------|
| 1~3 | $0 | $0 |
| 4 (Supply Chain) | $0 (SEC 파싱) | $0 |
| 5 (Gemini LLM) | ~$5/월 | ~$5/월 |
| 6 (키워드 Enrichment) | $0 (Gemini Free) | ~$5/월 |
| 7 (Institutional Holdings) | $0 (SEC 13F) | ~$5/월 |
| 8 (Regulatory/Patent) | $0 (SEC/USPTO) | ~$5/월 |

---

## 예상 관계 규모 (Phase 8 완료 시)

| 관계 타입 | 예상 규모 |
|----------|----------|
| PEER_OF | ~500 |
| SAME_INDUSTRY | ~2,000 |
| CO_MENTIONED | ~3,000 |
| HAS_THEME (ETF) | ~5,000 |
| SUPPLIED_BY / CUSTOMER_OF | ~1,000 |
| HELD_BY_SAME_FUND | ~10,000 |
| SAME_REGULATION | ~500 |
| PATENT_CITED | ~2,000 |
| **총계** | **~24,000** |

---

## 검증 방법

### Neo4j 쿼리
```cypher
// 전체 관계 통계
MATCH ()-[r]->()
RETURN type(r) as relationship, count(r) as count
ORDER BY count DESC

// NVDA 중심 2-depth 그래프
MATCH path = (s:Stock {symbol: 'NVDA'})-[*1..2]-(t:Stock)
RETURN path

// Supply Chain 관계만
MATCH (s:Stock)-[r:SUPPLIED_BY|CUSTOMER_OF]->(t:Stock)
RETURN s.symbol, type(r), t.symbol
```

### API 테스트
```bash
# Phase별 관계 조회
curl "http://localhost:8000/api/v1/serverless/chain-sight/stock/NVDA/category/suppliers"
curl "http://localhost:8000/api/v1/serverless/chain-sight/stock/NVDA/category/institutional_holders"
```
