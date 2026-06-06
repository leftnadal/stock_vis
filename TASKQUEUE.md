# TASKQUEUE.md — 에이전트 간 오케스트레이션 큐

> 에이전트는 자신에게 할당된 태스크 중 `depends_on`이 모두 `done`인 것만 착수한다.
> 상태: `todo` → `in_progress` → `review` → `verified` → `done` / `blocked`

---

## Chain Sight 마켓 뷰 (redesign v1)

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|-----------------|
| CS-R1 | Schema 마이그레이션 (previous_status, neo4j_dirty) | @backend | - | done | `chainsight/migrations/0005_add_neo4j_dirty_previous_status.py` |
| CS-R2 | Seed Selection Task (14개 함수, 매일 13:00 UTC) | @backend | CS-R1 | done | `chainsight/services/seed_selection.py`, `chainsight/tasks/seed_tasks.py` |
| CS-R3 | Neo4j Dirty Sync (undirected 정규화) | @infra | CS-R1 | done | `chainsight/services/neo4j_sync.py`, `chainsight/tasks/neo4j_dirty_sync_tasks.py` |
| CS-R4 | 마켓 뷰 4개 API (seeds, sector/graph, neighbors, signals) | @backend | CS-R2, CS-R3 | done | `chainsight/api/views.py`, `chainsight/api/urls.py` |
| CS-R5 | FE 상태 + 섹터 바 + 그래프 캔버스 | @frontend | CS-R4 | done | `explorationStore.ts`, `SectorBar.tsx`, `MarketGraphCanvas.tsx` |
| CS-R6 | 탐색 트레일 + 관계 카드 | @frontend | CS-R5 | done | `ExplorationTrail.tsx`, `RelationCardPanel.tsx` |
| CS-R7 | 체인 스토리 피드 | @frontend | CS-R5 | done | `ChainStoryFeed.tsx` |
| CS-R8 | 코드 리뷰 | @qa | CS-R4~R7 | verified | 📎 `docs/chain_sight/task_done/chain_sight_redesign_V1/qa_evaluator_review_01.md` |
| CS-R9 | 커밋 + 머지 | orchestrator | CS-R8 | todo | PR |

---

## Thesis Control Phase 2 (프론트엔드)

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|-----------------|
| TC-3 | 대화형 빌더 (AI 조산사 UX) | @frontend | - | todo | 📎 `docs/thesis_control/plan/thesis_control_design.md` |
| TC-4 | 지표 설정 페이지 | @frontend | TC-3 | todo | - |
| TC-5 | 관제실 대시보드 (화살표+달 시각화) | @frontend | TC-4 | todo | - |
| TC-6 | 알림 + 마감 관리 | @frontend | TC-5 | todo | - |

---

## shared 경계 부채 소진 (#31 / 2026-06-01)

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|-----------------|
| BOUNDARY-1 | ~~shared → apps.market_pulse.utils.circuit_breaker 2건 청소~~ | @backend | - | **done** (2026-06-01, `d30915e`) | circuit_breaker → `packages/shared/api_request/` 승격으로 자연 해소. `KNOWN_VIOLATIONS` 2건 동시 삭제 완료. burn-down 5→3. |
| BOUNDARY-2 | ~~shared → apps.chain_sight.models 1건 청소~~ | @backend | - | **done** (2026-06-01, `80b9280`) | Django `apps.get_model("chainsight", "CompanyChainProfile")` 동적 lookup으로 정적 import 제거 (cross-app aggregator 표준). `KNOWN_VIOLATIONS` 1건 동시 삭제 완료. burn-down 3→2. |
| BOUNDARY-3 | ~~shared → macro.models 2건 청소 (eod_regime_calculator, eod_pipeline, lazy)~~ | @backend | - | **done** (2026-06-04, merge `a9bb229`, slices `[33e5437, 7b6572f, 73861d4, 662fdc4]`, brunch `monorepo/sess-market_pulse`) | 방향2(의존 역전 + 등록 패턴) 채택. `VIXProvider` 포트(`packages/shared/stocks/services/vix_provider.py`) + `MacroVIXProvider`(`apps/market_pulse/services/macro_vix_provider.py`) + `MarketpulseConfig.ready()`에서 `register_vix_provider`. 모델 이동 0 / makemigrations No changes / 회귀 302 GREEN / `KNOWN_VIOLATIONS` 양쪽(tests + health_check) 동시 삭제로 burn-down 2→0. |

