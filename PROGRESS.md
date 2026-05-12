# PROGRESS.md — 하네스 상태 영속화 로그

> 이 파일은 모든 에이전트가 세션 시작 시 반드시 읽고, 세션 종료 시 반드시 업데이트한다.

## Harness Engineering 전환 완료

- **일자**: 2026-04-12
- **범위**: PROGRESS.md, DECISIONS.md, TASKQUEUE.md, contracts/, CLAUDE.md 하네스 프로토콜, 에이전트별 Sub CLAUDE.md, 하네스 적합도 추적
- **첫 리뷰**: 2026-04-13 — contracts/ 정합성 검증 6건 수정, @qa Evaluator 첫 검증 완료

---

## 현재 활성 작업

> **✅ main 정착 완료 (2026-05-11)**: `origin/main = be2d6c7`. 활성 4개 브랜치 (portfolio / market_pulse_v2 / feature/chainsight-graph-v2 / data_structure_remodeling_V1) 모두 main 통합 머지 완료. origin/main만 단일 정착, 모든 stale 브랜치 정리됨.

### 활성 브랜치 현황 (2026-05-11 기준)

| 브랜치 | 상태 | 비고 |
|--------|------|------|
| `main` | be2d6c7 (HEAD) | 단일 통합 라인 정착 |
| `feature/watchlist-and-docs` (origin) | 보존 | 구브랜치, 상태 미확인 — 추후 검토 |
| `feature/chainsight-graph-v2` (local worktree) | `/Users/byeongjinjeong/Desktop/stock_vis_chainsight_v2` | 별도 worktree에 체크아웃, 안전 보존 |

### 작업 단위

| Feature | Agent | Status | Blocker | Last Updated |
|---------|-------|--------|---------|--------------|
| **audit P0 #14 envelope 단일화 (PR-D 진행 중)** | @backend + @frontend | PR-0/A/B/C 머지 완료. PR-D 작성 완료 (thesis 4 + etf 4 + theme 5 = 13 함수 + ThesisBuilder.tsx 호출자 + types/screener.ts 평탄화 + InvestmentThesis 모델 import 누락 fix) | PR-E(llm_relations + institutional + regulatory/patent + views_admin) 대기 | 2026-05-12 |
| Portfolio Slice 4 Part 2 (E6) | @backend | Part 1 (Step 0~5) 완료, 회귀 160 passed | Part 2 지시서 작성 + 실 LLM 호출 환경 확인 | 2026-05-07 |

---

## 완료된 작업 (최근 2주)

