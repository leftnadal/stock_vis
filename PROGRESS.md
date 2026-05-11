# PROGRESS.md — 하네스 상태 영속화 로그

> 이 파일은 모든 에이전트가 세션 시작 시 반드시 읽고, 세션 종료 시 반드시 업데이트한다.

## Harness Engineering 전환 완료

- **일자**: 2026-04-12
- **범위**: PROGRESS.md, DECISIONS.md, TASKQUEUE.md, contracts/, CLAUDE.md 하네스 프로토콜, 에이전트별 Sub CLAUDE.md, 하네스 적합도 추적
- **첫 리뷰**: 2026-04-13 — contracts/ 정합성 검증 6건 수정, @qa Evaluator 첫 검증 완료

---

## 현재 활성 작업

| Feature | Agent | Status | Blocker | Last Updated |
|---------|-------|--------|---------|--------------|
| Chain Sight v2 마켓 뷰 (redesign v1) | @backend + @frontend | QA 검증 완료 (91%), 커밋 대기 | 커밋 필요 | 2026-04-13 |
| 서비스 리모델링 (data_structure_remodeling_V1) | @backend | 브랜치 작업 중 | Chain Sight 마켓 뷰 머지 후 | 2026-04-12 |
| **Market Pulse v2 — Phase 1 + 후속 작업** | @backend + @frontend | Phase 1 복원 + drf-spectacular + Recharts + v1 deprecation 배너 + FRED sync (coverage 0.857) + Yahoo sync (Beat 11 task) + v1 collision 8건 + drf-spectacular noise silence + audit P0 #11/#15 (fetcher 분기 + thesis 요약 task) | (자동 흐름) VIX3M/MOVE 다음 평일 NY 17:35 sync | 2026-04-29 |

---

## 완료된 작업 (최근 2주)

| Feature | Agent | Completed | Notes |
|---------|-------|-----------|-------|
| Market Pulse v2 Phase 1 코드 복원 + 후속 5건 | @backend + @frontend | 2026-04-29 | (1) marketpulse 도메인/API/tasks/management 복원 + macro 0002~0004 마이그레이션 + 시드 (11 series + 20 indices). (2) drf-spectacular 도입 + `/api/v2/swagger/` `/api/v2/redoc/`. (3) Recharts 5 detail (Regime 레이더 / Breadth AD-line / Sector bar 2종 / Flow 도넛 / Brief 본문). (4) v1 페이지 amber deprecation 배너 + analytics tracking. (5) FRED sync 11 series 622 row 백필 → coverage 0.357→**0.857** (status=OK). 운영 Beat 10 PeriodicTask 등록. 64 tests PASS. 📎 `docs/operations/marketpulse_v2_*.md`, `docs/architecture/marketpulse_v2_api_contract.md` |
|---------|-------|-----------|-------|
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
- [ ] Chain Sight 마켓 뷰 PR-1~7 커밋 (CS-R9)
- [ ] Thesis Control FE-PR-3 (대화형 빌더) 착수 (TC-3)
- [ ] 서비스 리모델링 Phase 1 계속 (SR-1)
- [ ] QA follow-up: chainsightService.ts fetch() → authAxios 통일
- [ ] QA follow-up: RelationCardPanel 에러 UI 추가
- [ ] 정기 시크릿 스캔 스크립트 도입 검토 (KB 큐 cdc4d19e 참고)
