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
- **FMP** (Starter Plan): 300 calls/분, 10,000 calls/일, `/stable/*` 경로만 사용 (Legacy `/api/v3/*` 지원 안 함)
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
| 27 | pytest가 운영 Redis flush (Chain Sight 시드 증발) | `settings_test.py`에 LocMemCache 격리 + `SeedSnapshot` DB 영속화 + 3단 폴백 |
| 28 | Beat schedule drift (config dict vs DB) | DatabaseScheduler 사용 시 dict는 무시됨, `PeriodicTask.objects.create(...)`로 DB 등록 |

> 전체 버그 상세: [sub_claude_md/common-bugs.md](sub_claude_md/common-bugs.md)
> 배포 체크리스트(마이그레이션·env 인라인 포함 슬라이스 — 단일 출처): [sub_claude_md/common-bugs.md](sub_claude_md/common-bugs.md) "배포 체크리스트" 항목 (#53~#55 짝)

---

## 주요 기능별 상세 문서

| 기능 | 상세 문서 |
|------|----------|
| EOD Dashboard (14개 시그널, JSON Baking) | [sub_claude_md/eod-dashboard.md](sub_claude_md/eod-dashboard.md) |
| Market Movers (5개 지표, Corporate Action) | [sub_claude_md/market-movers.md](sub_claude_md/market-movers.md) |
| AI 키워드 생성 (Gemini + Celery) | [sub_claude_md/ai-keywords.md](sub_claude_md/ai-keywords.md) |
| News 기반 종목 인사이트 + 수집 카테고리 + Intelligence Pipeline v3 | [sub_claude_md/news-insights.md](sub_claude_md/news-insights.md) |
| Chain Sight (ETF, Supply Chain, LLM, Neo4j) | [sub_claude_md/chain-sight.md](sub_claude_md/chain-sight.md) |
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
| @qa | tests/, docs/ + Evaluator 역할 (다른 에이전트 산출물 검증) |
| @investment-advisor | 투자 도메인 콘텐츠, 용어 설명, UX 관점 조언 |
| @kb-curator | shared_kb/ 전체 — KB 큐레이션, 품질 관리, Neo4j 지식 그래프 |
| @UI-UX-designer | 화면 설계, 컴포넌트 스펙, 인터랙션 플로우 — 코드 작성 안 함 |

> 상세: [sub_claude_md/multi-agent.md](sub_claude_md/multi-agent.md)

---

## 구현 상태 요약

### 완료
JWT, Portfolio, 기술지표, Watchlist, Market Pulse, Market Movers (5개 지표 + Corporate Action + AI 키워드), Screener (Enhanced + 테제 빌더 + Chain Sight DNA), Chain Sight v1 (ETF Holdings + Supply Chain + LLM Relations + Neo4j + Institutional Holdings + Regulatory/Patent), RAG Phase 3, Stock Auto Sync, News 수집 카테고리 (sector/sub_sector/custom + Celery Beat), **News Intelligence Pipeline v3** (규칙 엔진 + LLM 분석 + ML 학습 + Neo4j 뉴스 이벤트 + Shadow/Production Mode + LightGBM, 테스트 607개), **EOD Dashboard** (14개 시그널 벡터 연산 + VIX 레짐 + JSON Baking + Atomic Write + 5단계 뉴스 매칭 + 메인 페이지), **Thesis Control 백엔드** (Views, Serializers, Builder, Tasks), **Thesis Control 프론트엔드 Phase 2** (FE-PR-1~6 완료: 라우팅 + 공통 컴포넌트 + 가설 목록 + 대화형 빌더 + 지표 설정 + 관제실 대시보드 + 알림/마감), **관제실 지표 설명** (INDICATOR_CATALOG description 73개 + recommendation_reason 저장), **1차 검증** (Peer 프리셋 6종 + Compute-on-Read 엔진 + LLM 대화형 필터 + 커스텀 Peer), **Chain Sight v2 Phase 0~5** (기업 프로파일 + 관계 파이프라인 + Neo4j GDS + REST API 3개 + 프론트엔드 그래프 시각화), **SEC Pipeline** (10-K Supply Chain + Business Model 추출)

### 진행 중
**Thesis Control Phase 3** (깊이 + 회고 + 프로필: FE-PR-7~11), **Chain Sight v2 프론트엔드 개선** (redesign v1), **서비스 리모델링** (데이터 구조 개편)

### 보류
Market Movers AWS Lambda 전환

> 상세: [sub_claude_md/completed-features.md](sub_claude_md/completed-features.md)

---

## 문서화

- 플랜 모드 진입 시 `docs/features/` 에 설계 문서 생성
- 구현 완료 후 CLAUDE.md 반영
- 로그: `stocks.log`, `logger = logging.getLogger(__name__)`

> 상세: [sub_claude_md/documentation.md](sub_claude_md/documentation.md)

---

## Harness Protocol

> "Agent = Model + Harness" — 모델 외부의 모든 인프라(컨텍스트, 상태, 오케스트레이션, 검증)를 체계적으로 관리한다.

> **교차 앱 규약의 단일 출처 = repo 하네스.** dashboard·chain_sight·market_pulse 공통으로 적용될 규약·세션 DoD·금지사항은 **여기(repo 하네스)에 한 번만** 정의한다. 각 Claude.ai 프로젝트의 공용 코어/참조 문서는 이 단일 출처의 **파생 투영**이며, 새 교차 규칙을 코어에 직접 복제하지 않는다(규약 10장 — 복제는 drift). 코어에는 "단일 출처는 repo"라는 포인터만 둔다.

### 하네스 핵심 파일

| 파일 | 역할 | 갱신 주기 |
|------|------|----------|
| `PROGRESS.md` | 세션 간 상태 영속화 | 매 세션 종료 시 |
| `DECISIONS.md` | 아키텍처 결정 단일 소스 | 결정 변경 시 |
| `TASKQUEUE.md` | 에이전트 간 태스크 오케스트레이션 | 태스크 상태 변경 시 |
| `contracts/` | API 인터페이스 계약 (OpenAPI + 공유 타입) | API 변경 시 |
| `shared_kb/` | OAG 지식 그래프 (교훈, 패턴, 트러블슈팅) | 교훈 발생 시 |

### Session Lifecycle

> 세션 격리·git 충돌 방지: [`docs/harness/SESSION_CONTRACT.md`](docs/harness/SESSION_CONTRACT.md) (소프트 강제 = worktree + 계약 헤더). 세션 시작 시 §C 헤더를 채워 commit 허용·금지 경로와 종료 절차를 명시한다.

1. **세션 시작**: `PROGRESS.md` → `DECISIONS.md` → `TASKQUEUE.md` 순서로 읽는다
2. **KB 컨텍스트 로드**: 현재 태스크 관련 키워드로 `shared_kb/search.py` 조회 — 이전 교훈/트러블슈팅 확인
   - 예: Celery 태스크 작업 시 → `python -m shared_kb.search "Celery" --type troubleshoot`
   - 예: Chain Sight 작업 시 → `python -m shared_kb.search "Chain Sight" --domain tech`
3. **작업 중**: 컨텍스트 50% 초과 시 compaction 수행 (아래 규칙 참조)
4. **세션 종료**: 반드시 아래를 수행한다
   - `PROGRESS.md` 업데이트 (현재 상태, blocker, 다음 할 일)
   - 변경된 contract 파일 업데이트
   - `TASKQUEUE.md`에서 완료 태스크 상태 변경
   - **KB 쓰기 고리 완성** (큐는 종착지가 아니다 — 마지막 칸까지):
     1. 교훈을 **1차 소스에 먼저 직접 기록** — 버그·함정 → `sub_claude_md/common-bugs.md`, 결정 → `DECISIONS.md` (큐 경유 아님)
     2. `shared_kb` 큐 **드레인 실행** — 밀린 항목 + 당 세션분을 검색KB로 반영 (`python -m shared_kb.curate`)
     3. 교훈 0건이면 PROGRESS 종료 메모에 **"교훈 없음" 명시** (빈손 종료 금지)
   - (아래 "Knowledge Base 연동 규칙" 참조)
   - **지시서 폐기 전 흡수 확인**: 실행 지시서(`*_지시서.md`)는 휘발성 → repo에 보관하지 않고 폐기한다. 단 폐기/세션 종료 전, 지시서 내 **비자명 결정의 '왜'가 `DECISIONS.md`에 한 줄 이상 흡수**됐고 관련 커밋이 **task ID로 추적 가능**한지 확인한다. (자명한 실행 디테일·STEP 0 측정값·Pseudocode·DoD는 흡수 대상 아님 — 휘발성이므로.)

### Plan Mode Handoff Protocol

플랜모드에서는 Edit/Write가 불가하므로 **지연 커밋(Deferred Commit)** 패턴을 사용한다.

**플랜모드 진입 시 (1~2단계 동일)**:
1. PROGRESS.md, DECISIONS.md, TASKQUEUE.md 읽기 — **가능**
2. KB 검색 (`python -m shared_kb.search`) — **가능**
3. 기존 설계 문서, contracts/ 스펙 읽기 — **가능**

**플랜모드 작업 중**:
- 설계 결과를 **대화 내에서 구조화된 텍스트로 출력**
- 아래 형식으로 "지연 커밋 블록"을 남긴다:

```
## Deferred Commits (플랜모드 종료 후 실행)

### PROGRESS.md 업데이트
- 활성 작업: [내용]
- 다음 할 일: [내용]

### DECISIONS.md 추가
- 결정: [내용]
- Why: [근거]

### TASKQUEUE.md 변경
- [태스크 ID]: [상태 변경]

### contracts/ 변경
- [파일]: [변경 내용]

### KB 큐 추가
- 타입: [LESSON/PATTERN/TROUBLESHOOT/DECISION]
- 제목: [내용]
- 내용: [상세]

### 설계 문서 생성
- 경로: docs/features/[feature]/[design].md
- 내용: [전체 설계 내용]
```

**플랜모드 종료 후 (구현 세션 시작 시)**:
1. 직전 플랜의 Deferred Commits 블록을 확인
2. 각 항목을 순서대로 실제 파일에 반영 (Edit/Write)
3. 반영 완료 후 구현 작업 시작

이렇게 하면 플랜모드의 설계 결과가 하네스 파일에 **누락 없이** 반영된다.

### Context Management Rules

- **Tool Output Offloading**: 테스트 결과, lint 출력, migration 로그 등 50줄 초과 출력은 파일로 저장하고 경로+요약만 컨텍스트에 유지
  - 패턴: `"47 passed, 2 failed → /tmp/test_results_20260412.log"`
- **Compaction Trigger**: 이전 PR/태스크 결과는 1줄 요약으로 압축
  - 패턴: `"PR-1 완료: CompanyFinancials 모델 + migration 0001 생성"`
- **Stale Context 제거**: 3단계 이전의 tool call 원본 출력은 참조하지 않는다

### Agent Dependency Graph

```
UI-UX-designer ──→ frontend (디자인 명세 확정 후 구현)
backend ──→ frontend (API contract 확정 후)
backend ──→ qa (코드 완료 후 검증)
kb-curator ──→ investment-advisor (지식 업데이트 후 콘텐츠 생성)
infra ──→ all (인프라 변경은 전체 영향)
rag-llm ──→ backend (RAG 분석 결과 → API 통합)
```

### Contract-Driven Development

- **@backend**가 API 변경 시 `contracts/` 하위 OpenAPI 스펙을 **먼저** 업데이트
- **@frontend**는 `contracts/` 스펙을 기준으로 타입과 API 호출 코드 생성
- **스펙과 구현이 불일치하면 구현 쪽을 수정한다** (스펙이 진실의 소스)
- 공유 타입: `contracts/shared-types.ts`

### Error Message as Teaching

- pre-commit, lint, test 실패 메시지는 "수정 방법을 가르치는" 형태로 작성
- Bad: `"AssertionError in test_xxx"`
- Good: `"test_peer_selection 실패: PeerGroup.get_peers()가 size_bucket 파라미터를 받지 않음. models.py의 get_peers 시그니처에 size_bucket: str = 'all' 추가 필요"`

### Knowledge Base 연동 규칙

**KB 큐 자동 추가 트리거** — 아래 상황 발생 시 `shared_kb/queue`에 자동 등록:

| 트리거 | knowledge_type | 예시 |
|--------|---------------|------|
| 버그 수정 완료 | `TROUBLESHOOT` | "FMP 402 에러 → FMPPremiumError + `.` 심볼 제외" |
| 새 아키텍처 결정 | `DECISION` | "neo4j_dirty 플래그 패턴 채택 (synced_to_neo4j 대신)" |
| 반복되는 실수 발견 | `LESSON` | "Celery에서 async LLM 호출 금지 — 동기 API만" |
| 코딩 패턴 정립 | `PATTERN` | "authAxios 단일 소스로 JWT 인터셉터 통일" |
| @qa 검증에서 이슈 발견 | `LESSON` | "contracts/ 스펙과 실제 API 응답 6건 불일치 — 사후 맞춤 위험" |

> ⚠️ **큐는 종착지가 아니다**: 큐 등록은 마지막 칸이 아니다. 세션 종료 의식에서 **검색KB로 드레인**(`python -m shared_kb.curate`)해야 `python -m shared_kb.search`로 다음 세션이 찾을 수 있다. 큐 미드레인이 누적되면 pre-commit hook이 stderr 경고(차단 아님). 흐름: **1차 소스 먼저 → 큐(복사본) → 드레인(검색KB)**.

**DECISIONS.md ↔ KB 동기화 원칙**:
- `DECISIONS.md`가 아키텍처 결정의 **1차 소스** (에이전트가 즉시 참조)
- KB `DECISION` 타입은 **장기 보존 + 검색용** 복사본 (Why/Context 포함)
- 새 결정 → **DECISIONS.md 먼저** → KB 큐에 DECISION 추가 → **세션 종료 시 검색KB 드레인**

**common-bugs.md ↔ KB 동기화 원칙**:
- `common-bugs.md`가 버그의 **1차 소스** (빠른 참조용, 번호 체계)
- KB `TROUBLESHOOT` 타입은 **상세 해결 과정 + 검색용** (재발 방지)
- 새 버그 → **common-bugs.md 먼저** → KB 큐에 TROUBLESHOOT 추가 → **세션 종료 시 검색KB 드레인**

### PR Completion Checklist (공통)

모든 에이전트는 PR 완료 전 자가 검증:
- [ ] `DECISIONS.md` 결정사항 위반 없음
- [ ] `contracts/` 스펙과 구현 일치
- [ ] `TASKQUEUE.md` 상태 업데이트
- [ ] `PROGRESS.md` 현재 상태 반영
- [ ] 세션 중 교훈이 있었다면 KB 큐에 추가했는가?

## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken", 500 errors → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- QA, test the site, find bugs → invoke qa
- Code review, check my diff → invoke review
- Update docs after shipping → invoke document-release
- Weekly retro → invoke retro
- Design system, brand → invoke design-consultation
- Visual audit, design polish → invoke design-review
- Architecture review → invoke plan-eng-review
- Save progress, checkpoint, resume → invoke checkpoint
- Code quality, health check → invoke health
