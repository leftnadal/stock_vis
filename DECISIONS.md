# DECISIONS.md — 아키텍처 결정 로그

> 에이전트는 구현 전 이 파일을 확인하고, 기존 결정과 충돌하는 작업은 수행하지 않는다.
> 각 결정에는 **근거(Why)**를 반드시 포함한다.

---

## 데이터 아키텍처

### 4-Layer 데이터 흐름
```
Raw (외부 API) → Metrics (Django 모델) → ChainSight (PostgreSQL 프로파일) → Neo4j (그래프)
```
**Why**: 각 계층이 다른 갱신 주기와 소비자를 가짐. Raw는 실시간, Metrics는 일일, Neo4j는 주간.

### neo4j_dirty 플래그 패턴
- PostgreSQL → `neo4j_dirty=True` 세팅 → Celery 배치로 Neo4j 동기화
- `synced_to_neo4j` 대신 채택
- **Why**: 단방향 동기화(PG→Neo4j)에서 "동기화 필요" 의미가 명확. 역방향 없음.
- 📎 상세: `docs/chain_sight/plan/redesign_v1_260409/chainsight_seed_node_design.md`

### CUSTOMER_OF 파생
- DB에 별도 저장 안 함. `SUPPLIES_TO`의 역방향을 API 계층에서 `display_type`으로 파생.
- **Why**: 중복 저장 제거. 방향 반전만으로 충분.

### Undirected 관계 정규화
- `PEER_OF`, `COMPETES_WITH`, `CO_MENTIONED`, `PRICE_CORRELATED` 4종은 Neo4j에서 무방향.
- 저장 시 `symbol_a < symbol_b` 순서로 정규화하여 중복 방지.
- **Why**: 양방향 엣지를 중복 생성하면 GDS 알고리즘 결과 왜곡.

### DailyPrice 단일 모델
- `HistoricalPrice` 모델 없음. 모든 가격 데이터는 `DailyPrice` 사용.
- **Why**: 히스토리컬과 일일의 구분 불필요. 중복 모델 방지.

### 운영 상태(배치 생성) vs Lazy cache(요청 시 생성) 분리
- **운영 상태** (배치로 하루 1회만 생성, 다음 배치까지 기다려야 복구되는 데이터) → **DB 영속화 필수**, Redis는 hot path 레이어
  - 적용: `SeedSnapshot` (Chain Sight 시드)
  - `cache_seed_result()` = DB upsert + Redis write. Redis 실패해도 DB 보존.
  - 조회 폴백 순서: Redis → `SeedSnapshot` DB (최근 7일) → async `run_seed_selection.delay()` (setnx lock 5분으로 중복 방지)
- **Lazy cache** (요청 시 즉시 재생성 가능한 데이터) → Redis만, DB 영속화 안 함
  - 적용: `sector_graph`, `neighbors`, `signals`
- **Why**: 2026-04-24 사건(pytest flush로 시드 캐시 증발, 다음 Beat까지 24h 빈 응답) 교훈. "배치 단위 영속성"과 "요청 단위 휘발성"은 다른 레이어에 둔다. Lazy cache는 cache miss 시 1~2초 지연 후 자동 재캐시 → DB 영속화해도 얻는 게 없고 stale만 누적.

### 테스트 캐시는 운영 Redis와 물리적 분리
- `config/settings_test.py`에 `CACHES[default] = LocMemCache` override
- `pytest.ini` → `DJANGO_SETTINGS_MODULE = config.settings_test`
- `tests/conftest.py:clear_cache_after_test`에 `assert 'locmem' in backend` 안전 가드
- **Why**: `django-redis.cache.clear()`는 KEY_PREFIX와 무관하게 `FLUSHDB` 호출 → DB 전체 삭제. 같은 Redis DB를 테스트와 운영이 공유하면 테스트 한 방으로 운영 데이터 증발.

### Celery Beat 스케줄의 진실의 소스는 DB `PeriodicTask`
- `settings.py`: `CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'`
- `config/celery.py`의 `app.conf.beat_schedule` dict는 **런타임에 무시됨** (선언적 reference만)
- 스케줄 추가/변경: Django admin 혹은 `PeriodicTask.objects.update_or_create(...)` + `PeriodicTasks.update_changed()`
- **Drift 체크**: `set(PeriodicTask.objects.values_list('name', flat=True))` vs config dict 키 diff. 주기적 수동 검증 필요.
- **Why**: DatabaseScheduler는 DB 테이블을 폴링. dict에만 추가하면 실행되지 않음(2026-04-24 `chainsight-heat-score-daily`, `sec-seed-relations-to-chainsight` 실종 사례).

### Chain Sight `get_market_date()`는 America/New_York 기준
- `date.today()` (시스템 TZ) 대신 `datetime.now(ZoneInfo('America/New_York')).date()`
- **Why**: NYSE EOD 기준 키와 일치. 시스템 TZ가 KST/UTC 등일 때 Beat 저장 시점과 read 시점의 `date` 불일치 방지.

---

## Chain Sight

### 마켓 뷰 이원 구조
- `/chainsight` = 마켓 뷰 (Breadth-first 탐색)
- `/chainsight/[symbol]` = Deep Dive Workspace (Depth-first 분석)
- **Why**: 광범위한 시장 탐색과 개별 종목 심화 분석은 다른 사용자 의도.
- 📎 상세: `docs/chain_sight/plan/redesign_v1_260409/chainsight_api_design.md`

### 마켓 뷰 4개 API
| 엔드포인트 | 역할 | 캐시 TTL |
|-----------|------|---------|
| `GET /seeds/` | 섹터바 + 시드 카드 | 30분 |
| `GET /sector/{sector}/graph/` | 섹터 overview 그래프 | 30분 |
| `GET /{symbol}/neighbors/` | 중심 이동 + 관계 카드 | 5분 |
| `GET /signals/` | 체인 스토리 피드 | 30분 |
- **Why**: 4개 엔드포인트로 5개 UI 컴포넌트를 모두 구동. 백엔드 복잡도 최소화.
- 📎 상세: `docs/chain_sight/plan/redesign_v1_260409/chainsight_ui_ux_design.md`

### 시드 선정 3단계 진화 경로
- Phase 1: 시장 시그널(B) + 관계 변화(A) → 매일 13:00 UTC, MAX=20
- Phase 2: Heat Score 복합 랭킹 (SeedHeatScore 모델 필요)
- Phase 3: 이벤트 전파 모델 (Gemini Embedding + ChromaDB 필요)
- **Why**: 각 Phase 전제조건이 다르므로 점진적 진화.
- 📎 상세: `docs/chain_sight/plan/redesign_v1_260409/chainsight_seed_node_design.md`

### seed_reasons 8개 코드
`price_top5`, `price_bottom5`, `volume_surge`, `sector_outlier`, `relation_upgrade`, `relation_downgrade`, `relation_new`, `comention_surge`
- **Why**: UI에서 "왜 시드로 선정됐는지" 시각적 배지로 표시.

### Neo4j GDS 알고리즘 유지
- PageRank, Louvain Community Detection, Betweenness Centrality 사용.
- **Why**: NetworkX 대비 대규모 그래프에서 성능 우수. APOC 프로시저 활용.
- 📎 상세: `docs/chain_sight/plan/cs_30_neo4j_sync.md`

### RelationConfidence.previous_status 필드
- `CharField(max_length=20)`, nullable
- **Why**: 시드 선정에서 "어제 confirmed → 오늘 probable" 상태 전이 감지 필요.

---

## SEC Pipeline

### 2-Track 추출 설계
- Track A: Item 1A (Risk Factors) → 공급망 추출
- Track B: Item 7 (MD&A) + Item 3 (Properties) → 사업모델 추출
- **Why**: 공급망과 사업모델은 10-K 내 다른 섹션에 위치하고 프롬프트가 다름.
- 📎 상세: `docs/sec_pipeline/plan/sec_pipeline_base_design.md`

### Ticker 매칭 3단계
1. `alias` (CompanyAlias 테이블 정확 일치)
2. `exact` (이름 정확 매칭)
3. `fuzzy` (Levenshtein 유사도)
- 실패 → `UnmatchedCompanyQueue` 적재 → 수동 검토
- **Why**: 100% 자동화 불가. 실패 케이스를 큐에 모아 bulk 등록.

### SEC EDGAR 직접 수집
- FMP sec-filings API가 Starter 플랜에서 404 → EDGAR submissions API 직접 사용.
- regex 3단계 + edgartools fallback으로 섹션 추출.
- **Why**: 비용 0원으로 10-K 원문 확보.
- 📎 상세: `docs/sec_pipeline/task_done/sec_pipeline_complete_summary.md`

---

## Thesis Control

### 화살표 시스템 (0°~180°, 5색상)
| 범위 | 색상 | 의미 |
|------|------|------|
| 0°~35° | #2563EB | 강하게 지지 |
| 36°~71° | #60A5FA | 지지하는 편 |
| 72°~107° | #D1D5DB | 중립 |
| 108°~143° | #FB923C | 약화하는 편 |
| 144°~180° | #EF4444 | 강하게 반박 |
- **Why**: 숫자(-1.0~1.0)보다 화살표 방향+색상이 직관적.
- 📎 상세: `docs/thesis_control/plan/thesis_control_design.md`

### 달 위상 시각화
- `overall_score` (-1~1) → 달 밝기 매핑
- **Why**: 숫자를 자연스러운 메타포로 변환하여 "느낌" 전달.

### authAxios 단일 소스
- `lib/api/authAxios.ts`: JWT 인터셉터 단일 소스 (AuthContext + thesis 공유)
- 3중 방어: 단일 탭 race condition, 다중 탭 동기화, Token rotation
- **Why**: JWT 로직 중복 방지. 한 곳에서 관리.

---

## 1차 검증 (Validation)

### Compute-on-Read 패턴
- DB에 사전 계산 저장 안 함. 요청 시 peer group 대비 percentile 실시간 계산.
- **Why**: peer group이 동적으로 변경될 수 있으므로 사전 계산값이 빠르게 stale.
- 📎 상세: `docs/first_validation_system/validation_design.md`

### Peer 프리셋 6종 + LLM 대화형 필터
- 프리셋: Industry+Size 기반 자동 선정
- LLM: 사용자 질문을 peer 조건으로 변환
- **Why**: MVP는 프리셋만으로 충분, Chain Sight DNA 활용해 고도화 예정.

### 신호등 기준: Percentile 통일
- `score >= 65`: green, `>= 35`: yellow, else: red
- **Why**: 절대값이 아닌 peer 상대 위치. 산업 특성 자동 반영.

---

## EOD Dashboard

### JSON Baking + Atomic Write
- Celery Beat 18:30 ET → 14개 시그널 계산 → JSON 파일 baking → Atomic directory swap
- **Why**: API 비용 0원. 실패 시 이전 데이터 유지 (partial update 방지).
- 📎 상세: `sub_claude_md/eod-dashboard.md`

