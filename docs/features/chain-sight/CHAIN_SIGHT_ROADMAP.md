# Chain Sight 로드맵

## 개요

Chain Sight는 주식 간 다양한 관계를 그래프로 시각화하여 "숨겨진 연결고리"를 발견하는 시스템입니다.

---

## Phase 현황

| Phase | 기능 | 상태 | 비용 |
|-------|------|------|------|
| 1 (MVP) | 기본 관계 (PEER_OF, SAME_INDUSTRY, CO_MENTIONED) | ✅ 완료 | $0 |
| 1.5 | Neo4j 온톨로지 통합 | ✅ 완료 | $0 |
| 2 | 프론트엔드 그래프 시각화 | 예정 | $0 |
| 3 | ETF Holdings (HAS_THEME) | ✅ 완료 | $0 |
| 4 | Supply Chain (SUPPLIED_BY, CUSTOMER_OF) | ✅ 완료 | $0 |
| 5 | Gemini LLM 관계 추출 | ✅ 완료 | ~$5/월 |
| 6 | 뉴스 자연 축적 + 사용자 행동 Edge Weight | 예정 | $0 |
| 7 | Insider/Institution (HELD_BY_SAME_FUND) | 예정 | TBD |
| 8 | Regulatory + Patent Network | 예정 | TBD |

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

## Phase 2: 프론트엔드 그래프 시각화 (예정)

### 목표
Neo4j 그래프 데이터를 인터랙티브하게 시각화

### 기술 스택
- **react-force-graph**: 3D/2D 포스 다이어그램
- **D3.js**: 커스텀 시각화 (옵션)

### API
```bash
GET /api/v1/serverless/chain-sight/graph/{symbol}?depth=2
```

### 응답 형식 (react-force-graph 호환)
```json
{
    "nodes": [
        {"id": "NVDA", "name": "NVIDIA", "sector": "Technology", "group": "center"},
        {"id": "AMD", "name": "AMD", "sector": "Technology", "group": "related"}
    ],
    "edges": [
        {"source": "NVDA", "target": "AMD", "type": "PEER_OF", "weight": 0.85}
    ]
}
```

### UI 컴포넌트
- `ChainSightGraph.tsx` - 3D 그래프 뷰어
- `GraphControls.tsx` - depth, 필터, 레이아웃 컨트롤
- `NodeTooltip.tsx` - 노드 호버 시 상세 정보

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

## Phase 6: 뉴스 자연 축적 + 사용자 행동 Edge Weight (예정)

### 목표
기존 Marketaux 뉴스에서 관계를 자연 축적하고, 사용자 행동으로 edge weight 강화

### 전략
```
┌─────────────────────────────────────────────────────────────┐
│ 이미 운영 중인 Marketaux $9/월에서 CO_MENTIONED 축적        │
│ 뉴스에서 "AAPL supplier TSMC" 같은 공급망 관계가 자연 발견  │
│ 월 ~50~80개 Supply Chain 관계 추가                          │
│ + 사용자 행동 데이터 (카드 클릭, 카테고리 선택)로 edge weight 강화 │
│ 비용: $0 추가 (기존 Marketaux 비용에 포함)                  │
└─────────────────────────────────────────────────────────────┘
```

### 데이터 흐름
```
Marketaux 뉴스 수집 (기존)
        │
        ▼
NewsEntity 저장 (기존)
        │
        ├── CO_MENTIONED 관계 생성 (기존)
        │
        └── 키워드 패턴 매칭 (신규)
            "supplier", "customer", "partner", "acquired"
                │
                ▼
            Supply Chain 관계 자동 생성
```

### 사용자 행동 기반 Edge Weight 강화

| 행동 | Weight 증가 |
|------|-------------|
| 카테고리 클릭 | +0.05 |
| 종목 카드 클릭 | +0.1 |
| "파도타기" (다음 종목으로 이동) | +0.2 |
| 관계 무시 (스크롤 패스) | -0.02 |

### 구현 계획
1. 뉴스 키워드 패턴 매칭 서비스 구현
2. 사용자 행동 이벤트 트래킹 API
3. Edge weight 업데이트 Celery 태스크
4. A/B 테스트: weight 강화 vs 기본

---

## Phase 7: Insider/Institution (예정)

