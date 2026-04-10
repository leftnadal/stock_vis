# CLAUDE.md - Stock-Vis

## 프로젝트 개요

**Stock-Vis**: AI 기반 투자 분석 플랫폼

- **Backend**: Django REST Framework + PostgreSQL
- **Frontend**: Next.js 14+ (TypeScript)
- **Async**: Celery + Redis
- **LLM**: Gemini 2.5 Flash (키워드, 테제, 관계 추출, RAG 분석 전체)
- **Graph DB**: Neo4j (Chain Sight 온톨로지)

> 상세 문서는 `sub_claude_md/` 폴더에 주제별로 분할되어 있습니다.
> 작업 시작 전 관련 파일을 반드시 읽어주세요. → [sub_claude_md/README.md](sub_claude_md/README.md)

---

## 개발 환경 설정

### Backend

```bash
poetry install
# .env 필수 키: ALPHA_VANTAGE_API_KEY, FMP_API_KEY, GEMINI_API_KEY
# .env DB: DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
# .env 선택: FINNHUB_API_KEY, MARKETAUX_API_KEY, NEO4J_URI/USERNAME/PASSWORD
# 전체 목록: .env.example 참조
createdb stock_vis && python manage.py migrate
python manage.py runserver
```

### Frontend

```bash
cd frontend && npm install && npm run dev
```

### Celery + Redis

```bash
brew services start redis
celery -A config worker -l info                          # default queue
celery -A config worker -Q neo4j -l info --pool=solo     # neo4j queue (fork 없이)
celery -A config beat -l info
```

---

## 아키텍처 요약

**Backend 3계층 패턴**: `API Client → Processor → Service → Models/Views → REST API`

| 앱 | 역할 | 상세 |
|----|------|------|
| stocks | 주가, 재무제표 | `/api/v1/stocks/*` |
| users | 사용자, Watchlist | `/api/v1/users/*` |
| analysis | 기술적 지표 | `/api/v1/analysis/*` |
| macro | Market Pulse (거시경제) | `/api/v1/macro/*` |
| graph_analysis | 상관관계 그래프 (모델/서비스만 구현, API 미구현) | ⏳ `/api/v1/graph/*` |
| news | 뉴스 기반 종목 인사이트 | `/api/v1/news/*` |
| rag_analysis | LLM 기반 RAG 분석 | `/api/v1/rag/*` |
| serverless | Market Movers, Screener, Chain Sight, 키워드 | `/api/v1/serverless/*` |
| thesis | 가설 통제실 (빌더, 관제실, 알림) | `/api/v1/thesis/*` |
| metrics | 공유 지표 메타데이터 + 배치 실행 이력 | (내부 서비스) |
| validation | 1차 검증 (Peer 비교, 벤치마크) | `/api/v1/validation/*` |
| chainsight | 기업 프로파일 (성장단계, 자본DNA, 민감도) | `/api/v1/chainsight/*` |
| sec_pipeline | SEC EDGAR 파이프라인 (Supply Chain + Business Model) | `/api/v1/sec/*` |

> 상세: [sub_claude_md/architecture.md](sub_claude_md/architecture.md), [sub_claude_md/api-endpoints.md](sub_claude_md/api-endpoints.md)

---

## 코딩 규칙 (필수)

### Backend
- `symbol.upper()` 필수, `get_object_or_404(Stock, symbol=symbol.upper())`
- Processor에 `return` 문 필수, 가격 모델은 `DailyPrice` (HistoricalPrice 없음)
- Celery 태스크: idempotent, max_retries=3, exponential backoff
- LLM 호출: Celery에서는 **동기 API만** 사용 (`genai.Client` sync)

### Frontend
- TypeScript strict mode, TanStack Query (서버 상태), Zustand (클라이언트 상태)
- `NEXT_PUBLIC_API_URL`에 `/api/v1` 포함 → 코드에서 중복 금지

### 외부 API Rate Limits
- **Alpha Vantage**: 5 calls/분, 12초 대기 필수
- **FMP**: 10 calls/분, `/stable/*` 경로만 사용 (Legacy `/api/v3/*` 지원 안 함)
- **Gemini Free**: 15 RPM, 1500 RPD

> 상세: [sub_claude_md/coding-rules.md](sub_claude_md/coding-rules.md)

---

## 자주 발생하는 버그 (핵심 8개)

| # | 버그 | 핵심 해결 |
|---|------|----------|
| 8 | Celery에서 async LLM 호출 | 동기 API만 사용 |
| 14 | FMP Key Metrics 필드명 불일치 | `earningsYieldTTM` 역수 = PE, `returnOnEquityTTM` * 100 = ROE |
| 15 | 캐시 키 불일치 | 읽기/쓰기/삭제 모두 동일 키 패턴 |
| 16-17 | SPDR XLSX 파싱 | `PK\x03\x04` 감지 + `list(iter_rows())` |
| 19 | API URL 중복 `/api/v1/api/v1` | `.env` 확인, 코드에서 중복 제거 |
| 20 | Next.js dev lock 충돌 | `predev` 스크립트로 `.next/dev/lock` 자동 삭제 |
| 21 | Chain Sight count만 표시, 목록 빈 배열 | `ETF_PEER`→ETFHolding, `HAS_THEME`→ThemeMatch 분기 |
| 22 | 재무제표 저장 시 모델 필드명 불일치 | `fiscal_date_ending`→`reported_date`, `accounts_payable`→`current_accounts_payable` 등 6개 |
| 23 | FMP 프리미엄 심볼 402 에러 | `FMPPremiumError` 즉시 실패 + `.` 포함 심볼 배치에서 제외 |
| 24 | Next.js Client Component Date.now() hydration 불일치 | 모듈 레벨 `Date.now()` 금지, 고정값 또는 `useEffect` 사용 |
| 25 | Celery macOS SIGSEGV (fork + Obj-C) | `OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES` + `PGGSSENCMODE=disable` + fork 후 `db.connections.close_all()` |
| 26 | Validation peer group 전환 안 됨 | `selectPreset` 등 POST/DELETE에서 raw `fetch()` → `authAxios` (JWT 필수) |