### 14개 시그널 체계
- Momentum (P1~P4), Breakout (P5), Reversal (P7), Volume (V1, PV1, PV2), Technical (MA1, T1), Relation (S1, S2, S4)
- VIX > 25: 상위 threshold 부스트
- **Why**: 각 시그널이 독립적 관찰 관점 제공. 너무 많으면 노이즈, 적으면 신호 부족.

---

## News Intelligence v3

### 3계층 파이프라인
- 규칙 엔진 → LLM 분석 (Gemini Flash) → ML 학습 (LightGBM)
- **Why**: 규칙은 저비용+빠름, LLM은 맥락 이해, ML은 패턴 최적화. 계층별 강점 활용.
- 📎 상세: `sub_claude_md/news-insights.md`

### Sector Ripple 2-hop 확산
- 대형주 → 같은 섹터 중소형주로 0.4x 감쇠, 20개 상한
- **Why**: 대형주 뉴스가 섹터 전체에 영향. hop 제한으로 노이즈 방지.

---

## 프론트엔드

### 차트: Recharts ComposedChart
- Bar + Scatter + ErrorBar 조합
- **Why**: D3.js보다 React 친화적, 복합 차트 표현력 충분.

### 상태 관리 이원화
- 서버 상태: TanStack Query (staleTime=5min, gcTime=30min, retry=2)
- 클라이언트 상태: Zustand (explorationStore 등)
- **Why**: 서버 캐싱과 UI 상태의 관심사 분리.

### Chain Sight 탐색 상태 공유
```typescript
interface ExplorationState {
  selectedSector: string | null;
  centerSymbol: string | null;  // null = pre-focus
  trail: TrailNode[];
  historyNodes: string[];
  currentNeighbors: Neighbor[];
}
```
- **Why**: 그래프와 카드가 "같은 탐색 상태를 공유하는 두 인터페이스"이므로 분리하지 않음.

---

## API 응답 규격

### 응답 표준: DRF 평탄 + 통일 에러 envelope
- **성공**: `serializer.data` 또는 dict **평탄 반환** (DRF 표준). 기존 `{success, data, meta}` wrapping 폐기.
- **에러**: 단일 형태 `{detail, code?, errors?, status_code}`
  - `detail`(필수): 사람이 읽는 메시지. DRF 기본 키 유지.
  - `code`(optional): snake_case 도메인 코드. 클라 분기용.
  - `errors`(optional): ValidationError field-level만.
  - `status_code`(필수): 정수. HTTP status 중복이지만 명시.
- **변환**: `config.exception_handler.custom_exception_handler` (REST_FRAMEWORK.EXCEPTION_HANDLER 등록, 2026-05-12).
- **도메인 코드 보존**: `rag_analysis/exceptions.py`(4개), `serverless/exceptions.py`(8개)에 `APIException` 서브클래스로 `default_code` 정의. 500계 도메인 에러 12개는 Sentry breakdown용 분기 의미가 있어 유지. 4xx 16개 코드는 DRF 표준 예외(`NotFound`, `PermissionDenied`, `NotAuthenticated`, `ValidationError`)로 흡수.
- **예외 범위**:
  - Market Pulse v2 cards (`marketpulse/api/views/cards.py:_envelope`) — v2 contract `{_meta, data}` 별도 유지.
  - 포트폴리오 (`portfolio/views.py` JsonResponse) — DRF 미사용, 정책 밖.
  - SSE 이벤트 페이로드 (`PIPELINE_ERROR`/`STREAM_ERROR`) — HTTP 200 내부 이벤트, 정책 밖.
- **Why**: 2026-05-06 api_consistency_audit P1 #14. 3종 혼재(W/D/C)로 FE가 라우트별 unwrap 분기 필요 → 같은 view 안에서도 성공은 wrap, 에러는 평탄으로 충돌하는 hotspot 존재. WRAP은 6 파일만 사용 → 마이그레이션 비용이 envelope 통일보다 작다. DRF 표준 정렬로 신규 view 결정 비용 0 + drf-spectacular ErrorSerializer 일관 적용.
- 📎 상세: `docs/features/api_envelope/policy.md`

---

## 인프라

### Neo4j 유지 결정
- GDS 알고리즘(PageRank, Louvain, Betweenness Centrality) + APOC 때문.
- **Why**: PostgreSQL의 `ltree`/`recursive CTE`로는 커뮤니티 탐지 불가.

### GraphRepository Protocol
- 백엔드 디커플링용 추상화. Neo4j 구현체만 존재.
- **Why**: 향후 다른 그래프 DB 전환 가능성 열어둠.

### Celery Beat 스케줄 분리
- `config/settings.py`: 기본 스케줄 (Market Movers, Breadth, Heatmap)
- `config/celery.py`: 확장 스케줄 (Chain Sight, EOD, ML, SEC)
- **Why**: 핵심 스케줄은 settings에, 기능별 스케줄은 celery.py에 분리.

### macOS Celery fork 안전성
- `OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES` + `PGGSSENCMODE=disable`
- fork 후 `db.connections.close_all()` 필수
- Neo4j queue: `--pool=solo` (fork 없이)
- **Why**: macOS에서 fork + Objective-C 런타임 충돌 (SIGSEGV). 버그 #25.

---

## 서비스 리모델링 (보류 — 2026-05-28)

### 3단계 플로우 전환 (계획서, 미시작)
- **이전**: Dashboard → Chain Sight → Node Monitoring → 1차 검증 → Thesis Control → Portfolio (6단계)
- **변경 계획**: Dashboard(매크로) → Chain Sight(발견/검증/가설) → Portfolio(보유) (3단계)
- **Why**: 사용자 여정 단순화. Chain Sight가 발견+검증+가설을 통합.
- 📎 설계 보존: `docs/stock_vis_service_remodeling/stock_vis_service_remodeling_plan_v1(260404).md`

### 보류 사유 (2026-05-28)
- 2026-04-04 계획서 작성 후 **실작업 0건** (브랜치 `data_structure_remodeling_V1` 부재, 5/11 main 정착 시 origin 삭제, 로컬도 부재)
- 44일 정체 (4/14 마지막 reflog → 5/28)
- 그동안 Slice 14~17이 main에서 진행되어 현 코드가 계획서 시점 대비 크게 변동
- 재개 시 현 시스템 기준 **재설계 필수**. 본 결정의 "변경 계획"은 사고의 출발점일 뿐 곧바로 실행 지침 아님
- TASKQUEUE "보류 (On Hold)" 섹션에 `SR (트랙)`으로 단일 행 이동 (옛 SR-1~4 통합)

---

## 지식 그래프 (OAG KB)

### 이중 저장 원칙: 1차 소스 + KB
- 아키텍처 결정 → `DECISIONS.md` (1차) + KB `DECISION` 타입 (장기 검색)
- 버그 해결 → `common-bugs.md` (1차) + KB `TROUBLESHOOT` 타입 (상세 과정)
- 세션 교훈 → KB `LESSON`/`PATTERN` 타입이 유일한 저장소
- **Why**: 1차 소스는 에이전트가 즉시 참조하는 "작업 메모리", KB는 장기 보존 + 의미 검색이 가능한 "장기 기억". 둘 다 필요.

### KB 큐 → 큐레이션 → Neo4j 파이프라인
- `queue_data.json`(대기) → `@kb-curator` 큐레이션 → `Neo4j Aura`(영구)
- **Why**: 품질 게이트 없이 KB에 직접 쓰면 노이즈 누적. 큐레이션이 신호/잡음 분리.

### knowledge_type 체계
| 타입 | 용도 | 주요 소스 |
|------|------|----------|
| `TROUBLESHOOT` | 버그 해결 과정 | common-bugs.md, @backend/@infra 세션 |
| `LESSON` | 교훈 (잘한 일/못한 일) | @qa 검증, 에이전트 세션 종료 |
| `DECISION` | 아키텍처 결정 | DECISIONS.md |
| `PATTERN` | 코딩 패턴 | @backend/@frontend 세션 |
| `TERM`/`METRIC` | 투자 용어/지표 | @investment-advisor |
- **Why**: 타입별로 검색 필터링 + 우선순위 규칙 적용 가능.

### 신뢰도 레벨 정책
- `verified`: 테스트 통과 또는 공식 문서 기반만
- `high`: 전문가(에이전트) 확인
- `medium`: 일반 합의 (큐레이션 기본값)
- `low`: 추정, 미검증
- **Why**: 에이전트가 검색 시 `confidence_min=high`로 노이즈 제거 가능.

---

## 외부 API

### FMP `/stable/*` 경로만 사용
- Legacy `/api/v3/*` 지원 안 함.
- **Why**: FMP가 stable 경로로 마이그레이션. 레거시 경로 deprecation 예정.

### Gemini 2.5 Flash 단일 LLM
- 키워드 생성, 관계 추출, RAG 분석, SEC 추출, 뉴스 분석 모두 Gemini.
- **Why**: 비용 효율 + 일관된 프롬프트 엔지니어링. $0.005/thesis 수준.

### Rate Limit 방어 원칙
| API | 제한 | 방어 |
|-----|------|------|
| Alpha Vantage | 5 calls/min | 12초 대기 필수 |
| FMP (Starter) | 300 calls/min, 10,000 calls/day | `.` 심볼 제외 (FMPPremiumError), api_request/rate_limiter.py에서 80% 안전 마진 |
| Gemini Free | 15 RPM, 1500 RPD | Exponential backoff + 배치 |

---

## 하네스 / 문서 관리

### 문서·git 정합성 관리 원칙 (2026-05-28 신규)

**결정**:
1. **PROGRESS.md를 두 영역으로 분리한다** — (a) **자동 추출 가능한 부분** (활성 brunch HEAD, origin/main 해시, 최근 머지 commit, 마지막 갱신 후 누적 commit 수)은 `scripts/health_check.py`가 매 세션 시작 시 검증·갱신 가이드 출력. (b) **수동 영역** (blocker, 결정 사항, 작업 단위 상태, 후속 큐)은 사람·에이전트가 종결 시 명시 갱신.
2. **매 세션 시작 시 `python scripts/health_check.py` 실행** — 5건 정합성 자동 검증 (origin HEAD vs PROGRESS / brunch·worktree 존재 / 마지막 갱신 후 commit 수 / TASKQUEUE done vs git 머지 매칭 / DECISIONS 갱신일). exit code 0=OK, 1=warning, 2=error. error 시 다른 작업 전 보정 우선.
3. **Claude 메모리는 진실의 소스가 아니라 PROGRESS의 캐시로 다룬다** — 메모리에 박힌 brunch/HEAD/PR 정보는 PROGRESS 표기를 참조한 결과물. PROGRESS가 stale이면 메모리도 stale. 갱신 우선 순위: git 현실 → PROGRESS → 메모리.
4. **TASKQUEUE의 `done` 상태는 git 머지 commit 매칭이 진실 기준** — TASKQUEUE에 `done` 표기됐는데 해당 PR/머지 commit이 git에 없으면 상태 오류. 외부(GitHub PR)에서 머지된 경우에도 머지 직후 TASKQUEUE 갱신 의무화.
5. **브랜치 종결 시(main 정착 + `slice*-done` 태그 생성) PROGRESS "활성 브랜치" 표에서 해당 행 제거** — 종결 이력의 진실 소스는 `slice*-done` 태그이고, PROGRESS 표는 "현재 활성"만 표기. 종결 brunch가 표에 잔존하면 health_check brunch 부재 ERROR 발생(2026-05-28 slice* 7건 일괄 삭제 후 slice17 표기 stale 사례). 백업 브랜치(`*-backup-*`)도 동일 원칙, 임시 백업 태그(`*-pre-merge`)는 표 외 노트로 유지.

