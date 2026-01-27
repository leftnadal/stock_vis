# Phase 1 완료 보고서: FMP 마이그레이션 분석 & 설계

**작성일**: 2025-12-08
**상태**: ✅ Phase 1 Complete
**다음 단계**: Phase 2 - 구현

---

## 📋 Executive Summary

Stock-Vis 프로젝트의 Alpha Vantage API에서 FMP(Financial Modeling Prep) API로의 마이그레이션을 위한 분석 및 설계 단계가 완료되었습니다.

### 핵심 결론

| 항목 | 결론 |
|-----|------|
| **마이그레이션 전략** | 하이브리드 접근 (두 API 동시 사용 권장) |
| **FMP 무료 티어** | 250 calls/day - 충분한 운영 가능 |
| **예상 개발 기간** | 6-8주 (55-80시간) |
| **예상 비용** | $0/월 (무료 티어 유지 가능) |
| **위험도** | 낮음 (점진적 전환 + Fallback) |

---

## 🎯 Phase 1 목표 및 달성 현황

| # | 태스크 | 담당 에이전트 | 상태 | 산출물 |
|---|-------|-------------|------|-------|
| 1.1 | Alpha Vantage 사용 현황 스캔 | QA-Architect | ✅ | `alpha-vantage-usage-report.md` |
| 1.2 | 마이그레이션 아키텍처 설계 | QA-Architect | ✅ | `architecture-design.md`, `architecture-diagram.md` |
| 1.3 | 테스트 전략 수립 | QA-Architect | ✅ | `test-strategy.md`, `TEST-STRATEGY-SUMMARY.md` |
| 1.4 | FMP API 심층 분석 | Investment-Advisor | ✅ | `api-mapping-table.md`, `FMP-ANALYSIS-INDEX.md` |
| 1.5 | 데이터 요구사항 정의 | Investment-Advisor | ✅ | `data-requirements.md` |
| 1.6 | API 호출 예산 계획 | Investment-Advisor | ✅ | `api-budget-plan.md` |
| 1.7 | 기존 지식 베이스 검토 | KB-Curator | ✅ | KB 노드 3개 추가 |

**달성률: 7/7 (100%)**

---

## 📊 산출물 상세

### 문서 목록 (13개 파일, 8,791줄, ~295KB)

```
docs/migration/
├── PHASE1-COMPLETION-REPORT.md    # 이 문서 (최종 정리)
│
├── [QA-Architect 산출물]
│   ├── alpha-vantage-usage-report.md   # 738줄 - 현행 시스템 분석
│   ├── architecture-design.md          # 1,773줄 - Provider 추상화 설계
│   ├── architecture-diagram.md         # 388줄 - 시각적 다이어그램
│   ├── test-strategy.md                # 2,596줄 - 테스트 전략
│   ├── TEST-STRATEGY-SUMMARY.md        # 349줄 - 테스트 요약
│   └── QA-TASK-COMPLETION-REPORT.md    # 559줄 - QA 작업 보고서
│
├── [Investment-Advisor 산출물]
│   ├── api-mapping-table.md            # 833줄 - API 엔드포인트 매핑
│   ├── API_COMPARISON_SUMMARY.md       # 282줄 - API 비교 요약
│   ├── FMP-ANALYSIS-INDEX.md           # 310줄 - FMP 분석 인덱스
│   ├── data-requirements.md            # 650줄 - 데이터 요구사항
│   └── api-budget-plan.md              # 700줄 - API 호출 예산
│
└── README.md                           # 226줄 - 빠른 참조 가이드
```

### 테스트 인프라 (11개 파일)

```
tests/
├── conftest.py              # pytest 공통 fixture (150줄)
├── README.md                # 테스트 실행 가이드
├── __init__.py
├── fixtures/                # Mock 데이터 디렉토리
│   └── fmp/                 # FMP 응답 샘플
├── unit/
│   └── providers/fmp/       # FMP 단위 테스트
├── integration/             # 통합 테스트
├── e2e/                     # E2E 테스트
├── scenarios/               # 시나리오 테스트
└── validators/
    └── data_validator.py    # 데이터 검증 로직 (240줄)

pytest.ini                   # pytest 설정
.coveragerc                  # 커버리지 설정
```

### KB 추가 지식 (3개)

| 제목 | 유형 | 상태 |
|-----|------|------|
| API Provider 추상화 패턴 | Pattern | 큐 대기 |
| FMP API Rate Limit 관리 (250/day) | API | 큐 대기 |
| API 마이그레이션 점진적 전환 전략 | Lesson | 큐 대기 |

---

## 🔍 주요 분석 결과

### 1. Alpha Vantage 현행 시스템