> ~~우선순위 1 = `BOUNDARY-1` (top-level이라 가장 위험).~~ **트랙 전체 종결 (2026-06-04, burn-down 5→0)**. 잔여 0건. 동결 추적은 야간 `docs/harness/boundary_ledger.jsonl`에 0 라인이 누적되어 추세 우하향 안정.
> 청소 절차: `docs/harness/SHARED_BOUNDARY_GUARD.md` "소진 절차" 참조 — 향후 새 위반 발견 시 동일 절차 + 본 트랙 close 이후 표준이 된 패턴(common-bugs #31 "패턴 정착").

---

## Iron Trading 출구 (integrations/iron_trading)

> 입력: `docs/trading_bot_api/api_decision_handoff.md` §2-B. 본 트랙은 stock_vis 소유 항목만. verify-first 결정·소비자 구현 지시서는 iron_trading 소유(별 repo).
> 관련 결정: `DECISIONS.md "iron-trading 출구 엔드포인트 STEP 0 발견 — 이미 main 라이브 (2026-06-04)"`.

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|-----------------|
| IT-1 | iron-trading daily-context 라이브 검증 세션 (read-only): 서버 기동 → 실측 200 응답 1건 → 동봉 샘플(`docs/trading_bot_api/samples/200_daily_context_2026-05-22.json`)과 필드 대조(captured_at·snapshot_id 제외) → 에러 샘플(404/400/503) 확인 | orchestrator | - | todo | 검증 로그 (경로 미정) |
| IT-2 | `docs/trading_bot_api/handoff_codex.md` 옛 경로(`iron_trading/`) + 옛 commit(`8c21a52`) → 현재 경로(`integrations/iron_trading/`)로 정리. **수정 전 STEP 0로 실제 경로·commit 재확인(휘발성 — 베이크 금지)** | @backend | - | todo | `docs/trading_bot_api/handoff_codex.md` |
| IT-3 | [보류] 엔드포인트 보강 — 봇이 실제로 필요로 할 때까지 착수 금지. 후보: (a) `exchange` 매핑(현재 광범위 null), (b) `earnings_within_14d` 정확화(현재 `latest_quarter + 90일` 휴리스틱 → 실적 캘린더 기반), (c) `themes[].tone` 활성화(현재 `"neutral"` 하드코딩 → `CompanyNarrativeTag.narrative_sentiment` 매핑), (d) 다중 유니버스(`us_total` 등, 현재 `us_core`만) | @backend | - | hold | - |

---

## Nightly 트리아지 추적 (git 밖 발견 ↔ git 안 변경)

> 야간 메일 보고서(`~/stock-vis-nightly/reports/YYYYMM/DD/`)의 발견 1건은 분류 → 본 표 등록 → 처리.
> 보고서엔 git 히스토리가 없다 → **처리 추적은 harness가 유일선** → 분류한 발견은 전부 등록 (기각/보류 포함).
> 분류·라우팅 규칙: `DECISIONS.md "Nightly 메일 트리아지 라우팅 규칙 (2026-06-03)"` 참조.

**상태**: `신규` / `라우팅됨` / `진행` / `보류` / `완료` / `기각`
**컬럼 정의**:
- `출처보고서`: `YYYY-MM-DD/섹션명` (예: `2026-06-03/CRITICAL`)
- `분류`: `ops` / `app(<앱명>)` / `shared` / `HALT`
- `목적지`: `ops` 풀 지시서 / `<앱> Claude Project` / `사용자 수동`
- `트리거(보류시)`: 재개 조건 명시 (예: "shared 행위변경 합의 후")
- `처리세션/커밋`: 완료 시 커밋 해시 — **git 밖 발견 ↔ git 안 변경**을 잇는 유일한 끈
- `baseline`: `🆕신규` / `⬆️악화` / `➡️유지`

| ID | 등록일 | 출처보고서 | 분류 | 목적지 | 상태 | 트리거(보류시) | 처리세션/커밋 | baseline |
|----|--------|-----------|------|--------|------|---------------|--------------|----------|
| NT-1 | 2026-06-04 | 2026-06-04/야간자동화 | ops | 📎 `docs/nightly_auto_system/triage/NT-1_nightly_duplicate_run.md` | **완료(재분류)** | - | STEP 0 → 자동화 정상, 메일 본문 표시 버그 (사용자 손 영역) | 🆕신규 |
| NT-2 | 2026-06-04 | 2026-06-04/뉴스LLM | ops (운영) | 📎 `docs/nightly_auto_system/triage/NT-2_llm_analysis_rate_drop.md` | **완료** | - | 좀비 종료(56586/91784) + launchd 재기동(PID 17499) + import 경로 미스매치 해소 검증 (16:17 KST) | 🆕신규 |
| NT-2b | 2026-06-04 | NT-2 후속 | app(news) | apps/news Claude Project | 신규 | - | - | 🆕신규 |
| NT-7 | 2026-06-04 | 2026-06-04/marketpulse | app(market_pulse) | TBD | 신규 | - | - | 🆕신규 |
| NT-8 | 2026-06-04 | NT-2 부산물 | ops (보고서) | 📎 `packages/shared/metrics/services/daily_report.py` + `templates/email/daily_report.html` + `tasks.py` | **완료** | - | 퍼널 N→M→K→J + 실행건강 J/K + 점수 기록률 M/N + null률 NT-2b 포인터. 6/3 K=3·J=3 재현. pytest 132 passed. | 🆕신규 |
| NT-9 | 2026-06-06 | 2026-06-06 archive 시스템 | ops (인프라) | 📎 `packages/shared/metrics/services/daily_report.py` `save_mail_archive()` + `.gitignore` `mail_archive/` | **완료** | - | 메일 발송 직후 `mail_archive/YYYY/MM/DD.md` 마크다운 사본 저장. best-effort(메일·archive 독립). assistant Read 직접 트리아지 자동화. 6/6 archive 5695B 생성 검증. | 🆕신규 |
| NT-10 | 2026-06-06 | 2026-06-06 메일 2회 발송 | ops (자동화) | TBD | 신규 | - | - | 🆕신규 |
| NT-11 | 2026-06-06 | beat_schedule_audit | ops (Beat) | TBD | 신규 | - | - | 🆕신규 |
| NT-3 | 2026-06-04 | 2026-06-04/노드속성 | app(chainsight) | 📎 `triage/NT-3to6_app_stubs.md` § NT-3 → chainsight Claude Project | 라우팅됨 | - | - | 🆕신규 |
| NT-4 | 2026-06-04 | 2026-06-04/관계균형 | app(sec_pipeline) | 📎 `triage/NT-3to6_app_stubs.md` § NT-4 → sec_pipeline Claude Project | 라우팅됨 | - | - | 🆕신규 |
| NT-5 | 2026-06-04 | 2026-06-04/구조분석 | app(chainsight) | 📎 `triage/NT-3to6_app_stubs.md` § NT-5 → chainsight Claude Project | 라우팅됨 | - | - | 🆕신규 |
| NT-6 | 2026-06-04 | 2026-06-04/뉴스커버 | app(news) | 📎 `triage/NT-3to6_app_stubs.md` § NT-6 → news Claude Project | 보류 | NT-2 분석률 회복 후 재평가 | - | 🆕신규 |

**STEP 0 부산물 (2026-06-04)**:
- **NT-7 신규 발견** (NT-2 STEP 0 중): `~/Library/Logs/stockvis/celery-worker-error.log`에서 `marketpulse.tasks.regime.mp_calc_regime_15min` + `mp_detect_anomaly_5min` 반복 retry — `FileNotFoundError(2, 'No such file or directory')`. 분류: app(market_pulse), 영향: 5분 단위 시그널 누적 미생성. 별도 STEP 0 후 핸드오프 예정.
- **NT-2b 신규 등록** (NT-2 조치 후): import 미스매치는 해결됐으나 Tier A 임계 0.7이 너무 빡빡(어제 349건 중 3건만 통과 = 0.86%). importance_score null률도 41~68%. 분류: app(news), 한 줄 문제 = "Tier 임계 + ML 채움률 동시 조정 필요", STEP 0 = 임계 통과율 회복(예: 0.5 임계 시 일일 분석 가능 수) 시뮬레이션. 행위보존 = 기존 Tier B/C 로직 손상 금지.
- **NT-8 신규 등록** (NT-2 조치 후 발견): Daily Report 본문의 "LLM 분석률" 지표가 `전체 24h 신규 ÷ 분석`으로 계산 — 시스템 설계(Tier A+ 임계 분석)와 분모/분자 정의 불일치. 보고서 본문 생성 측 보정 필요(사용자 손 영역, `run_tier3_audits.sh` 메일 빌드 또는 별도 본문 빌더).

**2026-06-06 회차 신규 발견**:
- **NT-9 (완료)**: 메일 복붙 부담 → `mail_archive/YYYY/MM/DD.md` gitignored 마크다운 사본 자동 저장. assistant가 `Read /Users/byeongjinjeong/Desktop/stock_vis/mail_archive/<오늘>.md` 로 직접 읽음.
- **NT-10 신규**: 6/6 회차에 동일 보고서가 2회 발송됨 (N=852 / N=840 약 1분 차이). Beat 스케줄은 `metrics-daily-report-7am-kst` 단일이고 cron 비어있음 → `send_daily_report_task`의 `max_retries=2` 또는 워커 재기동 시점 재실행 의심. STEP 0: 워커 로그(`celery-worker.log`)에서 task_id 별 호출 횟수 + retry 흔적 확인.
- **NT-11 신규**: `beat_schedule_audit` 자체 보고서가 발견한 4건 위험.
  - 🔴 `validation-weekly-batch` config dict만 존재 (DB 미등록, 버그 #28 정확 해당) → 주간 배치 자동 실행 미보장
  - 🔴 `refresh-korean-overviews-monthly` 03:00 ≈500 call → RPD 폭발 위험
  - 🔴 `sec-sync-dirty-neo4j` */5 + solo pool → 백로그 누적
  - 🟡 장중 `*/5` 동시 발사 충돌 (`update-realtime-prices` + `update-market-indices`)
- **NT-2b 우선순위 상승**: importance_score null률 5/29(99%) → 6/4(84%) → 6/5(82.7%) → 6/6(80.1%) 정체. 수집 N은 315→852로 2.7배 증가했는데 채움 절대값은 비례 증가 안 됨 → ML/규칙 엔진 처리량 한계. apps/news 핸드오프 우선순위 ↑.

**발견 상세 (요약)**:
- **NT-1**: 야간 보고서 22개 = 11종 ×2 흔적 (첫 12종 + 두 번째 10종, performance/security 누락). 자동화 중복 트리거 의심(launchd + cron 동시 등록 / 수동 재실행). → ops STEP 0: `launchctl list | grep stockvis` + `crontab -l` 동시 등록 여부 확인.
- **NT-2**: 24h 신규 뉴스 315건 중 LLM 분석 3건만 완료, 312건 pending(분석률 1.0%). Gemini paid tier 할당량 / Celery 큐 잠금 / retry backoff 의심. → ops STEP 0: `celery inspect active` + Gemini 콘솔 quota + `news.tasks` retry 로그 확인.
- **NT-3**: Stock 속성 채움률 `business_model_type=0.0%`, `overall_grade=0.0%`, `theme_tags=0.0%` + ChainProfile 미생성 31종목. 모델 필드 추가 후 backfill 미수행 의심. → chainsight 스텁: 한 줄 문제 = "신규 3 필드 + 31 종목 미생성", STEP 0 = "필드 추가 시점·calculate_all_profiles 동작 여부", 행위보존 = "기존 채움 데이터 손상 금지".
- **NT-4**: SUPPLIES_TO 61개 (vs PEER_OF 8674), UnmatchedCompanyQueue 1011건 pending. 상위: Flex Ltd. ×4, Compuware ×4, Adyen ×3, JERA ×3, Mitsui ×3. → sec_pipeline 스텁: 한 줄 문제 = "alias 매핑 미흡 → SUPPLIES_TO 추출률 저조", STEP 0 = "상위 빈도 회사명 수동 alias 룰 / fuzzy threshold 검토".
- **NT-5**: 고립 Stock 5종목 (관계 0). calculate_price_co_movement + update_relation_confidence 누락. → chainsight 스텁: 한 줄 문제 = "5종목 관계 0", STEP 0 = "심볼 식별 + 가격 데이터 존재 여부", 행위보존 = "관계 임계값 변경 금지".
- **NT-6**: 24h 뉴스 커버 51/535=9.5%, 미커버 484종목. → news 스텁: 한 줄 문제 = "종목 단위 수집 제약", STEP 0 = "Finnhub/MarketAux 종목별 vs sector broadcast 비용·rate limit 비교".



> 기각·보류는 `DECISIONS.md`에 "왜"를 남긴다(미래 세션 오해 방지). 표 행에는 결정 링크/커밋만 박는다.

---

## 보류 (On Hold)

| ID | Task | Agent | Reason | Resume Condition |
|----|------|-------|--------|-----------------|
| MM-L | Market Movers AWS Lambda 전환 | @infra | 비용 최적화 우선순위 낮음 | 트래픽 증가 시 |
| GA-1 | Graph Analysis REST API + Frontend | @backend + @frontend | 모델/서비스만 완료 | Chain Sight 안정화 후 |
| SR (트랙) | 서비스 리모델링 — Dashboard / Chain Sight / Portfolio 3탭 전환 (옛 SR-1~4) | orchestrator + @backend + @frontend + @qa | 미시작 계획서. 44일 정체(2026-04-14~). 브랜치 `data_structure_remodeling_V1` 부재. 재개 시 현 시스템(Slice 14~17) 기준 재설계 필요 | 사용자 명시 재개 신호 + 현 코드 기준 설계 재검증. 설계 사고는 `docs/stock_vis_service_remodeling/` 보존 |

---

## 완료 (최근)

| ID | Task | Agent | Completed | Notes |
|----|------|-------|-----------|-------|
| SESS-CONTRACT | 세션 충돌 방지 트랙 (소프트 강제 = worktree + 계약 헤더 선언) | orchestrator | 2026-06-01 | `docs/harness/SESSION_CONTRACT.md` 신규 + CLAUDE.md "Session Lifecycle" 참조 + STARTUP_CHECKLIST Step 0 추가. 시범 worktree `../stock_vis_mgmt` + `sess/mgmt` 생성. |
| SEC-ALL | SEC Pipeline 전체 (17 PR) | @backend + @rag-llm | 2026-04-04 | 📎 `docs/sec_pipeline/task_done/` |
| NI-v3 | News Intelligence v3 (6 Phase) | @backend + @infra | ~2026-03-20 | 607 tests |
| EOD-1 | EOD Dashboard (14 시그널 + 메인 페이지) | @backend + @frontend | ~2026-03-15 | JSON Baking |
| TC-1 | Thesis Control FE-PR-1 (라우팅+공통) | @frontend | ~2026-03-10 | 7개 라우트 + 5개 공통 컴포넌트 |
| TC-2 | Thesis Control FE-PR-2 (목록+변경+진입) | @frontend | ~2026-03-12 | ThesisListCard + TodayChangeCard |
| VAL-1 | 1차 검증 전체 (Peer+LLM필터) | @backend + @frontend | ~2026-03-05 | 6개 프리셋 + Compute-on-Read |