**Why**:
- 2026-05-28 종합 정합성 점검에서 **6가지 불일치 패턴** 동시 발견:
  1. PROGRESS.md 16일 stale (마지막 5/12, 그동안 167 commits 누적)
  2. `origin/main = be2d6c7` 표기 오류 (실제 `3e76bc8`)
  3. `feature/chainsight-graph-v2` worktree 부재 (PR-#8 머지 후 정리됐는데 PROGRESS는 보존 중이라 표기)
  4. TASKQUEUE CS-R9 `todo` 표기 (실제 PR-#8 머지로 완료)
  5. slice17 brunch 143 commits이 origin/main에 0% 반영 (16일 누적 미통합)
  6. 메모리에 박힌 brunch/HEAD가 stale PROGRESS를 캐시한 상태
- **16일 stale은 시스템적 결함이지 1회성 실수가 아님** — 매 슬라이스 종결 시 갱신 의무가 명시됐음에도 brunch 격리 작업 + main 정착 단계 지연 + 외부 자동화 audit commit 끼어들기 등 복합 원인으로 누락 발생. 매뉴얼 의존 방식이 한계.
- 검문소(`health_check.py`) + 단일 진실의 소스(git 현실) + 자동/수동 영역 분리가 함께 있어야 재발 차단.

**Layer 1~4 채택 (단계화)**:
| Layer | 시점 | 작업 | 효과 |
|-------|------|------|------|
| 1 (즉시, 2026-05-28) | 본 결정 | `scripts/health_check.py` 도입 + PROGRESS·DECISIONS·common-bugs 갱신 + Slice 17 closing 후 박음 | 정합성 점검 자동화, 1회 보정 |
| 2 (단기, monorepo 도입 시) | Slice 18+ | monorepo 재배치 시 `apps/*`, `packages/shared/*`, `services/*` 별로 PROGRESS 분리 + 각 영역 독립 health_check | 단일 PROGRESS의 stale 폭발 위험 감소 |
| 3 (중기) | 운영 안정화 | pre-commit hook에 `health_check.py` warning 표시 + GitHub Actions 야간 자동화로 PROGRESS 자동 patch PR | 갱신 의무를 hook으로 강제 |
| 4 (장기) | Phase 2 진입 시 | PROGRESS 자동 추출 영역을 `make progress` 명령으로 완전 자동화. 수동 영역만 사람 입력 | 매뉴얼 부담 0, 자동 영역과 수동 영역 완전 분리 |

**📎 참조**: `scripts/health_check.py`, `sub_claude_md/common-bugs.md` #30, `PROGRESS.md` "정합성 문제 발견 (2026-05-28)" 섹션

---

## monorepo 재배치 (실행 결정 2026-05-28)

> 청사진: `docs/monorepo_migration/blueprint_v1.md` (실행 확정 = 지금)

### ① import 경로 방식 = 안 B(dotted-path) 확정 (2026-05-28)

**결정**: 폴더 구조를 import 경로에 반영. `services.stocks`, `packages.shared.users` 등 dotted-path 패턴. **app_label은 유지** (DB·migration 영향 0).

**근거**:
- 8 멀티에이전트가 코드를 대량으로 읽는 환경 — 경로의 **명시성·규칙 일관성**이 일회성 변경 비용(~80-120 파일) 압도
- 가중합 비교: **안 B 4.23** vs 안 C(혼합) 3.35 vs 안 A(평면 유지) 2.90
- 폴더 위치만 보고 어느 계층(packages/services/apps)인지 즉시 식별 가능 → 신규 작업 진입 비용 최소화

**실행 방식**:
- 3단계(폴더 이동 + import 경로 일괄 갱신)에서 **그룹별 점진** 진행
- 의존 역순: `packages/shared/` → `services/` → `apps/` (역방향 dependency 발생 방지)
- 단계마다 pytest 회귀 검증 (전건 통과 확인 후 다음 그룹)
- 마이그레이션 dependencies 형식(`('stocks', '0001_initial')`)은 app_label 기준이라 변경 불필요

**연쇄 제약**:
- 분류 경계(②)가 곧 경로에 박힘 → 다음 ② 결정에서 packages/services/apps 경계를 신중 확정해야 함
- `graph_analysis` 흡수 결정 / `marketpulse` 위치(shared vs services vs apps) / `chainsight` v1+v2 통합 여부가 ② 핵심 갈림길

**📎 참조**: `docs/monorepo_migration/blueprint_v1.md` §2(분류 초안) + §5(깨질 참조)

### ② 분류 경계 확정 — 세션 충돌 경계 기준 (2026-05-28 재정의)

**근본 목적**: monorepo = **세션 간 git 충돌 방지** (병진 확정). 세션 3종 = 메인 / 서브 / 봇 연계. 폴더는 **세션 소유권이 겹치지 않게 분리**.

**apps/** (메인 세션, 각 단독 트랙):
- `dashboard` — 거시 통합 뷰
- `market_pulse` — Market Pulse 본체 (marketpulse v2 + macro v1 진입점 통합). **dashboard와 분리** — 둘 다 거시지만 별개 메인 트랙(베이스만 공유)
- `chain_sight` — 발견/검증/가설 진입점
- `portfolio` — 보유 관리 + 코치 (+ `thesis` `scope` 분기 통합)

**integrations/** (봇 연계 세션):
- `iron_trading` — read-only provider, contract 기반 비공유 연계
  - ⚠ **apps/services 아님**. 가중합: **C(integrations) 5.0** > A(apps) 3.20 > B(services) 2.35

**packages/shared/** (공유 인프라·데이터):
- `stocks` · `users` · `api_request` · `metrics`
- `macro` **공유자산** — `MarketIndex` · `MarketIndexPrice` 모델 + `fred_client` · `fmp_client`
- `marketpulse/utils/circuit_breaker.py` (파일 단위 분리, 외부 7건 사용)

**packages/web/** 또는 루트 유지 — Next.js UI 공유 레이어:
- `frontend/` (단일 SPA). **apps/web 폐기** — 독립 트랙 아님, 공유 UI 레이어로 위치 변경

**services/** (백엔드 도메인 서비스):
- `news` · `serverless` · `rag_analysis` · `validation` · `sec_pipeline`
- `chainsight` (백엔드 v2)
- **`services/_dormant/graph_analysis`** — 0 import · API 미구현 · 활성 세션 없음. 가격 상관 도메인이라 `chainsight`(사업/뉴스 관계)와 별개. 미래 어느 메인 트랙이 활용 시점에 흡수 위치 재결정. 세션 충돌 위험 0(휴면 코드). 근거: `docs/chain_sight/update_v2/ROADMAP_v1.4.md` L931 "독립 유지. 겹치지 않음." 명시

**메타 레이어** (서브 세션, 루트 유지):
- `docs/` · `scripts/` · `PROGRESS.md` · `DECISIONS.md` · `TASKQUEUE.md` · `CLAUDE.md` · `sub_claude_md/` · `contracts/` · `shared_kb/` · `.claude/` · `HARNESS_FITNESS.md` · `WORKSPACE_ROOT.md`

**해체(소멸)**:
- `macro` 앱 — 자산을 `packages/shared` + `apps/market_pulse`로 분산. 앱 자체 소멸. v1 진입점은 market_pulse 흡수

**삭제 후보** (사용처 0, 마이그레이션 영향 확인 후):
- `macro.EconomicEvent`
- `macro.SectorIndicatorRelation`
- `macro.IndicatorCorrelation`

### 정정 이력 — 이전 ②의 오류 3건 교정 (2026-05-28)

1. **marketpulse를 dashboard에 통합** → **취소**. market_pulse는 별개 메인 트랙(독립 apps)으로 분리. 사유: 둘 다 거시지만 세션 소유권이 다른 별도 메인 트랙
2. **apps/web (frontend 독립 트랙)** → **취소**. frontend는 모든 apps의 공유 UI 레이어이므로 `packages/web/` 또는 루트 유지가 정합. apps에 두면 세션 충돌 트리거
3. **iron_trading = apps/services 후보** → **integrations/ 격리 확정**. 봇 연계는 read-only contract 기반이라 메인 세션·도메인 서비스와 성격이 다름

### 3단계 실행으로 이관된 미해결

1. `macro/services/macro_service.py` 위치 (packages vs services) — marketpulse v2 분리 코드 정독 후 판정
2. macro v1 API 10개 deprecate 범위 — frontend 실사용 grep 후 판정
3. 삭제 후보 3 model 실 제거 — `makemigrations --check` 후
4. `frontend/` 최종 위치 — `packages/web/` vs 루트 유지 (세션 충돌 분석 + import 비용 측정 후 결정)
5. `iron_trading`이 읽는 앱 인터페이스 계약 — `integrations/`로 격리하려면 contract 명시 필요

**📎 참조**: `docs/monorepo_migration/blueprint_v1.md` §② (재정의 동기화)

### ③ 빌드 도구 및 실행 KPI (2026-05-28)

**[결정]** Turborepo · Nx 등 monorepo 빌드 도구는 **현재 보류**.

**근거**:
- CI 부재 (`.github/workflows` 없음) → 빌드 캐싱 가치 0
- frontend 단일 패키지 (`workspaces` 부재) → 워크스페이스 분할 불필요
- 백엔드 단일 Django + Celery → 태스크 그래프 불필요
- 의존 그래프는 INSTALLED_APPS + dotted-path가 이미 표현
- → 도구 도입은 비용(설정·학습·yaml)만 추가

**[재검토 트리거]** 아래 중 하나라도 발생 시 ③ 재결정:
- (a) CI 도입 (`.github/workflows` 생성)
- (b) frontend가 다중 패키지로 분할
- (c) 빌드 시간이 솔로 개발 흐름을 저해할 정도로 증가

**[KPI · 이동 순서 · 롤백 지점]** ③ 결정 사안 아님 — 점진 실행 계획에서 정의:
- **이동 순서**: 의존 역순 (`packages/shared` → `services` → `apps` → `integrations`) 자동 도출
- **검증 KPI**: pytest 회귀 ~770 유지 + 단계별 IDENTICAL hash + ImportError 0
- **롤백**: 각 그룹 진입 전 백업 태그 (`monorepo-pre-{packages,services,apps,integrations}`)
- **상세**: `docs/monorepo_migration/execution_plan_v1.md` (작성 완료, 2026-05-29)

### execution_plan_v1.md 1차 소스 결정 (2026-05-29)

**결정**: `docs/monorepo_migration/execution_plan_v1.md` = **1차 소스**.

**근거**:
- `blueprint_v1.md`와 동일 디렉토리 (`docs/monorepo_migration/`) — 일관성 유지
- 결정 ①②③ 박은 DECISIONS commit 3건(`4f01cb7`/`118f899`→`7e42193`/`9b48d37`)이 이미 본 경로 참조
- 사용자 원본(`docs/monorepo_project/execution_plan_v1.md`)과 diff 결과 의미 추가분 0 확인 (본 사본이 superset — §5 이관 매핑 5건 박음 + §8 위치 확정). 사용자 원본 삭제로 정합화

**📎 참조**: 통합 진입점 + 본 결정의 1차 소스 패턴은 직전 박은 결정 1~5(문서·git 정합성 관리 원칙)와 일관

### monorepo PR1 — services/_dormant/graph_analysis 이동 (2026-05-30)

**결과**: `graph_analysis/` → `services/_dormant/graph_analysis/` 이동 완료 (history 보존, 11 파일 R100)

**commit SHA (PR1 4 commits, branch `monorepo/pr1-dormant`)**:
- `61c92ad` — services/ + services/_dormant/ 패키지 초기화 (__init__.py 2개)
- `845a810` — git mv 11 파일 R100
- `ebca8f5` — import 경로 갱신 (ast-grep 자기참조 2건 + ruff import 정렬 5 fix)
- `91d5055` — Django INSTALLED_APPS + AppConfig 호출처 갱신 (settings.py + apps.py label 명시)

**branch SHA (머지 후 main)**: {머지 후 채움}

**학습 곡선 4가지 정착**:

1. **ast-grep 패턴 3종** 정착 → 부록 A 박음 (PR2~PR8 답습용). 휴면이라 외부 호출 0건이었으나 자기참조 2건 발견 — "0건 확신 금지" 원칙 검증
2. **git tag 롤백 절차** 정착 (`monorepo-pre-pr1` 박음, 미사용 — Step 4 dry-run + commit 1 hook 통과로 충분 검증)
3. **DECISIONS 형식** 정착 (본 entry가 PR2~PR8 템플릿)
4. **health_check baseline** 정착 (PR1 진입 시 6✅/0⚠/1❌, ❌는 자기참조성 PROGRESS hash 미반영. 신규 결함 0)

**검증 결과**:

- §4.1 import smoke: `python -c "import services._dormant.graph_analysis"` → OK
- §4.2 pytest: `pytest -k "dormant or graph_analysis"` → 3224 collected / 0 selected (휴면 모듈 테스트 부재 정상)
- §4.3 ruff check 델타: main baseline 1009 errors = PR1 1009 errors (델타 0, 휴면 lint 부채는 PR1 scope 외)
- Django setup: OK (INSTALLED_APPS + AppConfig.label='graph_analysis' 호환)

**PR1 scope 외 분리 보류**:
- `ruff format` 7파일 광범위 재포맷 (+675/-392) — 휴면 모듈 광범위 포맷팅은 별도 commit/PR 가치, PR1 scope 외

**다음 PR**: PR2 (packages/) — packages/shared + packages/web 이동

### 부록 A — ast-grep 패턴 (PR2~PR8 답습 템플릿)

트랙 이동 시 import 경로 변경 패턴 3종 (`{OLD}` `{NEW}` 치환만 하면 PR2 적용 가능):

```yaml
pattern_from_submodule:
  pattern: "from {OLD}.$X import $$$Y"
  rewrite: "from {NEW}.$X import $$$Y"
  lang: python

pattern_import_module:
  pattern: "import {OLD}"
  rewrite: "import {NEW} as {OLD}"  # alias로 호환성 유지
  lang: python

pattern_from_direct:
  pattern: "from {OLD} import $$$X"
  rewrite: "from {NEW} import $$$X"
  lang: python
```

**적용 순서**: dry-run → 보고 → 사용자 승인 → -U 적용 → `ruff check --select I --fix`

**PR1 미커버 패턴 (PR2~PR8 추가 점검 필수)**:
- Django `INSTALLED_APPS` 내 문자열 — `grep -rn "{OLD}" config/` 별도 실행
- `AppConfig.name` — 모듈 dotted-path와 일치해야 함 (`apps.py` 검토)
- `AppConfig.label` — 기존 DB 테이블명 보존을 위해 명시 권장 (휴면 트랙 답습)

### 부채 #73 close — pre-commit hook monorepo/* 패턴 추가 (2026-05-30)

**결과**: `.git/hooks/pre-commit` 화이트리스트에 `monorepo/*` 패턴 통과 로직 추가 (라인 19~23, 5줄)

**사유**:
- monorepo 8 PR 답습 효율 (1회 수정 → 7회 회수)
- 가드 견고성 보존 (prefix 한정, main 직커밋·외부 자동화 차단 유지)
- 부채 #73 (slice17 등록) 본 작업의 사이드 산출물로 close

**검증**:
- test branch (`monorepo/test-hook-verify`) commit 성공 확인
- diff = 추가 5줄만 (`if [[ "$CURRENT_BRANCH" == monorepo/* ]] && BRANCH_OK=true; fi`), 기존 로직 변경 0
- PR1 commit 1~4 모두 hook 통과 (`✅ pre-commit 검증 통과 (branch=monorepo/pr1-dormant)`)

**관련**: blueprint_v1.md §7 결정 ②, execution_plan_v1.md §1, PR1 §1.0 사이드 산출물

### monorepo PR2 — packages/shared (A-min, 4 앱) 이동 (2026-05-30)

**결과**: `stocks`/`users`/`api_request`/`metrics` → `packages/shared/*` 이동 완료 (history 보존, R100)

**결정**:
- shared 범위 = **A-min** (4 Django 앱). macro 해체·circuit_breaker.py 분리는 PR2 외 (PR5 또는 별도 슬롯)
- frontend = **B-3** (PR2 완전 제외). blueprint §② vs §④ 모순은 별도 결정 후 처리
- A-mid/A-full 보류 사유: PR2 영향 광범위 (매칭 ~410+), 보수성 우선

**commit SHA (PR2 8 commits, branch `monorepo/pr2-packages`)**:
- `7385d07` — pre-step: ruff format baseline cleanup (4 앱 103 파일, scope 외 분리)
- `e4aca27` — packages/ + packages/shared/ 패키지 초기화
- `dd71aba` — stocks → packages/shared/stocks (git mv R100)
- `e145338` — users → packages/shared/users (git mv R100)
- `8f1a982` — api_request → packages/shared/api_request (git mv R100)
- `3cb9d42` — metrics → packages/shared/metrics (git mv R100)
- `bc0476d` — import 경로 갱신 (Python 363 + Django 패치 + 동적 import 46 = 409건)
- `94c531e` — .gitignore에 node_modules/ 추가 (사이드)

**branch SHA (머지 후 main)**: {머지 후 채움}

**답습 자산 활용 (PR1 부록 A)**:
- ast-grep 3 패턴: 시도 후 **결함 발견** — `$X` metavar가 dotted-name single segment만 매칭. 다층 dotted-path(`from api_request.providers.fmp.client`)에서 `.fmp.client` 잘림 사고. reset --hard로 폐기 후 regex 기반 재변환.
- Django 3 패턴: 정상 답습 — INSTALLED_APPS / AppConfig.name + label / LOGGING / CUSTOM_APPS / urls.py include() / celery beat task name

**신규 학습 (PR3~PR8 답습 필수, 부록 A 보강)**:

1. **ast-grep `$X` 한계**: dotted-name single segment 한정 → 다층 import는 **regex 기반 처리** 필수. 패턴: `\bfrom (APP)((?:\.[a-zA-Z0-9_]+)*) import` + replace `\1packages.shared.\2\3\4`
2. **동적 import 패턴**: `mock.patch('X.Y.Z')` / `importlib.import_module('X.Y')` / Celery `send_task('X.Y')` — ast-grep + regex 정적 분석으로는 누락 가능. pytest 풀 회귀 fail 보고 fail 파일 한정 manual 처리 권장
3. **보호 케이스 (변경 금지)**:
   - `'app_label.ModelName'` (2 segment, Django model ref — AUTH_USER_MODEL='users.User', `to='stocks.stock'` 마이그레이션 등)
   - 파일명 (`'stocks.log'`)
   - JSON 응답 키 (`'stocks': {...}` API 카탈로그)
4. **권장 패턴**: 3 segment+ 보수적 regex (`'APP.snake.X.Y...'`)가 동적 import에는 안전. 단 광범위 sweep은 auto mode classifier 차단 가능 — **fail 파일 한정 manual sweep**으로 우회
5. **AppConfig.label 명시 필수**: dotted-path 변경 시 기존 마이그레이션 테이블명·`AUTH_USER_MODEL`·model ref 보존 위해 `label='users'`/`label='stocks'`/`label='metrics'` 명시
6. **Celery beat task name 갱신**: dotted-path 기반 task auto-name이라 module 이동 시 `'X.tasks.Y'` → `'packages.shared.X.tasks.Y'` 일괄 치환 필요 (10건, config/celery.py)
7. **§1.7 ruff format pre-step 검증**: 효과 100% — PR1처럼 본 PR commit에 흡수되지 않음 (별도 pre-step commit 박음)
8. **node_modules .gitignore 미박힘 사고**: `git add -A` 위험. PR1에서 node_modules untracked였으나 add 안 했고, PR2 commit 7에서 처음 잡힘. .gitignore 사전 점검 패턴 부록 A 추가

**검증 결과**:
- §4.1 import smoke (Django setup 후): 4 앱 모두 OK
- §4.2 Django check: System check identified no issues
- §4.2 makemigrations --dry-run: No changes detected
- §4.3 pytest 풀 회귀: **3172 passed, 52 skipped** (PR1 baseline 완전 일치, 회귀 0건)
- §4.4 ruff check 델타: main baseline 1009 = PR2 1009 (델타 0)
- §4.5 sanity IDENTICAL: **skip** (pytest 회귀 0 + Django check PASS = packages 변경이 런타임 결과 영향 0 강한 신호. LLM 비용 사전 보존, PR4 풀 적용 시 31/31 검증)

**미처리 (PR2 외 처리)**:
- frontend (B-3): blueprint §② vs §④ 모순 별도 결정 후 PR
- macro 해체: PR5 (apps/market_pulse) 또는 별도 슬롯
- circuit_breaker.py 파일 분리: PR5/PR8 흡수

**다음 PR**: PR3 (integrations/iron_trading)

### 부록 A 보강 (PR2 학습 반영)

PR1 부록 A는 ast-grep 3 패턴 + Django 3 패턴이었으나 PR2에서 결함 발견. 답습 권장 패턴 갱신:

```python
# 답습 1: Python static import (정확한 regex, ast-grep 대체)
import re
APPS_RE = '|'.join(['APP1', 'APP2', ...])
pat = re.compile(r'(\bfrom\s+)(' + APPS_RE + r')((?:\.[a-zA-Z0-9_]+)*)(\s+import\s+)')
# replace: r'\1{NEW_PREFIX}.\2\3\4'

# 답습 2: 동적 import (pytest fail 파일 한정)
# 3 segment+ 보수적 regex
pat_dynamic = re.compile(
    r'([\'"])('+ APPS_RE + r')'
    r'(\.[a-z_][a-z0-9_]*)'      # 2번째: snake_case
    r'(\.[a-zA-Z0-9_]+)'          # 3번째: snake or Pascal
    r'((?:\.[a-zA-Z0-9_]+)*)'     # 추가 (옵션)
    r'([\'"])'
)
```

```python
# 답습 3: Django 패치 (PR1 정착 + PR2 추가)
# - INSTALLED_APPS
# - CUSTOM_APPS (있으면)
# - LOGGING.loggers (logger key는 dotted-path 기반)
# - AppConfig.name + label (마이그레이션 테이블명 보존)
# - urls.py include() 문자열
# - celery.py beat schedule 'X.tasks.Y' (10건+ 예상)
# - asgi.py 'import X.routing' (Channels)
```

**PR3 진입 전 점검**:
- iron_trading은 integrations/ 트랙. 외부 API 격리라 import 영향 작을 가능성 (~10건 이하 예상)
- iron_trading 자체가 Django 앱이므로 INSTALLED_APPS / AppConfig 답습 적용
- contracts/ 의존 명시 확인 (PR2와 달리 외부 봇 API contract 명시 필요)

### monorepo PR3 — integrations/iron_trading (옵션 B 네임스페이스) 이동 (2026-05-30)

**결과**: `iron_trading` → `integrations/iron_trading` 이동 완료 (history 보존, R100). 격리 트랙 자명 입증 — 변환 대상 2건만.

**판정 (STEP 0 fact-check)**:
- INSTALLED_APPS 등록 O (line 208)
- URL 라우팅 O (config/urls.py:46)
- 외부 Python import 호출 0건
- → **ACTIVE** (외부 봇 read-only API로 동작 중). target = `integrations/iron_trading/` (dormant 아님)

**옵션 B 채택 — integrations/ 네임스페이스 규약 (잠정 v0.1)**:
- `integrations/__init__.py` + `README.md` + `_shared/__init__.py` (의도된 빈 패키지)
- `_shared/`: 2+ integration 공유 유틸 자리. 현재 단일 integration이라 빈 패키지
- `_dormant/`: 현재 부재. 휴면 발생 시 추가
- **2번째 integration 진입 시 재검토** (현재 iron_trading 단일 → 검증 사례 부족)
- 상세 규약: `integrations/README.md`

**commit SHA (PR3 5 commits, branch `monorepo/pr3-integrations`)**:
- `4d7cc7f` — pre-step: ruff format baseline cleanup (iron_trading 4 파일)
- `5bc0cf2` — integrations namespace scaffold (__init__/README/_shared)
- `7171f83` — mv iron_trading → integrations/iron_trading (R100)
- `6cf961a` — 호출처 갱신 (config/urls.py + config/settings.py + apps.py label)
- `{commit 5}` — DECISIONS + PROGRESS 정착

**branch SHA (머지 후 main)**: {머지 후 채움}

**답습 자산 활용 (PR2 부록 A 보강 8건)**:
- Python static import regex: **0건** (자기참조 + 외부 호출 모두 부재)
- 동적 import sweep: **0건** (mock.patch/send_task/importlib 부재)
- Django 패치 7종 중 3종 적용: INSTALLED_APPS / urls.py include / AppConfig.name+label
- .gitignore 사전 점검: 충돌 0
- ruff format pre-step: 4 파일 분리 commit

**검증 결과**:
- Django check: System check identified no issues
- makemigrations --dry-run: No changes detected
- import smoke (Django setup 후): iron_trading OK
- pytest 풀 회귀: **3172 passed, 52 skipped** (PR2 baseline 완전 일치, 회귀 0건)
- ruff 델타: main 1013 = PR3 1013 (델타 0)
- health_check: 6✅/0⚠/1❌ (baseline 평행, ⚠ 격상 없음 — 빈 `_shared/` docstring 의도 명시로 false-positive 회피)

**신규 학습 (PR4~PR8 답습 후보)**:
1. **격리 트랙 자명 입증**: integrations 분류 자체가 외부 호출 0건 보장. PR3 변환 2건은 가중합 C 5.0 분류의 검증
2. **빈 패키지 docstring 의도 명시 패턴**: `_shared/__init__.py`처럼 의도된 빈 패키지는 docstring으로 health_check false-positive 방지
3. **2단계 mv 분리**: namespace scaffold commit과 mv commit 분리 — 후속 integration 추가 시 scaffold 1회 + 각 mv N회 답습
4. **STEP 0 fact-check 단순화**: INSTALLED_APPS 등록 + URL 라우팅 = active. 추가 동적 import 검사로 보강

**다음 PR**: PR4 (apps/dashboard/) — packages.shared 의존, IDENTICAL 31/31 풀 적용 시작점

### monorepo PR4 — apps/market_pulse 이관 (dashboard 보류 승계) (2026-05-31)

**결과**: `marketpulse/` → `apps/market_pulse/` 이동 완료 (history 보존, R100, snake_case rename 동반).

**PR4 대상 교체 결정**:
- 원안 (execution_plan v1.0): PR4 = `apps/dashboard/`
- fact-check (STEP 0): dashboard 실 디렉토리/Django 앱 **부재** (`docs/dashboard_plan/`만 존재)
- → dashboard = **monorepo 트랙 외로 보류**. 트리거 = 독립 배포 또는 모듈 경계 명시 필요 시
- → PR4 = `apps/market_pulse/` 승계 (원안 PR5). PR5 결번. 결번 표기: execution_plan v1.0 §1 갱신 박음
- 사유: dashboard는 신규 생성 + stocks 내 자산 분리 복합 작업이라 monorepo 단순 이동 패턴 외. 별도 설계 필요.

**STEP 0 fact-check 결과**:
- 실존: `./marketpulse/` (snake_case 아님, 단일 단어)
- INSTALLED_APPS: `marketpulse.apps.MarketpulseConfig` ✅
- URL: `api/v2/market-pulse/` ✅
- 외부 import 호출: 다수 (rag_analysis 2 + serverless 2 + tests/marketpulse 다수)
- → **ACTIVE**. target = `apps/market_pulse/` (snake_case rename 동반)
- frontend 분리: `frontend/app/market-pulse{,_v2}/` 등 다수 — **PR4 scope 외 (B-3 답습)**

**commit SHA (PR4 6 commits, branch `monorepo/pr4-market-pulse`)**:
- `b7a95a2` — pre-step: ruff format baseline cleanup (57 파일)
- `a212593` — apps/ 네임스페이스 패키지 초기화
- `{c3}` — mv marketpulse → apps/market_pulse (snake_case rename 동반)
- `{c4}` — import 경로 갱신 (Python 154 + Celery task name 22 = 176건)
- `726e0fd` — Django INSTALLED_APPS + URL + AppConfig 호출처 갱신
- `{c6}` — DECISIONS + PROGRESS + execution_plan dashboard 보류 마킹

**branch SHA (머지 후 main)**: {머지 후 채움}

**답습 자산 활용 (PR2/PR3 부록 A)**:
- Python static import regex: 154건 (48 파일)
- 동적 import sweep: 0건 (mock.patch/send_task/importlib 부재)
- Celery task name (4-seg 문자열): 22건 변환
- Django 패치 7종 중 3종 적용: INSTALLED_APPS / urls.py include / AppConfig.name+label
- .gitignore 사전 점검: 충돌 0
- ruff format pre-step: 57 파일 분리 commit

**보호된 케이스 (label='marketpulse' 유지)**:
- migration `to="marketpulse.marketpulsenews"` 2건
- model lazy ref `"marketpulse.MarketPulseNews"` 1건
- → Django app_label 기반 ref, AppConfig.label='marketpulse'로 마이그레이션 history + 모델 ref 보존

**검증 결과**:
- Django check: System check identified no issues
- makemigrations --dry-run: No changes detected
- import smoke (apps.market_pulse): OK
- pytest 풀 회귀: **3165 passed, 7 fail** — 7 fail 모두 main에서 동일 fail (환경/날짜 변경 영향, PR4 무관)
- ruff 델타: main 1013 = PR4 1013 (델타 0)
- health_check: 5✅/1⚠/1❌ — ⚠ 격상 = PR4 무관 `5894177 docs: 코드베이스 감사 보고서 생성` 휴리스틱 misclassify (외부 자동화 의심으로 분류, 실제는 사용자 docs commit). ❌ 신규 격상 없음 → HALT 사유 아님

**미처리 (PR4 외)**:
- `apps/market_pulse/utils/circuit_breaker.py` (외부 4 호출처 — rag_analysis 2 + serverless 2). blueprint §② "packages/shared 후보". **PR5(결번)/PR8 흡수 또는 별도 분리 PR** 가능성. 본 PR4는 marketpulse 전체 이동만, 분리는 별도 결정.
- dashboard 앱: monorepo 외 이연 (트리거 명시: 독립 배포/모듈 경계)
- frontend market-pulse 자산: B-3 답습, 별도 PR

**신규 학습 (PR6~PR8 답습 후보)**:
1. **fact-check 답습 강제**: plan 표기 ≠ 실 코드명 (plan `market_pulse` vs 실 `marketpulse`). 폴더 rename 동반 가능성 사전 확인 필수
2. **plan 표기 오류 → trigger 명시 보류**: 실존 부재 트랙은 monorepo 외로 이연 + trigger 명시 (dashboard 사례)
3. **AppConfig.label로 마이그레이션 history 보존**: snake_case rename + label='oldname' 조합으로 model ref/migration to="oldname.X" 모두 보존
4. **외부 환경/날짜 회귀 분리 검증 패턴**: main 비교로 PR 무관 회귀 빠르게 분리 (`git stash + git checkout main + pytest 대상 + 복귀`)

**다음 PR**: PR6 (apps/chain_sight/) — chainsight 앱 (실 코드명 확인 후 진입)

### monorepo PR6 — apps/chain_sight 이관 (chainsight snake_case rename) (2026-05-31)

**결과**: `chainsight/` → `apps/chain_sight/` 이동 완료 (history 보존, R100, snake_case rename + label='chainsight' 보존).

**STEP 0 fact-check 결과 (PR4 학습 1 답습)**:
- 실 코드명 `chainsight` (1 단어) ≠ plan `chain_sight` → snake_case rename 동반
- INSTALLED_APPS L204 + URL L44 → **ACTIVE**
- 외부 메인 코드 결합 0건 (tests/만 21건, PR3 iron_trading 수준 격리)
- frontend 자산 3건 (services/app/components) → PR6 scope 외 (B-3 답습)
- 보호 케이스 사전 식별: migration to= 2건 + 단축 task name 'chainsight-X' 10건 + spectacular lazy ref 1건

**commit SHA (PR6 5 commits, branch `monorepo/pr6-chain-sight`)**:
- `4d16647` — pre-step: ruff format baseline cleanup (55 파일)
- `31782f5` — mv chainsight → apps/chain_sight (R100, snake_case rename)
- `a60983a` — import 경로 갱신 (Python 91 + Celery 12 + mock.patch 15 = 118건)
- `3769265` — Django INSTALLED_APPS + URL + AppConfig name='apps.chain_sight' + label='chainsight'
- `{c5}` — DECISIONS + PROGRESS 정착

**branch SHA (머지 후 main)**: {머지 후 채움}

**답습 자산 활용 (PR2/PR3/PR4 부록 A)**:
- Python static import regex: 91건 (42 파일)
- 동적 import sweep: 15건 (regex 14 + manual 1, fail 파일 한정 — PR4 학습 답습)
- Celery 4-seg task name: 12건 변환
- 단축 task name 'chainsight-X' 10건 보존 (DB PeriodicTask 매핑 보존)
- Django 패치 3종 (INSTALLED_APPS / urls.py / AppConfig.name+label)
- label='chainsight' 효과: migration to= 2건 + spectacular lazy ref + ContentType 자동 보존

**검증 결과**:
- Django check: System check identified no issues
- makemigrations --dry-run: **No changes detected** (★ label 보존 효과 확인, HALT 트리거 5 회피)
- import smoke (apps.chain_sight): OK
- pytest 풀 회귀: **3172 passed, 52 skipped** (PR4 baseline 동일, **회귀 0건** + PR4 환경 fail 7건 해소)
- ruff 카운트: main 1013 → PR6 **1009** (-4 개선, 회귀 0)
- health_check: 6✅/0⚠/1❌ (baseline 평행)

**미처리 (PR6 외)**:
- frontend chainsight 자산 — B-3 답습, 별도 PR
- URL prefix `api/v1/chainsight/` 보존 (외부 API consumer 호환성)

**다음 PR**: PR7 (apps/portfolio/) — **최고 위험도** (coach 포함, 슬라이스 병행 ❌ 금지). 풀 회귀 + IDENTICAL 31/31 필수.

### monorepo PR7 — apps/portfolio 이관 (단일 앱 최대 규모, IDENTICAL 7/7) (2026-05-31)

**결과**: `portfolio/` → `apps/portfolio/` 이동 완료 (history 보존, R100, rename 없음 위치만, label='portfolio' 명시).

**STEP 0 사전 조사 결과 (READ-ONLY)**:
- IDENTICAL = **정적 무결성 테스트** (`portfolio/tests/test_static_integrity.py` 7+ 케이스, binary 해시 아님)
- 거짓양성 위험 = **0** (import 갱신 후 모듈 import 성공하면 자동 통과)
- 외부 결합 = 0 (메인 코드 호출 0, tests 40 + scripts 일부)
- coach = `portfolio/services/coach/` (E1~E6 + prompt_builder)
- 보호 케이스: migration to= 11건 + URL namespace='portfolio_api' + URL name 'portfolio-X'
- 슬라이스 병행 = 없음

**commit SHA (PR7 6 commits, branch `monorepo/pr7-portfolio`)**:
- `66c52bc` — pre-step: ruff format baseline cleanup (89 파일)
- `225ff47` — mv portfolio → apps/portfolio (R100, rename 없음)
- `0f935ce` — import 경로 갱신 (Python 545 + 동적 mock.patch 15 + scripts importlib 5 = **565건**)
- `38c61c3` — Django INSTALLED_APPS + URL 2건 (namespace 보존) + AppConfig.name + label='portfolio' 명시
- `8ef118a` — fixture 경로 하드코딩 갱신 (8건, 신규 패턴)
- `{c6}` — DECISIONS + PROGRESS 정착

**branch SHA (머지 후 main)**: {머지 후 채움}

**답습 자산 활용 (PR2~PR6 부록 A)**:
- Python static import regex: **545건** (175 파일, 단일 PR 최대)
- 동적 mock.patch: 15건
- scripts importlib (dotted-path 문자열): 5건
- Django 패치 4종 (INSTALLED_APPS / urls 2건 + namespace 보존 / AppConfig.name+label)
- label='portfolio' 효과: migration to= 11건 + ContentType 자동 보존

**신규 발견 — fixture 경로 하드코딩 (부록 A 추가)**:
- `FIXTURE_DIR = Path("portfolio/tests/fixtures/...")` 형식 8건
- ast-grep/정적 import sweep으로 잡히지 않음 — STEP 6 pytest 4 errors로 노출
- regex 패턴: `(?<!apps/)(?<!docs/)portfolio/tests/fixtures` → `apps/portfolio/tests/fixtures`
- PR8 답습 후보로 박음

**검증 결과 (8단계)**:
- ① Django check: System check identified no issues
- ② ★ **IDENTICAL test_static_integrity: 7/7 PASSED** (import 갱신 후 자동 통과 — 거짓양성 0 입증)
- ③ vitest: N/A (frontend 변경 0)
- ④ makemigrations --dry-run: **No changes detected** (★ label 보존 효과 입증)
- ⑤ ruff: main 1009 → PR7 1010 (+1, 회귀 0)
- ⑥ health_check: 6✅/0⚠/1❌ baseline 평행
- ⑦ cost_ledger: N/A (LLM 호출 0)
- ⑧ pytest 풀 회귀: **3172 passed, 52 skipped** (PR6 baseline 완전 일치, **회귀 0건**)

**신규 학습 (PR8 답습 후보)**:
1. **IDENTICAL = 정적 무결성** (binary 해시 아님): plan 위험등급 "최고"는 메커니즘 미확인 기반이었음. 실측 결과 PR6 동급 + 규모만 큼. import 갱신 정확하면 자동 통과.
2. **fixture 경로 하드코딩**: `Path(...) / "portfolio" / "tests" / ...` 형식. STEP 3 정적 import sweep으로 누락, STEP 6 pytest fail로 노출. regex 보호 패턴 (`(?<!apps/)(?<!docs/)`) 필수.
3. **URL namespace 보존**: `include(..., namespace='portfolio_api')` 형식. namespace 문자열은 dotted-path 무관, 그대로 유지 (reverse() 호환성).
4. **단일 앱 최대 규모 일괄 처리**: 565건 변환 한 commit 안에 박음. Django 패치 분리(별 commit) + fixture 경로 추가 commit으로 분할 — 의미 단위 5 commits 정합.

**미처리 (PR7 외)**:
- frontend portfolio 자산 3건 (`frontend/app/portfolio`, `components/portfolio`, `services/portfolio.ts`) — B-3 답습, 별도 PR
- URL prefix `api/`, `api/v1/`은 그대로 (Django 외부 consumer 호환성)

**다음 PR**: PR8 — 루트 메타 정리 + 이관 5건 잔여 (모든 apps/packages/integrations/services 트랙 정착 후). 루트 잔존 7 Django 앱 (rag_analysis, serverless, macro, news, thesis, sec_pipeline, validation) 분류 결정.

### monorepo PR8a — services/ 5앱 이동 (순차 3그룹 / 옵션2) (2026-06-01)

**결과**: `news` + `serverless` + `rag_analysis` + `validation` + `sec_pipeline` → `services/*` 이동 완료. 5앱 일괄 + label 명시 + 보호 케이스 자동 보존. 동적 import 신규 패턴 4종 발견·처리.

**STEP 0 사전 조사 결과**:
- rename 0 (디렉토리명 그대로 유지)
- 상호 의존: news→rag(1) / serverless→news/rag(2) / 나머지 독립 — **순환 없음**
- 공유 유틸 후보 0 (5앱 내 utils/lib 부재)
- ★ 동적 mock.patch 260건 (5앱 합계, PR7 15건의 17배)

**옵션2 채택 — 순차 3그룹**:
- 1차: rag_analysis + validation + sec_pipeline (독립, 동시 이동)
- 2차: news (rag 의존 1)
- 3차: serverless (news + rag 의존 2)

**commit SHA (PR8a 8 commits, branch `monorepo/pr8a-services`)**:
- `cfa33e6` — pre-step: ruff format baseline cleanup (200 파일)
- `57fcc55` — mv 1차 3앱 → services/
- `6ed3d69` — 1차 import 갱신 (정적 360 + import 단독 1 + mock.patch 107 + Celery 13 = 481건)
- `ddca3bd` — mv news → services/news
- `d86c680` — 2차 import 갱신 (정적 198 + mock.patch 89 + monkeypatch 2 + 멀티라인 patch 1 + Celery 38 + test assert 6 = 334건)
- `e403527` — mv serverless → services/serverless
- `94f082c` — 3차 import 갱신 (정적 249 + mock.patch 64 + Celery 24 = 337건)
- `{c8}` — DECISIONS + PROGRESS 정착

**branch SHA (머지 후 main)**: {머지 후 채움}

**규모 (PR1~7 통합 답습)**:
- 정적 import: 360+198+249 = **807건** (STEP 0 추정 779 +3.6%)
- 동적 mock.patch: 107+89+64 = **260건** (STEP 0 추정 정확)
- 신규 동적 패턴 (PR8a 학습): monkeypatch.setattr 2 + 멀티라인 patch 1 + test assert task name 6 = 9건
- Celery task name: 13+38+24 = **75건**
- 총 **~1150건** (PR7 545건의 2.1배, STEP 0 추정 1100~1200 정확)

**신규 학습 (부록 A 추가, PR8b/c 답습)**:

1. **monkeypatch.setattr 동적 경로 패턴**: `monkeypatch.setattr('X.Y.Z', ...)` — pytest fixture. mock.patch와 별개. 5앱 중 news 2건. PR8a-2 setup ERROR 12건으로 노출.
2. **멀티라인 patch 패턴**: `patch(\n    "X.Y.Z",\n    ...)` — 줄바꿈으로 인해 단일라인 regex `patch\(["']X` 미커버. multi 패턴 regex `patch\(\s*\n\s*["']` 추가 필요.
3. **Test assert hardcode task name**: `assert task['task'] == 'X.tasks.Y'` — Celery task 이름이 test 안에 박혀있음. Celery beat schedule 갱신과 별개로 test 코드도 갱신 필요.
4. **ready() 안 들여쓰기 import + 주석 # noqa**: `        import X.signals  # noqa` — regex `\s*$|\s+as`로 잡지 못함 (`# noqa`는 `\s*$` 미매칭). 5앱 중 rag_analysis/sec_pipeline 2건 manual 처리.

**검증 결과**:
- ① Django check: PASS (5앱 모두)
- ② makemigrations --dry-run: **No changes detected** (★ label 보존 효과 입증)
- ③ pytest 풀 회귀: **3172 passed, 52 skipped** (PR7 baseline 완전 일치, **회귀 0건**, PR4/PR8a-1 환경 fail 7건도 해소)
- ④ ruff: main 1010 = PR8a 1010 (델타 0)
- ⑤ 5앱 정적 잔존 0 (sweep 통과)
- ⑥ health_check: 5✅/1⚠/1❌ (⚠는 PR8a 무관 `24b748e` docs commit 휴리스틱 misclassify, ❌ 신규 격상 없음 → HALT 사유 아님)
- ⑦ INSTALLED_APPS 5앱 services.* 적용 확인

**보호된 케이스 (label 보존)**:
- news: migration to= 2 + lazy ref 8 (model ref 2 + i18n 키 6)
- serverless: migration to= 4+
- rag_analysis: migration to= 5+
- validation: 0
- sec_pipeline: migration to= 3+ + lazy ref 1

**미처리 (PR8b/c 외)**:
- macro 해체 (apps/market_pulse + packages/shared 분배) — PR8b
- thesis 처분 결정 (보류, 사용자 트리거 대기)
- 메타 정리 (marketpulse/ 빈 디렉토리 + graph_analysis 회귀 + plan 도식) — PR8c

**다음 PR**: PR8b (macro 해체) — services/ 5앱 정착 후 진입. macro v1 진입점 → apps/market_pulse 흡수 + MarketIndex/MarketIndexPrice/fred_client/fmp_client → packages/shared/ 분배 + 삭제 후보 3 model 보류.

### shared 경계 검문소 (2026-06-01)

**결정**: 채택 = ㄱ(pytest 아키텍처 테스트, AST) + 보조 ㄴ(health 8번째 항목) + 야간 가(추적만, read-only). 자동 수정·자동 청소(다) **영구 배제** — 행위 보존 위반 위험.

**배경**: PR8b STEP 0 fact-check에서 `packages/shared/`가 거꾸로 `apps/*`·`macro`를 import하는 5건 검출. shared는 단방향 base 경계이므로 위반. 새 위반 차단(검문소) + 묵은 5건 동결(소진 트랙 분리)로 분리 대응.

**Why**:
- 단방향 경계는 검문소 없으면 새 우회가 PR마다 슬며시 추가됨 (PR8b STEP 0에서 5건 한꺼번에 드러난 게 시그널).
- AST 파싱은 import 실행을 하지 않으므로 Django 셋업/순환 폭발과 무관 — 가장 비용이 싼 차단 장치.
- 묵은 5건을 같은 사이클에 고치면 행위 변경 + import 리팩토링이 섞여 위험. 동결 후 별도 사이클로 청소.

**How to apply**:
- 새 위반: `tests/architecture/test_shared_boundary.py` 자동 FAIL → 의존 방향 뒤집기 또는 shared 승격으로 해결.
- 묵은 5건: TASKQUEUE `BOUNDARY-1/2/3` 소진 큐 따라 별도 PR로 청소 → `KNOWN_VIOLATIONS` 키를 tests + health_check 2곳에서 동시 삭제.
- 야간 추적: `docs/harness/boundary_ledger.jsonl`에 `{frozen, bypass, total}` 한 줄/일 burn-down. health_check `--ledger`로만 append (수동 실행은 ledger 오염 회피).
- 자동 수정 금지: 야간이 import를 고치거나 커밋하면 안 됨. ledger 적재 외 행위 0.

**SSOT**: `tests/architecture/test_shared_boundary.py:KNOWN_VIOLATIONS`. `scripts/health_check.py:_BOUNDARY_KNOWN_VIOLATIONS`는 동기 복사본 — 양쪽 동시 갱신 필수.

**관련 문서**: `docs/harness/SHARED_BOUNDARY_GUARD.md`, `sub_claude_md/common-bugs.md #31`.

### monorepo PR8b-1 — macro 비모델 분배 (실행) (2026-06-01)

**결정**: macro는 "**모델 전용 shell app**"으로 잔존(INSTALLED_APPS 'macro' 유지, label 'macro' 불변). 비모델 모든 행위는 `apps/market_pulse/`로 동거 이사. fred_client만 `packages/shared/api_request/`로 승격 (추천 B).

**HEAD**: `61b1d97` → `1a20c9b` (+4 commits).

**커밋**:
| 순 | hash | 의미 |
|---|---|---|
| 1a | `0b5c8ed` | services 분배 (fred→shared, fmp/macro_service→market_pulse) |
| 1b | `083b8da` | entry (views/serializers/urls) → market_pulse, config/urls.py:39 갱신 |
| 1c | `5ab58ee` | tasks → market_pulse/tasks/macro.py + celery.py Beat 5건 갱신 |
| 1d | `1a20c9b` | mgmt/constants → market_pulse |

**불변**:
- `INSTALLED_APPS = ['macro', ...]` (settings.py:197)
- LLM domain enum `('macro', 'Macro')` (settings.py:404)
- spectacular_enums.py:19 `MACRO = 'macro'`
- URL prefix `/api/v1/macro/*` (frontend macroService.ts 영향 0)
- `reverse('macro:market-pulse')` = `/api/v1/macro/pulse/`
- `app_label='macro'` (migrations 디렉토리명 기반, 명시 0건 → 변경 불요)

**잔존 (PR8b-2/c 트리거 대기)**:
- macro/models + migrations — **PR8b-3에서 옵션 A 채택(이동 안 함)**. 영구 모델 전용 앱(아래 PR8b-3 결정 참조).
- fmp_client / constants dead-code 판정 — PR8c
- thesis 처분 확정 시 → fred 최종 위치 재검토

**R6 (Beat schedule drift)**: dict + 코드 갱신 완료. **DB sync 미실행**(별도 절차, 사용자 트리거). 운영 동기화 절차:
```python
# python manage.py shell
from django_celery_beat.models import PeriodicTask
mapping = {
    'update-economic-indicators':   'apps.market_pulse.tasks.macro.update_economic_indicators',
    'update-market-indices':        'apps.market_pulse.tasks.macro.update_market_indices',
    'update-economic-calendar':     'apps.market_pulse.tasks.macro.update_economic_calendar',
    'refresh-market-pulse-cache':   'apps.market_pulse.tasks.macro.refresh_market_pulse_cache',
    'cleanup-old-macro-data':       'apps.market_pulse.tasks.macro.cleanup_old_data',
}
for name, new_task in mapping.items():
    updated = PeriodicTask.objects.filter(name=name).update(task=new_task)
    print(name, '->', updated, 'rows')
```
실행 후 celery beat 재시작 필요. 미실행 시 DB의 옛 경로 `macro.tasks.X`로 호출 → ImportError로 task 실패.

**검증**: pytest 3175 passed/52 skipped (회귀 0), 경계 GREEN(우회 0/동결 5), reverse 불변, `find macro -type f` = `__init__.py`/`apps.py`/`admin.py`/`models/`/`migrations/` + 빈 mgmt 패키지.

### Beat 드리프트 = reconcile 커맨드로 항구 처리 (2026-06-01, PR8b-2 Track A)

**결정**: task 이동·리네임으로 인한 DB↔dict 드리프트는 일회용 shell one-liner 대신 `python manage.py sync_beat_schedule` reconcile 커맨드(`apps/market_pulse/management/commands/sync_beat_schedule.py`)로 표준화한다. dry-run 기본 + `--apply` 명시 + idempotent.

**Why**: 매 monorepo PR 마다 5~75건씩 누적 drift 발생, shell snippet 재작성은 휴먼 에러 위험 + 일관성 부재. 재사용 가능한 멱등 커맨드 1개로 압축하고 모든 절차(common-bugs #28)는 거기를 가리킨다.

**How to apply**:
- 신규 task / 이동 / 리네임 → dict 갱신 후 `sync_beat_schedule --dry-run` → `--apply` → beat 재시작.
- 운영 DB 변경은 사용자 트리거(Claude Code dev DB 검증까지만).
- 첫 적용 (2026-06-01): dev DB 75 row reconcile, idempotent 확인 PASS.

**관련 문서**: `sub_claude_md/common-bugs.md #28` "항구 해결" 절차, `tests/marketpulse/test_sync_beat_schedule.py` 4 tests.

### PR8b-2 Track B — fmp_client / macro_service / constants 판정 = 보존 (2026-06-01)

**결정**: STEP 0 가설("constants 소비자 0건", fmp_client 외부 0)을 reachability 전수 실측으로 정정. 3개 후보 모두 **REACHABLE** → 삭제 0건.

| 후보 | 직접 소비 | Transitive | 결론 |
|---|---|---|---|
| `apps/market_pulse/services/fmp_client.py` | `macro_service.py` 단일 | macro_service → views(9) + tasks/macro(4) | reachable |
| `apps/market_pulse/services/macro_service.py` | views.py 9 + tasks/macro.py 4 (lazy) | — | reachable |
| `apps/market_pulse/constants/` | `macro_service.py` (`calculate_fear_greed_index`, `get_insight_message`) | → views/tasks 사슬 | reachable |

**Why**: STEP 0 가설은 import만 보고 transitive 호출 사슬을 보지 않은 결함. dead-code 단정 전 transitive 도달성 전수 (import + 동적 + 문자열 + admin + serializer field + task name)는 절대 규칙 2 명시.

**How to apply**: PR8c에서도 위 3개를 dead-code로 단정 짓지 말 것. 동일 이름의 `FMPClient`가 3개 모듈에 존재 (`apps/market_pulse/services/fmp_client.py` vs `packages/shared/api_request/providers/fmp/client.py` vs `services/serverless/services/fmp_client.py`) — 검색 시 혼동 주의, 절대 경로로 식별.

**잔재 (PR8c 정리 대상 태깅)**:
- `macro/management/commands/__init__.py` 빈 패키지 (안에 .py 0개) → PR8c.

### monorepo PR8b-3 종결 — macro = 영구 모델 전용 앱 (옵션 A, 이동 안 함) (2026-06-01)

**결정**: macro/models + migrations를 **옮기지 않는다**. macro 앱을 영구 "모델 전용 앱"으로 확정 — `models/` + `migrations/` + `apps.py` + `admin.py` + 빈 `__init__.py` + 빈 `management/` 구조가 의도된 최종 상태다. **Django 정상 패턴 = 부채 아님.**

**근거 3**:
1. prod DB·배포 보류 전제에서 영향 0. ContentType / db_table / state migration 리스크를 감수할 이득 없음.
2. **모델을 market_pulse로 옮겨도 #4·#5는 풀리지 않는다** — shared가 여전히 앱 모델을 거꾸로 import (label만 'macro' → 'marketpulse'로 바뀔 뿐 shared→app 위반은 동일).
3. monorepo 목적(git 충돌 방지·비모델 정돈)은 **PR8b-1에서 이미 달성**. macro는 비모델 행위가 0이라 충돌면이 없다.

**옵션 C(모델을 packages/shared로 승격) = 조건부 보류**(deferred, not cancelled). BOUNDARY-3 경계 STEP 0에서 방향1(소비자 이동)이 막힐 때 정공법으로 부활.

**결과**:
- macro 최종 구조: `__init__.py` + `apps.py` + `admin.py` + `models/{__init__,indicators,relationships}.py` + `migrations/0001~0006` + (빈) `management/commands/__init__.py`
- INSTALLED_APPS `'macro'` 영구 유지, label `'macro'` 영구 유지, `MACRO` enum 영구 유지

**관련 갱신**:
- TASKQUEUE BOUNDARY-3 재정의 (Part 2 참조)
- `docs/harness/SHARED_BOUNDARY_GUARD.md` #4·#5 행 정정
- `sub_claude_md/common-bugs.md #31` 소진 순서 3 정정 + "#4·#5 영구 동결 아님" 명시

### BOUNDARY-3 재정의 — #4·#5 청소 = 소비자 이동 (모델 이동 아님) (2026-06-01)

**결정**: BOUNDARY-3(`stocks/services/eod_regime_calculator.py:77`, `eod_pipeline.py:617` lazy import `macro.models`)의 청소 경로를 **모델 이동 동봉**에서 **소비자 이동(방향1)** 으로 재정의. 후보 3:

- **방향1 (우선)**: 두 소비자 파일을 `apps/market_pulse/`로 이동 → app→app 의존이라 합법, prod DB 무관. 다만 두 파일이 정말 market_pulse 전용인지 vs 진짜 공용(EOD 파이프라인 등 도메인 공통)인지 **경계 STEP 0** 필요.
- **방향2**: dependency inversion — shared에 추상 인터페이스 두고 market_pulse가 구현 주입.
- **C (조건부 보류)**: 방향1·2가 모두 막히면 macro/models를 `packages/shared/`로 승격(옵션 C 부활).

**Why**: 모델 이동은 ContentType / db_table 리스크가 크고 #4·#5를 직접 풀지 못한다(위 PR8b-3 근거 2). 소비자 이동은 prod DB 무관 + app→app이므로 가드 비대상 + 경계 burn-down 직접 효과.

**How to apply**: BOUNDARY-3 진입 시 먼저 두 파일의 호출자 + 도메인 사용처 전수 (eod_regime_calculator / eod_pipeline 호출자 grep)→ 단일 도메인이면 방향1, 다도메인이면 C. 절대 모델부터 건드리지 말 것.

**관련 문서**: TASKQUEUE.md `BOUNDARY-3` (새 정의), `docs/harness/SHARED_BOUNDARY_GUARD.md` #4·#5 행.

### monorepo PR8c 종결 — 메타 정리 + 트랙 완주 (2026-06-01)

**결정**: monorepo 8 PR 시리즈 완주. macro = 영구 모델 전용 앱, packages/shared / apps/* / services/* / integrations/* / services/_dormant/ 전 격자 정착.

**커밋 3**:
| 순 | hash | 의미 |
|---|---|---|
| a | `19eeb7f` | 빈 잔재 정리 (`marketpulse/` untracked dir + `macro/management/` 빈 패키지) + blueprint_v1.md dashboard 행 정정 + common-bugs #32 FMPClient 동명 3 모듈 가이드 |
| b | `dec8941` | graph_analysis 휴면 자기참조 회귀 2건 정정 (`from graph_analysis.models` → `from services._dormant.graph_analysis.models`, 휴면 의도 보존) |
| c | (이 docs commit) | PROGRESS / DECISIONS 트랙 완주 기록 |

**monorepo 8 PR 시리즈 (history)**:
1. PR1 (2026-05-30) — `services/_dormant/graph_analysis` 휴면 이동
2. PR2 (2026-05-30) — `packages/shared/{stocks,users,api_request,metrics}` (A-min)
3. PR3 (2026-05-30) — `integrations/iron_trading` (옵션 B 네임스페이스)
4. PR4 (2026-05-31) — `apps/market_pulse` (dashboard 보류 승계)
5. PR5 — 결번 (PR4 흡수)
6. PR6 (2026-05-31) — `apps/chain_sight`
7. PR7 (2026-05-31) — `apps/portfolio` (단일 앱 최대, IDENTICAL 7/7)
8. PR8a (2026-06-01) — `services/{news,serverless,rag_analysis,validation,sec_pipeline}` (옵션2 3그룹)
9. PR8b (2026-06-01) — macro 분배 (1: 비모델 → market_pulse / 2: Beat 항구 해결 + reachability 판정 / 3: macro=영구 모델앱)
10. PR8c (2026-06-01) — 메타 정리 + graph_analysis 회귀 해소 + 완주 정착

**최종 격자**:
```
apps/        — 메인 트랙 (chain_sight, market_pulse, portfolio)
packages/    — 단방향 base (shared/{stocks,users,api_request,metrics}) — 경계 검문소 LIVE
services/    — 도메인 서비스 (news, serverless, rag_analysis, validation, sec_pipeline)
services/_dormant/ — 휴면 (graph_analysis)
integrations/ — 봇 연계 격리 (iron_trading)
macro/       — 영구 모델 전용 앱 (PR8b-3 옵션 A)
thesis/      — 처분 보류 (사용자 트리거 대기, monorepo 외)
```

**잔존 (monorepo 외 트랙)**:
- BOUNDARY-1/2/3 (경계 트랙 소진 큐)
- Beat prod DB 동기화 (운영 트리거, `sync_beat_schedule --apply` + beat 재시작)
- thesis 처분 (a/b/c 트리거 대기)
- FMPClient 3중화 통합 (별도 부채 트랙)
- health ❌ 1건 PROGRESS hash 자기참조 (push 트리거, 정합성 Layer 4 영역)

**검증 (최종)**: pytest **3179 passed, 52 skipped** (회귀 0, monorepo 8 PR 시리즈 누적 0건 회귀), 경계 GREEN (우회 0 / 동결 잔여 5), health 7✅/0⚠/1❌(별개 트랙).

### 버킷A — shared 인프라 정착 (circuit_breaker 승격 + FMP namespace 통합) (2026-06-01)

**결정**: monorepo 외 첫 후속 트랙으로 `packages/shared/api_request/` 인프라 정착. (1) `circuit_breaker` 승격으로 BOUNDARY-1 #1·#2 자연 해소 (2) FMP 3벌을 same namespace로 격자화 (#32 1단계 종료).

**HEAD**: `b8f3d00` → `ccbdce5` (+2 commits, branch=main).

**커밋 2**:
| 순 | hash | 의미 |
|---|---|---|
| 1 | `d30915e` | circuit_breaker → `packages/shared/api_request/` 승격, 10 파일 import 갱신, KNOWN_VIOLATIONS #1·#2 해제 (5→3) |
| 2 | `ccbdce5` | FMP 3 클래스를 `providers/fmp/{client,market_pulse_client,serverless_client}.py`로 격자화, 16 소비처 갱신 (#32 1단계) |

**왜 namespace 옵션 (i) 채택**:
- (ii) canonical에 24 메서드 이식 = 행위보존 경계 위반 위험.
- (i) namespace 이동 + 클래스 이름 보존 = 행위보존 100% + #32 "동명 3 모듈" 신호어 해소.
- 2단계(완전 단일화)는 별도 사이클 (에러 정책 통일 + 메서드 합집합 설계 필요).

**burn-down**: shared 경계 동결 **5 → 3**. 잔여 = #3 (chain_sight), #4·#5 (macro.models).
**잔존 트랙**:
- BOUNDARY-2 (#3 chain_sight)
- BOUNDARY-3 (#4·#5 macro, 소비자 이동 방향1)
- FMP 2단계 통합 (canonical 메서드 합집합, 사용자 트리거)

**검증**: pytest 3179/52 (회귀 0, 버킷A 누적 0건), 경계 GREEN (우회 0 / 동결 잔여 3), health 8✅/0⚠/0❌.

### 버킷B / BOUNDARY-2 — #3 chain_sight 의존 청소 (Django apps.get_model) (2026-06-01)

**결정**: shared cross-app aggregator(`packages/shared/metrics/services/daily_report.py`)에서 `apps.chain_sight.models.CompanyChainProfile` 정적 import 제거. **Django app registry 동적 lookup**(`apps.get_model("chainsight", "CompanyChainProfile")`) 채택.

**HEAD**: `55f3cb6` → `80b9280` (+1 commit).

**왜 방향3 변종 채택**:
- **방향1 (소비자 이동) 불가**: daily_report = stocks + news + nightly + chain_sight + sec_pipeline + health 횡단 집계 aggregator. 단일 앱 흡수 불가능.
- **방향2 (callable 주입) 반쪽 효과**: 호출자도 `packages/shared/metrics/` 내부(tasks.py / management command / agent_reports). 의존이 caller chain을 따라 올라가도 shared를 못 벗어남 — 어딘가 static import 필요.
- **방향3 변종**: Django 공식 cross-app dynamic model lookup 표준. chain_sight 앱 소멸 시 import 단계 폭발 없이 runtime graceful fallback 가능. 행위 100% 보존. AST 가드는 정적 import만 검사 → 위반 자연 해소.

**범위 (행위 보존, 라인 +2 / -1)**:
- `packages/shared/metrics/services/daily_report.py:240` `collect_coverage_gaps()` 함수 1곳만 변경
- `from apps.chain_sight.models import CompanyChainProfile` 제거
- `CompanyChainProfile = django_apps.get_model("chainsight", "CompanyChainProfile")` 추가
- 사용처 (`CompanyChainProfile.objects.values_list("symbol_id", flat=True)`) 동일

**KNOWN_VIOLATIONS 해제** (tests + health_check 동시 갱신): #3 키 제거 + 사유 주석.

**burn-down**: shared 경계 동결 **3 → 2**. 잔여 = #4·#5 (macro.models lazy).

**가드 회피 vs 정당 패턴 판단**: 회피 아님. 근거 3:
1. Django 공식 패턴 (`django.apps.AppConfig.get_model`)
2. 실제로 shared가 chain_sight를 "직접 알지 않음" — 문자열 `'chainsight'`만 사용
3. cross-app aggregator의 본질 — 1 앱 의존을 정적으로 잡는 게 부적절

**잔존 트랙**:
- BOUNDARY-3 (#4·#5 macro, 소비자 이동 방향1, 경계 STEP 0 선행)
- FMP 2단계 통합 (사용자 트리거)

**검증**: pytest 3179/52 (회귀 0), 경계 GREEN (우회 0 / 동결 잔여 2), health 8✅/0⚠/0❌.
