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

---

## 완료된 작업 (최근 2주)

| Feature | Agent | Completed | Notes |
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

### audit P0 후속 큐 (2026-04-26 야간 자동화 기준, 15건 중 6건 완료)
- [ ] **#5/#14 Permission/Pagination** — DEFAULT_PERMISSION_CLASSES IsAuthenticated 강화 + DEFAULT_PAGINATION_CLASS 도입 + NewsViewSet/StockListAPIView/Users.get/UserFavorites 무제한 응답 4건 정리. 회귀 영향 큼, 별도 PR
- [ ] **#6 admin 뷰 권한** — serverless/views.py 16개 + macro/DataSyncView + sec_pipeline/FilingDataView IsAdminUser 적용
- [ ] **#7 FMP rate_limiter** — 현재 10/min·250/day. Starter 티어면 300/min·10000/day로 정정. **사용자 티어 확인 필요**
- [ ] **#9 Neo4j 동기화 플래그 단일화** — `synced_to_neo4j`/`neo4j_dirty`/`neo4j_synced` 3종 혼재 (57건 분포). DECISIONS는 `neo4j_dirty` 단일. 마이그레이션 동반 큰 PR
- [ ] **#10/#11 indicator_catalog 3일 누적** — 표시 이름 4건 BE/FE 불일치(id 6/7/30/54) + 버그 #14 회귀(id 50/52/58 PE 역수·ROE 스케일·revenueGrowth)
- [ ] **#12/#13 모바일 UX** — MobileNav `/profile` 깨진 라우트 + Header/MobileNav 이중 네비, 터치 타겟 44pt 미달 5건
- [ ] **#15 thesis generate_thesis_summaries** — Celery task 미구현, AISummarySection이 항상 빈 문자열

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