> 전체 버그 상세: [sub_claude_md/common-bugs.md](sub_claude_md/common-bugs.md)

---

## 주요 기능별 상세 문서

| 기능 | 상세 문서 |
|------|----------|
| EOD Dashboard (14개 시그널, JSON Baking) | [sub_claude_md/eod-dashboard.md](sub_claude_md/eod-dashboard.md) |
| Market Movers (5개 지표, Corporate Action) | [sub_claude_md/market-movers.md](sub_claude_md/market-movers.md) |
| AI 키워드 생성 (Gemini + Celery) | [sub_claude_md/ai-keywords.md](sub_claude_md/ai-keywords.md) |
| News 기반 종목 인사이트 + 수집 카테고리 + Intelligence Pipeline v3 | [sub_claude_md/news-insights.md](sub_claude_md/news-insights.md) |
| Chain Sight (ETF, Supply Chain, LLM, Neo4j) | [sub_claude_md/chain-sight.md](sub_claude_md/chain-sight.md) |
| Graph Analysis (상관관계 온톨로지) | [sub_claude_md/graph-analysis.md](sub_claude_md/graph-analysis.md) |
| Screener (Enhanced + 투자 테제) | [sub_claude_md/screener.md](sub_claude_md/screener.md) |
| RAG Analysis (Phase 3 파이프라인) | [sub_claude_md/rag-analysis.md](sub_claude_md/rag-analysis.md) |
| Thesis Control (가설 통제실, 화살표/달 시각화) | [sub_claude_md/thesis-control.md](sub_claude_md/thesis-control.md) |
| 1차 검증 (Peer 비교, 프리셋, LLM 필터) | `docs/first_validation_system/` |
| Chain Sight v2 (프로파일, 관계, Neo4j GDS) | `docs/chain_sight/plan/` |
| SEC Pipeline (10-K 공급망 + 사업모델) | `docs/sec_pipeline/` |

---

## 멀티에이전트 담당

| 에이전트 | 영역 |
|---------|------|
| @backend | stocks/, users/, analysis/, API_request/, serverless/, news/, macro/, thesis/, metrics/, validation/, chainsight/, sec_pipeline/ |
| @frontend | frontend/ 전체 |
| @rag-llm | rag_analysis/ 전체 |
| @infra | */tasks.py, */consumers.py, config/, docker/ |
| @qa | tests/, docs/ |

> 상세: [sub_claude_md/multi-agent.md](sub_claude_md/multi-agent.md)

---

## 구현 상태 요약

### 완료
JWT, Portfolio, 기술지표, Watchlist, Market Pulse, Market Movers (5개 지표 + Corporate Action + AI 키워드), Screener (Enhanced + 테제 빌더 + Chain Sight DNA), Chain Sight v1 (ETF Holdings + Supply Chain + LLM Relations + Neo4j + Institutional Holdings + Regulatory/Patent), RAG Phase 3, Stock Auto Sync, News 수집 카테고리 (sector/sub_sector/custom + Celery Beat), **News Intelligence Pipeline v3** (규칙 엔진 + LLM 분석 + ML 학습 + Neo4j 뉴스 이벤트 + Shadow/Production Mode + LightGBM, 테스트 607개), **EOD Dashboard** (14개 시그널 벡터 연산 + VIX 레짐 + JSON Baking + Atomic Write + 5단계 뉴스 매칭 + 메인 페이지), **Thesis Control 백엔드** (Views, Serializers, Builder, Tasks), **Thesis Control 프론트엔드 Phase 2** (FE-PR-1~6 완료: 라우팅 + 공통 컴포넌트 + 가설 목록 + 대화형 빌더 + 지표 설정 + 관제실 대시보드 + 알림/마감), **관제실 지표 설명** (INDICATOR_CATALOG description 73개 + recommendation_reason 저장), **1차 검증** (Peer 프리셋 6종 + Compute-on-Read 엔진 + LLM 대화형 필터 + 커스텀 Peer), **Chain Sight v2 Phase 0~5** (기업 프로파일 + 관계 파이프라인 + Neo4j GDS + REST API 3개 + 프론트엔드 그래프 시각화), **SEC Pipeline** (10-K Supply Chain + Business Model 추출)

### 진행 중
**Thesis Control Phase 3** (깊이 + 회고 + 프로필: FE-PR-7~11), **Chain Sight v2 프론트엔드 개선** (redesign v1), **서비스 리모델링** (데이터 구조 개편)

### 보류
Market Movers AWS Lambda 전환, Graph Analysis (모델/서비스 완료, API 미구현)

> 상세: [sub_claude_md/completed-features.md](sub_claude_md/completed-features.md)

---

## 문서화

- 플랜 모드 진입 시 `docs/features/` 에 설계 문서 생성
- 구현 완료 후 CLAUDE.md 반영
- 로그: `stocks.log`, `logger = logging.getLogger(__name__)`

> 상세: [sub_claude_md/documentation.md](sub_claude_md/documentation.md)