### 목표
동일 기관이 보유한 종목 간 관계 발견

### 관계 타입

| 타입 | 설명 | 예시 |
|------|------|------|
| **HELD_BY_SAME_FUND** | 같은 펀드 보유 | AAPL, MSFT (ARK Innovation) |
| **INSIDER_OVERLAP** | 같은 임원 보유 | AAPL, DIS (Bob Iger) |
| **INSTITUTIONAL_MOMENTUM** | 기관 동시 매수/매도 | Q4에 Berkshire가 같이 산 종목들 |

### 데이터 소스 옵션

| 소스 | 데이터 | 비용 |
|------|--------|------|
| SEC 13F Filing | 기관 보유 현황 (분기별) | $0 (EDGAR) |
| SEC Form 4 | 내부자 거래 | $0 (EDGAR) |
| Fintel API | 기관/내부자 통합 | ~$50/월 |
| WhaleWisdom | 헤지펀드 포지션 | ~$30/월 |

### 예상 카테고리
- "ARK 포트폴리오" - ARK가 보유한 종목들
- "Berkshire 포트폴리오" - 버핏이 보유한 종목들
- "같은 펀드 보유" - 동일 기관이 보유한 종목

### 구현 계획
1. SEC 13F 파서 개발 (EDGAR API)
2. 주요 기관 목록 관리 (ARK, Berkshire, BlackRock 등)
3. HELD_BY_SAME_FUND 관계 생성
4. 분기별 자동 업데이트 Celery 태스크

---

## Phase 8: Regulatory + Patent Network (예정)

### 목표
규제 영향 및 특허 인용 관계 추가

### 8.1 Regulatory (규제 영향)

| 타입 | 설명 | 예시 |
|------|------|------|
| **SAME_REGULATION** | 같은 규제 영향 | GOOGL, META (반독점) |
| **REGULATORY_RISK** | 규제 리스크 공유 | 중국 기술 제재 관련 종목 |

#### 데이터 소스
- SEC 8-K (Material Events)
- 뉴스 키워드: "antitrust", "FDA approval", "tariff"
- Gemini 추출 (Phase 5 연계)

#### 예상 카테고리
- "반독점 규제 관련" - GOOGL, META, AMZN, AAPL
- "FDA 승인 대기" - MRNA, PFE (동일 약물 경쟁)
- "중국 제재 영향" - NVDA, AMD, INTC

### 8.2 Patent Network (특허 인용)

| 타입 | 설명 | 예시 |
|------|------|------|
| **PATENT_CITED** | 특허 인용 | AAPL → Qualcomm 특허 인용 |
| **PATENT_DISPUTE** | 특허 분쟁 | AAPL ↔ Samsung |

#### 데이터 소스
- USPTO API (무료)
- Google Patents

#### 예상 카테고리
- "특허 인용 관계" - 기술 의존성 파악
- "특허 분쟁 이력" - 법적 리스크 파악

### 구현 계획
1. SEC 8-K 규제 관련 키워드 파서
2. USPTO API 클라이언트 구현
3. 규제/특허 관계 모델 추가
4. Neo4j 확장

---

## 비용 요약

| Phase | 추가 비용 | 누적 비용 |
|-------|----------|----------|
| 1~3 | $0 | $0 |
| 4 (Supply Chain) | $0 (SEC 파싱) | $0 |
| 5 (Gemini LLM) | ~$5/월 | ~$5/월 |
| 6 (자연 축적) | $0 (기존 Marketaux) | ~$5/월 |
| 7 (Institution) | $0 (SEC 13F) 또는 ~$30/월 (Fintel) | ~$5~35/월 |
| 8 (Regulatory/Patent) | $0 (SEC/USPTO) | ~$5~35/월 |

---

## 우선순위 권장

### 단기 (1~2개월)
1. **Phase 2**: 그래프 시각화 - UX 임팩트 높음
2. **Phase 4**: Supply Chain - SEC 무료 데이터 활용

### 중기 (3~4개월)
3. **Phase 6**: 뉴스 자연 축적 - 비용 $0, 자동화
4. **Phase 5**: Gemini LLM - 관계 추출 자동화

### 장기 (5~6개월)
5. **Phase 7**: Institution - 가치 높은 인사이트
6. **Phase 8**: Regulatory/Patent - 차별화 데이터

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
