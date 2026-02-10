# Stock-Vis Documentation

## 문서 구조

| 폴더 | 설명 |
|------|------|
| `architecture/` | 시스템 아키텍처 및 설계 문서 |
| `features/` | 기능별 설계 및 구현 가이드 |
| `infrastructure/` | 인프라, AWS, 배포 관련 문서 |
| `migration/` | API 마이그레이션 문서 |
| `testing/` | 테스트 전략 및 QA 리포트 |
| `bug-reports/` | 버그 리포트 및 수정 내역 |
| `user-guide/` | 사용자 가이드 |
| `ai-analysis/` | AI 분석 기능 설계 |
| `misc/` | 기타 문서 |

---

## 주요 문서

### 아키텍처

- [AI 분석 아키텍처](architecture/AI-analysis-architecture.md)
- [그래프 온톨로지 설계](architecture/GRAPH_ONTOLOGY_INFRA_REDESIGN.md)
- [데이터 인프라 로드맵 평가](architecture/DATA_INFRASTRUCTURE_ROADMAP_EVALUATION.md)
- [뉴스 아키텍처 리뷰](architecture/NEWS-ARCHITECTURE-REVIEW.md)
- [키워드 수집 아키텍처](architecture/KEYWORD_DATA_COLLECTION_ARCHITECTURE.md)
- [스크린 데이터 구조](architecture/SCREEN_DATA_STRUCTURE.md)

### 기능별 문서

#### Screener
- [스크리너 업그레이드 플랜](features/screener/SCREENER_UPGRADE_PLAN.md)
- [프리셋 공유 구현](features/screener/PRESET_SHARING_IMPLEMENTATION.md)

#### Market Movers
- [Market Movers 키워드 설계](features/market-movers/MARKET_MOVERS_KEYWORD_DESIGN.md)
- [Market Movers 키워드 인프라 설계](features/market-movers/MARKET_MOVERS_KEYWORD_INFRA_DESIGN.md)

#### Keywords
- [프론트엔드 키워드 시스템 설계](features/keywords/FRONTEND_KEYWORD_SYSTEM_DESIGN.md)
- [키워드 데이터 수집 사용법](features/keywords/KEYWORD_DATA_COLLECTION_USAGE.md)
- [키워드 인프라 구현 요약](features/keywords/KEYWORD_INFRA_IMPLEMENTATION_SUMMARY.md)

#### News
- [뉴스 인프라 설정](features/news/NEWS-INFRASTRUCTURE-SETUP.md)

#### Stock Sync
- [주식 자동 동기화 시스템](features/stock-sync/STOCK_AUTO_SYNC_SYSTEM.md)

#### Empty Basket
- [빈 바구니 가이드라인](features/empty-basket/empty-basket-guidelines.md)
- [빈 바구니 구현](features/empty-basket/empty-basket-implementation.md)
- [빈 바구니 요약](features/empty-basket/EMPTY_BASKET_SUMMARY.md)

#### Watchlist
- [Watchlist 스펙](features/watchlist/SPEC.md)
- [Watchlist 코드 리뷰](features/watchlist/watchlist_code_review.md)

### 인프라

- [환경 변수 가이드](infrastructure/ENVIRONMENT-VARIABLES.md)
- [모니터링](infrastructure/MONITORING.md)

#### AWS
- [AWS 계정 설정 및 보안 가이드](infrastructure/aws/AWS-account-setup-security-guide.md)
- [서버리스 마이그레이션 플랜](infrastructure/aws/serverless-migration-plan.md)
- [Market Movers Django to AWS 플랜](infrastructure/aws/market-movers-django-to-aws-plan.md)

#### Serverless
- [서버리스 개요](infrastructure/serverless/00_SERVERLESS_OVERVIEW.md)
- [뉴스 자동 수집](infrastructure/serverless/01_NEWS_AUTO_COLLECTION.md)
- [Market Movers Lambda](infrastructure/serverless/02_MARKET_MOVERS_LAMBDA.md)
- [AI 키워드 Lambda](infrastructure/serverless/03_AI_KEYWORDS_LAMBDA.md)
- [가격 동기화 Lambda](infrastructure/serverless/04_PRICE_SYNC_LAMBDA.md)
- [구현 로드맵](infrastructure/serverless/05_IMPLEMENTATION_ROADMAP.md)

### 테스트

- [테스팅 가이드](testing/testing-guide.md)
- [재무 단위 스펙](testing/financial_unit_specification.md)
- [재무 단위 테스트 케이스](testing/financial_unit_test_cases.md)

#### QA 리포트
- [뉴스 QA 리포트](testing/qa-reports/NEWS-QA-REPORT.md)
- [KB 품질 리포트 AI 분석](testing/qa-reports/KB_Quality_Report_AI_Analysis.md)
- [GOOGL 데이터 이슈 분석](testing/qa-reports/qa_analysis_googl_data_issue.md)

### 버그 리포트

- [뉴스 시스템 중복 엔티티 버그](bug-reports/news-system-duplicate-entity-bug.md)
- [뉴스 버그 수정 요약](bug-reports/news-bug-fix-summary.md)

### 마이그레이션

- [API 비교 요약](migration/API_COMPARISON_SUMMARY.md)
- [Alpha Vantage 사용 리포트](migration/alpha-vantage-usage-report.md)
- [API 매핑 테이블](migration/api-mapping-table.md)
- [데이터 요구사항](migration/data-requirements.md)
- [테스트 전략](migration/test-strategy.md)
- [테스트 전략 요약](migration/TEST-STRATEGY-SUMMARY.md)

### 사용자 가이드

- [사용자 가이드 목차](user-guide/README.md)
- [주식 상세](user-guide/stock-detail/README.md)
- [포트폴리오](user-guide/portfolio/README.md)
- [전략 분석](user-guide/strategy-analysis/README.md)
- [Market Pulse](user-guide/market-pulse/README.md)

### AI 분석

- [Phase 1.0 개요](ai-analysis/plan/version-1.0/overview.md)
- [Phase 1](ai-analysis/plan/version-1.0/phase_1.md)
- [Phase 2](ai-analysis/plan/version-1.0/phase_2.md)
- [Phase 3](ai-analysis/plan/version-1.0/phase_3.md)
- [프롬프트](ai-analysis/plan/version-1.0/prompts.md)
- [스크린 구조](ai-analysis/plan/version-1.0/screen_structure.md)

---

## 문서 네이밍 규칙

- 파일명: `UPPER_SNAKE_CASE.md` (설계/구현 문서) 또는 `lower-kebab-case.md` (가이드)
- 폴더명: `lower-kebab-case`
- 버전: `version-X.Y` 형식