| Feature | Agent | Completed | Notes |
|---------|-------|-----------|-------|
| **audit P0 신규 #5 — Pagination + 응답 상태코드 3건 (envelope 분리)** | @backend | 2026-05-12 | PR-#14 머지. (1) `validation/api/views.py:65, 82, 348` HTTP 200 에러 응답 수정 — `not_in_universe` 200→**422 Unprocessable Entity**, `no_data` 200→**404 Not Found** (FE 실패 분기를 HTTP 상태로 식별). (2) `stocks/views.py` `StockListAPIView`에 `StockListPagination(PageNumberPagination)` 적용 (page_size=50, max=200) — S&P 6000+ 종목 일괄 반환 차단(DoS 표면 축소). (3) `news/api/views.py` `NewsViewSet`에 `NewsArticlePagination` 적용 (page_size=20, max=100) — 누적 시 응답 폭주 차단. **portfolio/marketpulse 영향 없음**: 전역 `DEFAULT_PAGINATION_CLASS` 미설정, ViewSet 단위로만 적용해 v2 API 보호. 회귀 564 PASS. **별도 PR로 이월**: P1 응답 envelope 단일화 (실측 BE 154건+FE 동시 작업, 회귀 위험 매우 큼). |
| **audit P0 신규 #4 — Mobile 44pt 터치 타겟 + hover-only 접근성 9건** | @frontend | 2026-05-12 | PR-#13 머지. Apple HIG 44×44pt / WCAG 2.5.5 미달 9건 처리. 크기 조정 7건(`min-h-[44px]` 적용): PeerContextBar 프리셋 탭, AdminTabNav 6탭, stocks L1 탭, MobileCardList 3 CTA, ScreenerTable 바구니 버튼, screener Pagination 페이지 번호, StockPriceChart 라인/영역/캔들 버튼. 접근성 보완 2건(div→button + onTouchStart + aria-label): SignalSummaryCard(gray 신호 사유 hover-only → 터치 접근 가능), QuarterlySparkline(text-[8px]→text-[11px] + 터치 활성). portfolio·marketpulse 도메인 영향 없음. frontend TS 0 에러. |
| **audit P0 신규 #3 — CircuitBreaker async Gemini 2건 + Neo4j 1건 (7/7 완료)** | @backend | 2026-05-12 | PR-#12 머지. audit P0 #6 권고 7건 전부 완료. (1) `marketpulse/utils/circuit_breaker.py` `CircuitBreaker.acall(func, *args, **kwargs)` 신규 — `tenacity.AsyncRetrying` 사용, sync `call()`과 동일한 상태 머신. (2) `rag_analysis/services/context_compressor.py` `gemini_compress` — `ContextCompressor._compress_single` + `QuestionAwareCompressor._compress_single` 두 클래스에 `await cb.acall(...)` 적용. (3) `rag_analysis/services/llm_service.py` `gemini_rag` — `generate_stream`의 stream 가져오는 호출에 CB(retry_attempts=1로 외부 retry와 중복 방지). (4) `serverless/services/neo4j_chain_sight_service.py` `neo4j_chain_sight` — `is_available()`에 CB 상태 체크 추가(silent failure 위장 차단, 30개 메서드 자동 차단), `_run_with_cb()` 헬퍼 추가, `create_stock_node`+`get_related_stocks` 두 핵심 메서드에 명시 CB 적용(다른 28 메서드는 향후 점진 확장). 회귀 45 PASS / 7 skipped / 0 fail. `acall()` smoke 검증: 성공→OK, 2회 실패→OPEN, 3회째 CircuitBreakerError. |
| **야간 자동화 통합 #2 (5/11 base) — tsconfig 클라우드 동기화 제외 + sec_pipeline edge 테스트** | orchestrator | 2026-05-12 | PR-#11 머지. 야간 자동화 base 브랜치 2개에서 의미있는 작업 cherry-pick: (1) `b3a81c4` frontend tsconfig에 macOS Finder/iCloud sync 중복 파일 (`* [0-9].py`, `* [0-9].ts`) 컴파일 제외 (1 file, +12/-1). (2) `29242f0` sec_pipeline edge case 테스트 5건 신규 (`test_*_edge.py` for models/normalizer/quality_checks/ticker_matcher/validators, 7 files, +1114). 로컬 stale base 9개 일괄 삭제 (chore/dead-code-cleanup, fix/broken-tests, fix/fe-type-safety, fix/ts-compile-errors, test/fe-thesis-components, test/fe-validation-chainsight, test/rag-analysis-unit-tests, test/sec-pipeline-tests, test/users-unit-tests, test/validation-unit-tests). origin = main 단일, 로컬 = main + feature/chainsight-graph-v2 (worktree) + feature/watchlist-and-docs (보존 결정) 3개. |
| **audit P0 신규 #2 — CircuitBreaker FMP 3건 + Gemini thesis_builder (4/7)** | @backend | 2026-05-12 | PR-#10 머지. `marketpulse/utils/circuit_breaker.py` 재사용. (1) `serverless/services/data_sync.py` `fmp_market_movers` — Market Movers 3개 API 동시 호출을 CB.call로 부분 실패 허용으로 변경 (이전: 하나 실패 시 전체 sync 실패 → 이후: 실패한 mover_type만 빈 리스트). (2) `stocks/services/sp500_eod_service.py` `fmp_sp500_eod` — 500 심볼 루프 누적 실패 차단(threshold=10). (3) `stocks/services/sp500_service.py` `fmp_sp500_constituents` — S&P 500 동기화 단일 진입점, CB open 시 빈 결과 + 명시 로그(silent failure 차단). (4) `thesis/services/thesis_builder.py` `gemini_thesis` — `_parse_free_input`의 Gemini 호출에 CB 적용, open 시 기존 `_fallback_parse()` 자동 사용. 회귀 405 PASS / 33 skipped / 0 fail. **다음 PR 이월 3건**: `gemini_rag`/`gemini_compress`(async wrapper 필요), `neo4j_chain_sight`(메서드 다수 wrap 필요). |
| **audit P0 신규 #1 — Security (StockSync 인증 + 헬스체크 raw exception)** | @backend | 2026-05-11 | PR-#9 머지. (1) `stocks/views.py` `StockSyncAPIView` `permission_classes = []` → `[IsAuthenticated]` + `throttle_classes = [UserRateThrottle]`. 비인증 외부 FMP API 트리거(cost amplification) 차단. (2) `api_request/admin_views.py` `HealthCheckView` DB/Cache/Provider 체크의 `"error": str(e)` 응답 노출 제거, `logger.exception()`으로 내부 로그만 보존, 응답은 status enum (healthy/unhealthy/degraded)만. connection string / 내부 호스트 / 자격증명 메시지 외부 유출 차단. (3) `config/settings.py` `DEFAULT_THROTTLE_RATES`에 `user: '60/min'`, `anon: '20/min'` 신규(market_pulse_* 키 유지). 신규 테스트 5건 PASS + 인근 회귀 219 PASS. 부수: macOS Finder/iCloud sync 마이그레이션 중복 37개(`* [0-9].py`) 환경 정리 — git track 안 됨, 동일 환경 재발 가능. |
| **main 정착 — 4개 활성 브랜치 통합 머지 + 브랜치 일괄 정리** | orchestrator | 2026-05-11 | 4개월 정체 main(022bb46→**be2d6c7**) 일괄 정착. (1) market_pulse_v2 시간순 4분할 PR (B1 Spring Foundation 108c / B2 Harness+SEC+Chain Sight v1 44c / B3 Audit P0+Chain Sight v2+Portfolio Slice 1+Pulse Phase 1 56c / B4 Portfolio Slice 2~7+Pulse PR-A 58c) → PR-#3~6 머지. stacked PR base 변경이 GraphQL Projects classic 경고로 머지 직전 적용 실패 → main에 b1/b2 직접 머지로 보정(c5a4d5d, c77a195). (2) 야간 자동화 6 커밋 cherry-pick 통합 PR-#7 (TS 픽스 1 + sec_pipeline/users/validation 단위 테스트 + thesis/validation-chainsight FE 컴포넌트 테스트, +2640L). (3) feature/chainsight-graph-v2 PR-#8 (FE-PR-1~6 그래프 재설계 v2, 자동 머지 충돌 없음). (4) data_structure_remodeling_V1는 ahead=0(main이 superset)이라 머지 작업 불필요. (5) origin 정리 — merge/b1~b4, merge/nightly-2026-05-10, feature/chainsight-graph-v2, portfolio, market_pulse_v2, data_structure_remodeling_V1, feat/eod-dashboard-and-improvements 삭제. feature/watchlist-and-docs만 보존. (6) 로컬 stale 100개 야간 자동화 브랜치(`chore/dead-code-cleanup-*`, `fix/broken-tests-*`, `fix/fe-type-safety-*`, `fix/ts-compile-errors-*`, `test/sec-pipeline-tests-*`, `test/users-unit-tests-*`, `test/validation-unit-tests-*`, `test/fe-thesis-components-*`, `test/fe-validation-chainsight-*`, `test/rag-analysis-unit-tests-*` 각 9~12개) 일괄 정리. 의미있는 6개만 PR-#7로 통합, 5/6 이전 4개 카테고리는 의미있는 변경 없음 확인 후 폐기. |
| **PR-A3 재해석 — 카드 스냅샷 테스트 보강** | @backend | 2026-05-11 | PR-A3 모델 3개(BreadthSnapshot/SectorFlowSnapshot/ConcentrationSnapshot)는 Phase 1 복원 시점에 marketpulse 0001_initial에 통합되어 있어 원본 지시서 §5.2(T12~T17 마이그레이션 분리 테스트) 적용 불가. 대신 §5.1(T1~T11 모델 제약)과 §5.3(T19 A2 공존) + ConcentrationSnapshot `clean()` validator(top5≤top10 / top10≤1 / hhi∈[0,1]) 보강. `tests/marketpulse/models/test_snapshot.py` 신규 18 tests PASS (universe choices, unique 제약, FK PROTECT, long-format 11 ETF, JSON top_holdings, is_finalized 일관성, __str__, ordering). 회귀 marketpulse+macro 130 → **148 PASS**. |
| **PR-A2 → `market_pulse_v2` 통합** | @backend | 2026-05-11 | portfolio HEAD에 PR-A1/A2 sub-task 4건(`17c897e` PR-A1 / `a108800` schemas / `2ad8211` 저위험 + 0002 / `f0acbe7` 중·고위험 wip)이 누락된 채로 marketpulse 모델이 옛 스키마로 회귀해 있던 상태. portfolio에서 새 `market_pulse_v2` 브랜치 분기 후 4 commit 시간순 cherry-pick. PROGRESS.md만 매번 충돌해 portfolio 쪽 유지 후 마지막에 통합. 19 파일 변경(+650/-29). PR-A2 0005 마이그레이션은 SeparateDB&State로 reverse-safe 정렬 (RenameField가 인덱스 ProjectState ref 자동 갱신 안 함 문제 보정). marketpulse 검증: `manage.py check` 0 issues, `makemigrations --check --dry-run` no changes, forward/reverse 모두 통과. |
| Portfolio Slice 4 (E6) Part 1 — Step 0~5 | @backend | 2026-05-07 | E6 schema/service/view/Mock test/hybrid 7 fixture. 회귀 123 → 160 passed (+37). 5 step commit + docs/instructions commit. 케이스 A(D-7 분석 엔진 의존)·D(Slice 2 fixture 함수명 정정) 발생, B/C/E 미발생. D2.B 글쓰기 가설 4번째 외삽 검증 준비. Part 2(Step 6~9)에서 실 LLM 호출 + #2 score 산식 통합 |
| **PR-A2 중·고위험 필드 변경** | @backend | 2026-04-30 | 중위험 RenameField: `is_exposed`→`shown_on_layer0`, `first_exposed_at`→`shown_at`, `inputs_summary`→`prompt_inputs`. 고위험 구조 변경: `matched_symbols`/`matched_keywords` → `entities` (JSONField dict `{"tickers","sectors","topics"}`), `content` → `body`+`body_sections`. 마이그레이션 0003(RenameField) + 0004(RunPython 데이터 보존) + 0005(SeparateDB&State 인덱스 ProjectState 정렬). 운영 코드 8개 파일 갱신, 신규 테스트 21개 추가. f0acbe7 wip → 5/11 정식 정리. |
| **PR-A2 저위험 누락 필드 추가** | @backend | 2026-04-30 | (1) MarketPulseNews에 6 필드: `expires_at` (D5 TTL), `category_confidence`/`relevance_score`, `sentiment_score` nullable, `summary_ko`, `paired_with_anomaly`. (2) BriefingLog에 `cost_usd` + `error_message`. (3) `mark_exposed()` D5 정책 (노출 시 expires_at NULL). (4) 0002_pr_a2_field_extension 마이그레이션 (모두 default/null로 추가). (5) tests/marketpulse/models/test_field_extension.py 8 tests. |
| **PR-A2 schemas/ Pydantic v2 디렉토리 신규** | @backend | 2026-04-30 | `marketpulse/schemas/` 4개 도메인 분리 (`news.py` NewsEntities, `anomaly.py` R02/R04/R09/R12 Evidence, `regime.py` IndicatorValue/IndicatorsSnapshot/MatchedCondition/PendingTransition, `briefing.py` BriefingSection) + `__init__.py` re-export 10종. Pydantic v2 (`Field`, `Literal`, `model_dump()`, `model_config`). tests/marketpulse/schemas/ 14 tests PASS. |
| **PR-A1 v1→v2 마이그레이션 — sector_group GICS 12종 확장** | @backend | 2026-04-29 | `MarketIndex.sector_group` 4종 → **12종(BENCHMARK + GICS 11)** 확장. max_length 20→32, db_index=True, default='BENCHMARK'. 마이그레이션 0005 SCHEMA + 0006 DATA 매핑(A-Ⅲ 3분리, B-Ⅰ dict 하드코딩, idempotent). `marketpulse/calculators/sector_flow.py` `GICS_SECTOR_GROUPS` 11종, `marketpulse/api/views/overview.py` ticker bar 12 그룹. `backfill_v2_a1` management command 신규. tests/macro/ 16 신규 테스트 PASS. |
| Market Pulse v2 Phase 1 코드 복원 + 후속 5건 | @backend + @frontend | 2026-04-29 | (1) marketpulse 도메인/API/tasks/management 복원 + macro 0002~0004 마이그레이션 + 시드 (11 series + 20 indices). (2) drf-spectacular 도입 + `/api/v2/swagger/` `/api/v2/redoc/`. (3) Recharts 5 detail (Regime 레이더 / Breadth AD-line / Sector bar 2종 / Flow 도넛 / Brief 본문). (4) v1 페이지 amber deprecation 배너 + analytics tracking. (5) FRED sync 11 series 622 row 백필 → coverage 0.357→**0.857** (status=OK). 운영 Beat 10 PeriodicTask 등록. 64 tests PASS. 📎 `docs/operations/marketpulse_v2_*.md`, `docs/architecture/marketpulse_v2_api_contract.md` |
| audit P0 #8 — Beat NY 16:30 Gemini 충돌 분산 | orchestrator | 2026-04-27 | extract-daily-news-keywords를 16:30 → 16:45로 이동. analyze-news-deep-batch와 15분 간격 확보. **운영: PeriodicTask DB도 동일 시각으로 update 필요(#28 패턴)** |
| audit P0 #1~4 — settings.py 보안 환경변수화 | orchestrator | 2026-04-27 | 70d6a68. SECRET_KEY/JWT_SIGNING_KEY/DEBUG/CORS/NEO4J_PASSWORD env-driven + 운영 가드 + .env 600. 회귀 2096 passed. 사용자 후속: API 키 회전 + .env 신규 변수 추가 |
| 야간 자동화 결과 통합 (4/25~4/27) | orchestrator | 2026-04-27 | merge: chore/dead-code-cleanup-20260425 (thesis __all__) + test/users-unit-tests-20260425 (Watchlist 631줄) + audit 리포트 24종 + stale 30개 정리. d1985f2 |
| 옛 audit 리포트 21개 정리 → nightly_auto_system/ 일원화 | orchestrator | 2026-04-27 | d1985f2. docs/architecture, chain_sight, infra, thesis_control 산재 → 매일 자동 생성되는 nightly_auto_system/reports/{월}/{일}/ 로 흐름 통일 |
| timezone.now().date() → localdate() 일괄 치환 (#29) | orchestrator | 2026-04-25 | 1d3386e. 22개 운영 파일 49건. KST 자정~09시 잠복 결함, common-bugs #29 추가 |
| Alpha Vantage provider 전면 제거 | orchestrator | 2026-04-25 | df85496. -3001 lines, 26 files. PeriodicTask 좀비 2건(collect-sentiment-av-*) 삭제. .env/scripts/settings.local.json 평문 키 제거 |
| 보안: SSH 키 차단 + settings.local.json 평문 API 키 제거 + deny/ask 정책 | orchestrator | 2026-04-25 | d96e434. .gitignore에 OpenSSH/PEM 패턴 + dlswnl545/heaven545 명시. local 권한 정책 deny 11건/ask 12건 추가 |
| 마켓 그래프 초기 노드 간격 + zoomToFit 개선 | orchestrator | 2026-04-24 | b97408c. ResizeObserver, force 동적, onEngineStop fit |
| Chain Sight 시드 캐시 안정화 (#27) + Beat drift 복구 (#28) | orchestrator | 2026-04-24 | f50b3f3. settings_test.py LocMem 격리, SeedSnapshot 영속화, `_get_today_seeds` 3단 폴백, heat_score / sec-seed-relations PeriodicTask 재등록, snapshot cleanup 주간 배치 |
| 하네스 잔여 개선 3건 | orchestrator + @qa | 2026-04-13 | sec-pipeline 스펙 상세화, shared-types.ts 연결, QA 검증 |
| 하네스 contracts/ 정합성 검증 | @qa | 2026-04-13 | 6건 불일치 수정 (chainsight/validation API) |
| 하네스 엔지니어링 전환 | orchestrator | 2026-04-12 | PROGRESS/DECISIONS/TASKQUEUE/contracts/HARNESS_FITNESS |
| CLAUDE.md 최신화 (5개 앱, 버그 #25~26) | orchestrator | 2026-04-12 | a09662f |
| Chain Sight 단계별 설계 문서 3개 | orchestrator | 2026-04-10 | API/시드/UI_UX 설계 |
| Chain Sight 레거시 설계 문서 정리 | orchestrator | 2026-04-09 | 8a3eec1 |
| FMP rate limit 보호 강화 + NewsCard 방어 | @backend + @frontend | 2026-04-08 | ea45b44 |
| Validation peer group 전환 버그 수정 | @frontend | 2026-04-07 | 37c2b67 (버그 #26) |
| SEC Pipeline 전체 (17 PR) | @backend + @rag-llm | 2026-04-04 | 10-K 공급망+사업모델 추출 완료 |

---

## 다음 세션에서 할 일

### audit P0 후속 큐 (2026-04-26 야간 자동화 기준, 15건 중 12건 완료)
- [x] **#5 Permission 강화** — `DEFAULT_PERMISSION_CLASSES`: IsAuthenticatedOrReadOnly → **IsAuthenticated** (GET 무차별 노출 차단). users/PublicUser·LogIn에 명시 [AllowAny] 추가. news ML 모니터링 액션 4종(`ml_status`/`ml_shadow_report`/`ml_weekly_report`/`ml_lightgbm_readiness`)에 [IsAdminUser] 추가. 영향 받는 테스트 44건 force_authenticate/force_login 패턴으로 일괄 수정 (5 파일 fixture override + watchlist `auth_user` fixture). 회귀 2182 PASS / 51 skipped / 0 fail (2026-04-29).
- [ ] **#14 Pagination 표준** — 응답 envelope 결정(옵션 A: `{success, data, meta}` vs 옵션 B: DRF 기본)이 선결 조건. 별도 PR로 분리. 영향: NewsViewSet list 액션 응답 형식 변경 → 프론트엔드 동시 작업 필수.
- [x] **#6 admin 뷰 권한** — serverless/views.py 15건 (IsAdminUser 7 + IsAuthenticated 8) + macro/DataSyncView + sec_pipeline/FilingDataView IsAdminUser 적용 (2026-04-29). 73 tests PASS, Django check 0 issues.
- [x] **#7 FMP rate_limiter (Starter Plan)** — 사용자 티어(Starter) 확인 후 정정. stocks/services/rate_limiter.py LIMITS 10/250 → 300/10000, macro/services/fmp_client.py request_delay 0.5 → 0.2, CLAUDE.md/DECISIONS.md/coding-rules.md/serverless-README/marketpulse_v2_runbook/market-pulse user-guide 6개 docs 정정. api_request/rate_limiter.py는 이미 Starter 80% 안전 마진(240/8000) 적용. 207 tests PASS (2026-04-29).
- [x] **#9 Neo4j 동기화 플래그 단일화** — `synced_to_neo4j`/`neo4j_synced` 제거, `neo4j_dirty` 단일 소스로 통일. (1) `RelationConfidence.synced_to_neo4j` 제거 (필드 + index + neo4j_sync.py 1 + relation_tasks.py 6 + sync_tasks.py 1 + sec_pipeline/tasks.py 1 = 9건). (2) `CompanyChainProfile.neo4j_synced` (반전 의미) → `neo4j_dirty` 의미 통일 (sync_tasks.py 3건). (3) 마이그레이션 0008_unify_neo4j_flags 작성 (AddField → RunPython 반전 → RemoveField 순서로 데이터 보존). 회귀 2182 PASS / 51 skipped / 0 fail (2026-04-29).
- [x] **#10 indicator_catalog 표시 이름** — id 6/7/30/54 BE/FE 풀 네임 모두 일치 확인. audit 도구 outdated cache의 false positive로 closing (2026-04-29).
- [x] **#11 indicator_catalog #14 회귀 메타데이터 + fetcher 분기** — id 50/52/53/58 data_params에 inverse/scale_multiplier/endpoint/audit_note 명시. `thesis/tasks/eod_pipeline.py`에 `_apply_value_postprocess` (inverse/scale_multiplier 후처리) + `_fetch_fmp_ttm_or_growth` (TTM/financial-growth endpoint 분기) 헬퍼 추가, `_fetch_fmp_value`에 thesis target fallback + 분기 통합. tests/thesis/test_fmp_value_postprocess.py 13 tests + thesis 18 tests + marketpulse 68 tests PASS (2026-04-29).
- [x] **#12 MobileNav 깨진 라우트 + 이중 네비** — `/profile`→`/mypage` + Header 모바일 햄버거 hidden (MobileNav 단일 네비) (2026-04-29). TS strict PASS.
- [x] **#13 터치 타겟 44pt** — MobileNav `min-h-[44px]` + Header 햄버거 `min-h/min-w-[44px]` + aria-label (2026-04-29).
- [x] **#15 thesis generate_thesis_summaries** — `thesis/tasks/summary.py` Celery task 구현 + Beat 등록 (NY 18:35 평일, snapshot 후 5분) + 5 tests PASS (2026-04-29)

### 운영 후속 (사용자 수동)
- [ ] **노출 위험 키 회전**: FMP / Marketaux / Finnhub API 키 발급사 콘솔에서 회전
- [ ] **.env 추가**: `SECRET_KEY=<generated>`, `JWT_SIGNING_KEY=<generated>`, `DJANGO_DEBUG=True`. 운영 .env에는 추가로 `DJANGO_ALLOWED_HOSTS`, 강력한 `NEO4J_PASSWORD`
- [ ] **Beat DB sync (#8/#28 패턴)**: 운영 PeriodicTask `extract-daily-news-keywords`의 minute을 30 → 45로 update (DatabaseScheduler가 dict를 무시하므로 DB 업데이트 필수)
- [ ] **Alpha Vantage 무료 티어 키 방치 확인** (revoke UI 부재 → Alpha Vantage 계정 자체 비활성화 검토)

### 작업 중
- [x] ~~PR-Security 2건~~ — **PR-#9 머지 (2026-05-11)**
- [x] ~~PR-CircuitBreaker 4/7건~~ — **PR-#10 머지 (2026-05-12)** (FMP 3 + thesis_builder)
- [x] ~~PR-CircuitBreaker 잔여 3/7건~~ — **PR-#12 머지 (2026-05-12)** (async Gemini 2 + Neo4j 1, **audit P0 #6 완료**)
- [x] ~~PR-Mobile44pt 9건~~ — **PR-#13 머지 (2026-05-12)**
- [x] ~~PR-Pagination P0 3건~~ — **PR-#14 머지 (2026-05-12)** (validation 상태코드 + StockList/News 페이지네이션)
- [/] **Phase 5 핵심 잔여: P1 응답 envelope 단일화** — 분할 진행 중
  - [x] **PR-0 (2026-05-12, PR #15 머지)**: `config/exception_handler.py` + `config/serializers.py:ErrorSerializer` + `rag_analysis/exceptions.py`(4) + `serverless/exceptions.py`(8) + `REST_FRAMEWORK.EXCEPTION_HANDLER` 등록 + 계약 테스트 18건 PASS + `contracts/shared-types.ts:ApiError` 추가 + `test_trending_invalid_timeframe` 회귀 픽스 1건. 외부 의미 동등(기존 `raise NotFound` 41건은 `detail` 동일, `code`/`status_code` 키만 추가). 📎 `docs/features/api_envelope/policy.md`
  - [x] **PR-A (2026-05-12, PR #16 머지)**: `rag_analysis/views.py` 36건 helper 호출 → `raise` 패턴 + 평탄 응답. helper 2개 정의(28 LOC) 제거. 신규 도메인 예외 4종 추가(`BasketFull`, `DuplicateItem`, `CapacityExceeded` 400 + `CacheUnavailable` 503). `frontend/services/ragService.ts` interceptor 제거(unwrap 폐기). 전체 회귀 1869 PASS / 51 skipped / 0 failed.
  - [x] **PR-B (2026-05-12, PR #17 머지)**: `serverless/views.py` 35-886 라인 5개 소도메인 15 함수 변환 (movers + keywords + health + breadth + heatmap). 5개 캐시 키 envelope v2 마이그레이션 (`env2:` prefix). 회귀 1869 PASS.
  - [x] **PR-C (2026-05-12, PR #18 머지)**: `serverless/views.py` screener 도메인 14 함수 변환 (presets/execute/filters/advanced/alerts/sharing/trending). `frontend/services/screenerService.ts` alerts·sharing·createPreset 응답 타입 평탄화 + `app/screener/page.tsx` sharePreset 호출 패턴 갱신. `screener_filters` 캐시 키 env2 마이그레이션. 회귀 1869 PASS.
  - [/] **PR-D (2026-05-12, PR 작성 중)**: `serverless/views.py` thesis 4 + etf 4 + theme 5 = 13 함수 변환. ThesisBuilder.tsx 호출자(`response.success`/`.data`/`.warning` 분기) 평탄으로 갱신 + `types/screener.ts` `ThesisResponse`/`MyThesesResponse` 평탄 타입. `InvestmentThesis` 모델 import 누락 fix (운영 버그). 회귀 1869 PASS.
  - [ ] PR-E 대기: llm_relations + institutional + regulatory/patent + views_admin 1건
- [ ] Neo4j 28개 잔여 메서드 점진 CB 확장 (`_run_with_cb` 헬퍼 활용, P2 priority)
- [ ] Phase 5 후속 P1 — Thesis ValidityScore 주1회 Celery, 역제안(Contrarian Nudge), LLM 프롬프트 인젝션 sanitization, cleanup_seed_snapshots Beat 등록, indicator id 39 `DX-Y.NYB`→`DXY`
- [ ] Thesis Control FE-PR-3 (대화형 빌더) 착수 (TC-3)
- [ ] Portfolio Slice 4 Part 2 (E6 Step 6~9: 실 LLM + 토큰 측정 + 회고 + #2 score 산식 통합)
- [ ] QA follow-up: chainsightService.ts fetch() → authAxios 통일
- [ ] QA follow-up: RelationCardPanel 에러 UI 추가
- [ ] 정기 시크릿 스캔 스크립트 도입 검토 (KB 큐 cdc4d19e 참고)
- [ ] feature/watchlist-and-docs 브랜치 상태 검토 (보존 vs 삭제)
