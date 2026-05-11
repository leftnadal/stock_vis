# PROGRESS.md — 하네스 상태 영속화 로그

> 이 파일은 모든 에이전트가 세션 시작 시 반드시 읽고, 세션 종료 시 반드시 업데이트한다.

## Harness Engineering 전환 완료

- **일자**: 2026-04-12
- **범위**: PROGRESS.md, DECISIONS.md, TASKQUEUE.md, contracts/, CLAUDE.md 하네스 프로토콜, 에이전트별 Sub CLAUDE.md, 하네스 적합도 추적
- **첫 리뷰**: 2026-04-13 — contracts/ 정합성 검증 6건 수정, @qa Evaluator 첫 검증 완료

---

## 현재 활성 작업

> **🔴 main 정체 경고**: `origin/main = 022bb46` (2026-04 초). 4개 활성 브랜치 모두 main 대비 130~214 커밋 ahead. main catch-up 전략 결정이 모든 PR의 선결 조건.

### 활성 브랜치 현황 (2026-05-01 기준)

| 브랜치 | Agent | 작업 내용 | main 대비 | 상태 | 다음 액션 |
|--------|-------|----------|----------|------|----------|
| `portfolio` | @backend | Slice 1 (E1+GARP) + Slice 2 (E5) + Slice 3 (E2) 완료 + **Slice 4 (E6) Part 1 완료** | +218 | Slice 4 Part 2 대기 (Step 6~9: 실 LLM 호출 + 토큰 측정 + 회고 + score 산식 통합) | Part 2 지시서 작성 후 진입 |
| `market_pulse_v2` | @backend | portfolio 기반 + PR-A1/A2 4 commits cherry-pick 통합 (2026-05-11). 이전 `marketpulse-v2`(legacy, 하이픈)는 본 브랜치로 통합 후 삭제 | portfolio+4 | PR-A2 검증 완료, push/머지 대기 | PR-A3/C/G 진행 또는 정리 후 push |
| `feature/chainsight-graph-v2` | @frontend | 그래프 재설계 v2 (설계 명세 + FE-PR-1~6) | +210 | **origin push 완료** (2026-05-01), PR 보류 | main catch-up 후 PR |
| `data_structure_remodeling_V1` | @backend + @frontend | Chain Sight v2 마켓 뷰 (redesign v1, PR-1~7) | +132 | QA 91% 통과, 커밋 대기 | feature/chainsight-graph-v2와 통합 머지 검토 |

### 작업 단위

| Feature | Agent | Status | Blocker | Last Updated |
|---------|-------|--------|---------|--------------|
| **main 일괄 catch-up** | orchestrator | 전략 결정 대기 | 사용자 의사결정 필요 | 2026-05-01 |
| Chain Sight v2 마켓 뷰 (redesign v1) | @backend + @frontend | QA 검증 완료 (91%), 커밋 대기 | main catch-up 선행 | 2026-04-13 |
| Chain Sight 그래프 재설계 v2 (FE-PR-1~6) | @frontend | origin push 완료, PR 보류 | main catch-up 선행 | 2026-05-01 |
| 서비스 리모델링 (data_structure_remodeling_V1) | @backend | 브랜치 작업 중 | Chain Sight 마켓 뷰 머지 후 | 2026-04-12 |
| **Market Pulse v2 — Phase 1 + 후속 작업** | @backend + @frontend | Phase 1 복원 + drf-spectacular + Recharts + v1 deprecation 배너 + FRED sync (coverage 0.857) + Yahoo sync (Beat 11 task) + v1 collision 8건 + drf-spectacular noise silence + audit P0 #11/#15 (fetcher 분기 + thesis 요약 task) | (자동 흐름) VIX3M/MOVE 다음 평일 NY 17:35 sync | 2026-04-29 |
| Portfolio Slice 4 Part 2 (E6) | @backend | Part 1 (Step 0~5) 완료, 회귀 160 passed | Part 2 지시서 작성 + 실 LLM 호출 환경 확인 | 2026-05-07 |

---

## 완료된 작업 (최근 2주)

| Feature | Agent | Completed | Notes |
|---------|-------|-----------|-------|
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
- [ ] **main 일괄 catch-up** — origin/main이 022bb46(2026-04 초)에 정체. 200+ 커밋(audit P0, security, marketpulse v2, timezone, chainsight v1/v2/redesign V1/V2, portfolio Slice 1~2 등)이 main 미반영. 도메인별로 PR 분할 정리 필요.
- [ ] Chain Sight 마켓 뷰 PR-1~7 커밋 (CS-R9) — main catch-up 후
- [ ] Chain Sight 그래프 재설계 v2 PR — origin push 완료(2026-05-01), main catch-up 후 PR 생성
- [ ] Thesis Control FE-PR-3 (대화형 빌더) 착수 (TC-3)
- [ ] 서비스 리모델링 Phase 1 계속 (SR-1)
- [ ] QA follow-up: chainsightService.ts fetch() → authAxios 통일
- [ ] QA follow-up: RelationCardPanel 에러 UI 추가
- [ ] 정기 시크릿 스캔 스크립트 도입 검토 (KB 큐 cdc4d19e 참고)
