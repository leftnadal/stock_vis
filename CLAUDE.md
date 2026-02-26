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
celery -A config worker -l info
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

## 자주 발생하는 버그 (핵심 6개)

| # | 버그 | 핵심 해결 |
|---|------|----------|
| 8 | Celery에서 async LLM 호출 | 동기 API만 사용 |
| 14 | FMP Key Metrics 필드명 불일치 | `earningsYieldTTM` 역수 = PE, `returnOnEquityTTM` * 100 = ROE |
| 15 | 캐시 키 불일치 | 읽기/쓰기/삭제 모두 동일 키 패턴 |
| 16-17 | SPDR XLSX 파싱 | `PK\x03\x04` 감지 + `list(iter_rows())` |
| 19 | API URL 중복 `/api/v1/api/v1` | `.env` 확인, 코드에서 중복 제거 |
| 20 | Next.js dev lock 충돌 | `predev` 스크립트로 `.next/dev/lock` 자동 삭제 |
| 21 | Chain Sight count만 표시, 목록 빈 배열 | `ETF_PEER`→ETFHolding, `HAS_THEME`→ThemeMatch 분기 |

> 전체 21개 버그 상세: [sub_claude_md/common-bugs.md](sub_claude_md/common-bugs.md)

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

---

## 멀티에이전트 담당

| 에이전트 | 영역 |
|---------|------|
| @backend | stocks/, users/, analysis/, API_request/, serverless/, news/, macro/ |
| @frontend | frontend/ 전체 |
| @rag-llm | rag_analysis/ 전체 |
| @infra | */tasks.py, */consumers.py, config/, docker/ |
| @qa | tests/, docs/ |

> 상세: [sub_claude_md/multi-agent.md](sub_claude_md/multi-agent.md)

---

## 구현 상태 요약

### 완료
JWT, Portfolio, 기술지표, Watchlist, Market Pulse, Market Movers (5개 지표 + Corporate Action + AI 키워드), Screener (Enhanced + 테제 빌더 + Chain Sight DNA), Chain Sight (ETF Holdings + Supply Chain + LLM Relations + Neo4j + Institutional Holdings + Regulatory/Patent), RAG Phase 3, Stock Auto Sync, News 수집 카테고리 (sector/sub_sector/custom + Celery Beat), **News Intelligence Pipeline v3** (규칙 엔진 + LLM 분석 + ML 학습 + Neo4j 뉴스 이벤트 + Shadow/Production Mode + LightGBM, 테스트 607개), **EOD Dashboard** (14개 시그널 벡터 연산 + VIX 레짐 + JSON Baking + Atomic Write + 5단계 뉴스 매칭 + 메인 페이지)

### 진행 중
Graph Analysis (모델/서비스 완료, urls.py+tasks.py 미구현, 시각화 미구현), Chain Sight 프론트엔드 그래프 시각화

### 보류
Market Movers AWS Lambda 전환

> 상세: [sub_claude_md/completed-features.md](sub_claude_md/completed-features.md)

---

## 문서화

- 플랜 모드 진입 시 `docs/features/` 에 설계 문서 생성
- 구현 완료 후 CLAUDE.md 반영
- 로그: `stocks.log`, `logger = logging.getLogger(__name__)`

> 상세: [sub_claude_md/documentation.md](sub_claude_md/documentation.md)