**사용 중인 API 엔드포인트 (9개)**:

| Function | 용도 | 호출 빈도 |
|----------|------|----------|
| `GLOBAL_QUOTE` | 실시간 주가 | 높음 |
| `OVERVIEW` | 회사 기본정보 | 중간 |
| `TIME_SERIES_DAILY` | 일별 시세 | 중간 |
| `TIME_SERIES_WEEKLY` | 주간 시세 | 낮음 |
| `SYMBOL_SEARCH` | 종목 검색 | 중간 |
| `BALANCE_SHEET` | 재무상태표 | 낮음 |
| `INCOME_STATEMENT` | 손익계산서 | 낮음 |
| `CASH_FLOW` | 현금흐름표 | 낮음 |
| `SECTOR` | 섹터 성과 | 낮음 |

**현재 아키텍처**:
```
API request/
├── alphavantage_client.py     # HTTP 클라이언트 (Rate Limit 12초)
├── alphavantage_processor.py  # 데이터 변환 (camelCase → snake_case)
└── alphavantage_service.py    # DB 저장, 비즈니스 로직
```

**호출 지점**:
- `stocks/views_search.py` - 종목 검색
- `stocks/tasks.py` - Celery 백그라운드 태스크
- `users/utils.py` - 포트폴리오 데이터 수집

### 2. FMP API 분석

**무료 티어 제한**:
- 250 API calls/day (Alpha Vantage: 500/day)
- Rate Limit 없음 (Alpha Vantage: 12초 대기 필요)
- 배치 API 지원 (최대 5개 심볼 동시 조회)

**Alpha Vantage vs FMP 비교**:

| 항목 | Alpha Vantage | FMP | 승자 |
|-----|--------------|-----|------|
| 일일 호출 제한 | 500회 | 250회 | AV |
| Rate Limit | 5/분 (12초 대기) | 없음 | **FMP** |
| 배치 API | ❌ | ✅ | **FMP** |
| 재무제표 품질 | 양호 | SEC 소스 (최상) | **FMP** |
| 실시간 주가 | NASDAQ 공식 | 양호 | AV |
| 기술적 지표 | 20+ 내장 | ❌ | AV |
| 히스토리 데이터 | 20년 | 120년 | **FMP** |

**권장: 하이브리드 접근**
- Alpha Vantage: 실시간 주가, 기술적 지표 (RSI, MACD 등)
- FMP: 재무제표, 회사 프로필, 히스토리 데이터

### 3. API 엔드포인트 매핑

| 기능 | Alpha Vantage | FMP | 무료 지원 |
|-----|--------------|-----|----------|
| 실시간 주가 | `GLOBAL_QUOTE` | `/quote/{symbol}` | ✅ |
| 회사 정보 | `OVERVIEW` | `/profile/{symbol}` | ✅ |
| 일별 시세 | `TIME_SERIES_DAILY` | `/historical-price-full/{symbol}` | ✅ |
| 주간 시세 | `TIME_SERIES_WEEKLY` | 계산 필요 | ⚠️ |
| 종목 검색 | `SYMBOL_SEARCH` | `/search?query={q}` | ✅ |
| 재무상태표 | `BALANCE_SHEET` | `/balance-sheet-statement/{symbol}` | ✅ |
| 손익계산서 | `INCOME_STATEMENT` | `/income-statement/{symbol}` | ✅ |
| 현금흐름표 | `CASH_FLOW` | `/cash-flow-statement/{symbol}` | ✅ |

### 4. API 호출 예산 계획

**일일 250회 내 운영 전략**:

| 최적화 단계 | 예상 호출 | 감소율 |
|-----------|---------|--------|
| 기본 (캐싱 없음) | 1,440회/일 | - |
| Redis 캐싱 (85% 히트율) | 216회/일 | 85% ↓ |
| 배치 API 추가 | 40회/일 | 97% ↓ |
| DB Fallback | 6회/일 | 99.6% ↓ |

**사용자 시나리오**:
- 일반 사용자 (10종목): ~5 calls/일
- 활발한 사용자 (50종목): ~6 calls/일 (배치 API)

**캐시 TTL 권장값**:

| 데이터 유형 | TTL | 근거 |
|-----------|-----|------|
| 실시간 주가 | 60초 | 빠른 변동 |
| 회사 프로필 | 1시간 | 거의 불변 |
| 재무제표 | 1주일 | 분기/연간 업데이트 |
| 히스토리 가격 | 24시간 | 일일 종가 기준 |

---

## 🏗️ 아키텍처 설계

### Provider 추상화 패턴

```python
# providers/base.py
from abc import ABC, abstractmethod

class StockDataProvider(ABC):
    @abstractmethod
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """실시간 주가 조회"""
        pass

    @abstractmethod
    def get_company_profile(self, symbol: str) -> Dict[str, Any]:
        """회사 기본정보 조회"""
        pass

    @abstractmethod
    def get_historical_daily(self, symbol: str) -> List[Dict[str, Any]]:
        """일별 시세 조회"""
        pass

    # ... 8개 메서드 정의
```

### 디렉토리 구조 (권장)

```
API_request/
├── providers/
│   ├── __init__.py
│   ├── base.py                    # StockDataProvider 추상 클래스
│   ├── alphavantage/
│   │   ├── client.py              # 기존 코드 이동
│   │   ├── processor.py           # 기존 코드 이동
│   │   └── provider.py            # 인터페이스 구현
│   └── fmp/
│       ├── client.py              # FMP HTTP 클라이언트 (신규)
│       ├── processor.py           # FMP 데이터 변환 (신규)
│       └── provider.py            # 인터페이스 구현 (신규)
├── cache/
│   ├── base.py
│   ├── redis_cache.py
│   └── decorators.py              # @cached_provider_call
├── provider_factory.py            # Feature Flag 기반 선택
└── stock_service.py               # Provider-agnostic 서비스
```

### Feature Flag 설정

```bash
# .env
STOCK_DATA_PROVIDER=alphavantage    # 기본 Provider

# 엔드포인트별 개별 전환 (점진적 마이그레이션)
PROVIDER_SEARCH=fmp
PROVIDER_COMPANY_PROFILE=fmp
PROVIDER_FINANCIAL=fmp
PROVIDER_QUOTE=alphavantage         # 실시간 주가는 AV 유지

# Fallback 설정
ENABLE_PROVIDER_FALLBACK=true
FALLBACK_PROVIDER=alphavantage
```

### Fallback 메커니즘

```
요청 → Primary Provider (FMP)
         │
         ├─ 성공 → 응답 반환
         │
         └─ 실패 (API Error, Rate Limit)
              │
              └─ Fallback Provider (Alpha Vantage)
                   │
                   ├─ 성공 → 응답 반환 (+ 로깅)
                   │
                   └─ 실패 → 에러 반환
```

---

## 🧪 테스트 전략

### 테스트 피라미드

```
        ┌─────────┐
        │   E2E   │  10%  (주요 사용자 시나리오)
        ├─────────┤
        │Integrat-│  30%  (DB, Cache, Provider 통합)
        │  ion    │
        ├─────────┤
        │  Unit   │  60%  (Client, Processor, Provider)
        └─────────┘
```

### 테스트 시나리오

| 카테고리 | 시나리오 | 검증 항목 |
|---------|---------|----------|
| **정상** | FMP 주가 조회 | 필드 존재, 타입 검증, 값 범위 |
| **정상** | 재무제표 조회 | 연간/분기 구분, 날짜 형식 |
| **에러** | Rate Limit 초과 | 429 응답 처리, Fallback 동작 |
| **에러** | API 서버 다운 | 타임아웃, 재시도, Fallback |
| **Fallback** | Primary 실패 | Alpha Vantage 자동 전환 |
| **캐시** | 캐시 히트 | TTL 검증, 캐시 무효화 |

### 커버리지 목표

| 영역 | 목표 | 현재 |
|-----|------|------|
| Unit Tests | 80% | 0% (인프라 준비 완료) |
| Integration | 70% | 0% |
| E2E | 50% | 0% |
| **전체** | **80%** | **0%** |

---

## 📅 Phase 2 로드맵

### 마이그레이션 단계 (6-8주)

```
Week 1-2: 인프라 구축
├── FMP Client 구현
├── FMP Processor 구현
├── Provider 추상화 레이어
└── Feature Flag 설정

Week 3-4: 점진적 전환
├── 검색 API → FMP (위험도 최소)
├── 회사 프로필 → FMP
├── 재무제표 → FMP
└── 히스토리 가격 → FMP

Week 5-6: 검증 및 안정화
├── 통합 테스트 실행
├── 성능 모니터링
├── Fallback 동작 확인
└── 캐싱 효율 검증

Week 7-8: 완전 전환
├── 실시간 주가 평가 (AV 유지 or FMP 전환)
├── Alpha Vantage 의존성 축소
├── 문서 업데이트
└── 운영 가이드 작성
```

### 점진적 전환 순서 (위험도 낮은 순)

```
1. 검색 API        ──▶ 영향도 최소, 캐싱 효과 높음
2. 회사 프로필     ──▶ 데이터 거의 불변
3. 재무제표 (3개)  ──▶ 분기별 업데이트, FMP 품질 우수
4. 주간 가격       ──▶ 사용 빈도 낮음
5. 일간 가격       ──▶ 차트에 영향
6. 실시간 주가     ──▶ 가장 민감, 마지막 전환
```

### 담당 에이전트 배정

| Phase | 담당 | 작업 내용 |
|-------|------|----------|
| 2.1 | @backend | FMP Client/Processor/Provider 구현 |
| 2.2 | @backend | Provider 추상화 레이어 구현 |
| 2.3 | @infra | Redis 캐싱 설정, Feature Flag 환경변수 |
| 2.4 | @infra | Celery 스케줄링 최적화 |
| 2.5 | @qa-architect | 단위 테스트 작성 |
| 2.6 | @qa-architect | 통합/E2E 테스트 작성 |
| 2.7 | @frontend | API 응답 형식 호환성 검증 |

---

## ⚠️ 리스크 및 대응 방안

| 리스크 | 확률 | 영향 | 대응 방안 |
|--------|-----|------|----------|
| 필드 매핑 불일치 | 높음 | 중간 | Processor에서 변환 레이어 |
| FMP Rate Limit 초과 | 중간 | 높음 | 캐싱 강화 + 호출 모니터링 |
| 데이터 품질 차이 | 낮음 | 중간 | 일관성 테스트로 사전 검증 |
| Fallback 무한 루프 | 낮음 | 높음 | Circuit Breaker 패턴 적용 |
| 성능 저하 | 낮음 | 중간 | 벤치마크 테스트 |

### 롤백 전략

**긴급 롤백 (환경변수만 변경)**:
```bash
STOCK_DATA_PROVIDER=alphavantage
ENABLE_PROVIDER_FALLBACK=false
```

**코드 롤백**:
```bash
git revert <migration-commit>
```

---

## 💰 비용 분석

### 현재 (Alpha Vantage 무료 티어)

| 항목 | 비용 |
|-----|------|
| 월간 API 비용 | $0 |
| 제한 | 500 calls/day, 12초 Rate Limit |
| 문제점 | Rate Limit으로 인한 성능 저하 |

### 마이그레이션 후 (하이브리드)

| 항목 | 비용 |
|-----|------|
| Alpha Vantage | $0 (실시간 주가, 기술 지표용) |
| FMP 무료 | $0 (재무제표, 회사 프로필용) |
| **총 월간 비용** | **$0** |

### 스케일업 시나리오

| 사용자 규모 | 예상 호출 | 권장 플랜 | 월 비용 |
|-----------|---------|---------|--------|
| 1-50명 | ~100/일 | 무료 | $0 |
| 50-200명 | ~400/일 | FMP Starter | $29 |
| 200-1000명 | ~1,500/일 | FMP Pro | $99 |

---

## ✅ Phase 1 완료 체크리스트

- [x] Alpha Vantage 사용 현황 문서 완료
- [x] FMP 엔드포인트 매핑 테이블 완료
- [x] 아키텍처 설계 문서 승인
- [x] 테스트 전략 문서 승인
- [x] API 호출 예산 계획 승인
- [x] 데이터 요구사항 정의 완료
- [x] 테스트 인프라 구축 완료
- [x] KB 지식 추가 완료
- [x] 모든 에이전트 리뷰 완료

---

## 📚 참고 자료

### 생성 문서

| 문서 | 위치 | 용도 |
|-----|------|------|
| Alpha Vantage 분석 | `alpha-vantage-usage-report.md` | 현행 시스템 이해 |
| 아키텍처 설계 | `architecture-design.md` | 개발 가이드 |
| API 매핑 | `api-mapping-table.md` | 필드 매핑 참조 |
| 테스트 전략 | `test-strategy.md` | QA 가이드 |
| 데이터 요구사항 | `data-requirements.md` | 기능 명세 |
| API 예산 | `api-budget-plan.md` | 운영 계획 |

### 외부 문서

- [FMP 공식 문서](https://site.financialmodelingprep.com/developer/docs)
- [Alpha Vantage 문서](https://www.alphavantage.co/documentation/)

---

## 🚀 다음 단계

Phase 1이 완료되었습니다. Phase 2 (구현)를 시작하려면:

```bash
# 1. FMP API 키 발급
https://site.financialmodelingprep.com/developer/docs

# 2. 환경 변수 추가
echo 'FMP_API_KEY=your_key_here' >> .env

# 3. 테스트 의존성 설치
poetry add --group dev pytest pytest-django pytest-mock pytest-cov pytest-vcr

# 4. Phase 2 시작
@backend: FMP Client 구현 시작
```

---

*이 보고서는 2025-12-08 Phase 1 완료 시점에 자동 생성되었습니다.*
*담당 에이전트: QA-Architect, Investment-Advisor, KB-Curator*
