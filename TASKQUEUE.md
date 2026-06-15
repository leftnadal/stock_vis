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
| CS-R9 | 커밋 + 머지 | orchestrator | CS-R8 | **done** | PR #8 / `be2d6c7` 머지 확인 (2026-06-11 CS-RD1 Part A 정합화) |

---

## Chain Sight 이벤트 보드 개편 (redesign 26.06)

> 첫 화면 정보 구조 역전: 이벤트(테마) 보드 → 관심도 랭킹 → 그래프 드릴다운. 결정 근거: DECISIONS "CS-RD (2026-06-11)".

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|-----------------|
| CS-RD1 | 하네스 정합화 + 테마 데이터 적재 (Phase 0–1) | @backend | CS-R9 | **done** | Part A·B 정합화 + Part C 적재 완료(옵션2: sector+theme w≥1.0, DECISIONS CS-RD-C2). 채움률 60.3%/15그룹, Neo4j :Theme 21/HAS_THEME 536 |
| CS-RD2 | 관심도 M1 엔진 (모델·배치·API, Phase 2) | @backend | CS-RD1 | **ready** (보드 연료 60.3% 확보) | `docs/chain_sight/redesign(26.06)/Cs redesign 02 attention m1 backend.md` |
| CS-RD3 | 이벤트 보드·관심도 랭킹 프론트 (Phase 3–4) | @frontend | CS-RD2 | **blocked** (RD2 선행) | `docs/chain_sight/redesign(26.06)/Cs redesign 03 event board frontend .md` |
| CS-EXT1 | 외부 API 직접 호출 4곳 → shared FMP 래퍼 경유로 이전 | @backend | - | **backlog** (이번 개편 범위 외 — 등록만) | `insider_tasks.py:38`, `sensitivity_tasks.py:80`, `neo4j_loader.py:132,144` (FMP `requests.get` 직접 호출) |
| CS-COV | 정식 섹터 분류 기반 그룹핑으로 커버리지 확장 검토 (ETF 비중 1% 미만 잔여 편입) | @backend | - | **backlog** | NarrativeTag(LLM) 태깅 병합 + w<1.0 잔여 종목 편입 검토 |
| CS-UNIV | 유니버스 확장 범위 분석 — 디렉터 지시서 발행됨, 별도 read-only 세션에서 실행. 확장 자체는 확정, tier 결정은 측정 후 디렉터 세션 | @backend | - | **active** (측정 완료 `9d80cdc`, 디렉터 결정 대기) | `docs/chain_sight/univ_analysis/REPORT.md` — T1 포화/T2 품질우위, 러셀 프록시 차단 |
| CS-EXP | 테마 ETF holdings 확대 + 유니버스 U2 편입 + 백필 (디렉터 지시서) | @backend | CS-RD1·CS-UNIV | **in-progress** (STEP 0 완료 `714b8fd` / Part A (c)복구 2/6 `a7a245e` — ARKK 44·ARKG 32. FMP holdings 전제 붕괴 → CSV 직링크 경로 확정) | `docs/chain_sight/redesign(26.06)/Cs exp universe expansion.md` + `CS-EXP_STEP0_findings.md` |
| CS-EXP-P1 | generic 파서 확장 — Roundhill/Amplify 다중펀드 통합 CSV(Account=<ticker> 필터 + `StockTicker`/`Weightings` 컬럼) 지원 → HACK·BETZ holdings 적재 | @backend | CS-EXP | **todo** (shared 파서 코드 변경 — CS-EXP 세션 범위 밖) | URL 확보됨(amplifyetfs/roundhill), `etf_csv_downloader.py` `_parse_csv` 확장 |
| CS-EXP-P2 | KWEB Cloudflare 우회 — `download_holdings` httpx가 Cloudflare 403, curl는 200. 우회 수단 + `parser_map` `kraneshares` 키 누락 보정 | @backend | CS-EXP | **todo** (downloader 코드 변경) | URL 확보됨(date-based), `etf_csv_downloader.py` |
| CS-EXP-P3 | `_parse_ark_csv` 버그 수정 — 면책행 `ticker=None` → `str(row.get("ticker") or "").strip()`. 수정 시 ARKK/ARKG를 ark 파서로 복귀 가능 | @backend | CS-EXP | **todo** (파서 버그) | `etf_csv_downloader.py:786` |
| CS-EXP-TAN | TAN(Invesco Solar) holdings 소스 — Invesco 다운로드 엔드포인트 403, 공개 직접 CSV 부재. 대안 소스 탐색 필요 | @backend | CS-EXP | **backlog** (소스 부재) | 대안: 타 제공자 holdings 또는 수동 |

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
| NT-7 | 2026-06-04 | 2026-06-04/marketpulse | ops (운영) | 📎 § NT-7 종결 (본 파일 하단 §) | **완료 2026-06-06** | - | Bug #28 Beat drift + 좀비 beat 56670 이중 디스패치. ORM UPDATE 11 row(`task` 컬럼) + 좀비 종료 + 정상 beat 재기동(15151→86614). 검증: regime/anomaly 새 경로 succeeded, unregistered ∆=0(1705 후 06-07 신규 0건), 회귀 302 passed, 코드 diff 0. | 🆕신규 |
| NT-8 | 2026-06-04 | NT-2 부산물 | ops (보고서) | 📎 `packages/shared/metrics/services/daily_report.py` + `templates/email/daily_report.html` + `tasks.py` | **완료** | - | 퍼널 N→M→K→J + 실행건강 J/K + 점수 기록률 M/N + null률 NT-2b 포인터. 6/3 K=3·J=3 재현. pytest 132 passed. | 🆕신규 |
| NT-9 | 2026-06-06 | 2026-06-06 archive 시스템 | ops (인프라) | 📎 `packages/shared/metrics/services/daily_report.py` `save_mail_archive()` + `.gitignore` `mail_archive/` | **완료** | - | 메일 발송 직후 `mail_archive/YYYY/MM/DD.md` 마크다운 사본 저장. best-effort(메일·archive 독립). assistant Read 직접 트리아지 자동화. 6/6 archive 5695B 생성 검증. | 🆕신규 |
| NT-10 | 2026-06-06 | 2026-06-06 메일 2회 발송 | ops | ops | **NT-10/7 진단 → kill실행→검증(6/7)** | - | STEP 0 = TaskResult 2 SUCCESS (07:00 + 07:06 KST 매일), Beat 1회만 발사, worker는 2회 received. 원인 = 좀비 Beat 56670 (PPID 13862 살아있음, cwd=`~/.Trash/stock_vis.icloud_backup.20260516_144329`, default scheduler). kill 완료(21:30). 6/7 07:00 메일 1통 검증 대기. 📎 DECISIONS "좀비 Beat 56670 (2026-06-06)" / common-bugs #33. | 🆕신규 |
| NT-11 | 2026-06-06 | beat_schedule_audit | ops | ops(+shared) | **NT-10 후속 / 가드범위 결정대기→git지시서** | - | NT-11-1(validation-weekly-batch DB 미등록) STEP 0 = 이미 DB 등록·정상 작동 중(last_run=6/6 09:00 UTC, total_run=8). 무효(no-op). 잔여 가드 트랙: 다중 Beat 감지(origin/cwd 기반) + 옵션 없는 beat 알림 — 가드 코드 구현 위치(`config/tasks.py` 또는 watchdog 셸 또는 daily report 섹션) **결정 대기**. NT-11-2/3/4(refresh-korean-overviews-monthly RPD / sec-sync-dirty-neo4j */5 / 장중 동시 발사)는 운영 결정 대기 별도 보류. | 🆕신규 |
| NT-11c | 2026-06-10 | NV-1 후속 | ops | `scripts/health_check.py` | 보류 | NT-11b 착수 시 같은 세션에서 묶어 구현 | **health_check.py에 Neo4j 연결 점검 추가** — `RETURN 1` 인증 확인 + `count(n)` 노드 수 보고를 health_check 항목으로 추가. 시크릿 마스킹 정책 준수(`len + head 4자`만). 비밀번호는 `.env`에서 환경변수 경유 전달 — cmdline 평문 금지(NV-1 STEP 2 패턴 재사용). **배경**: 2026-06-10 NEO4J_PASSWORD 회전 검증(NV-1)에서 health_check.py가 Neo4j를 점검하지 않음이 드러남(문서·git 정합만 점검). 자격증명 회전 실수·컨테이너 다운 시에도 "health_check 통과"가 나와 거짓 안심을 줌. **연계**: NT-11b와 동일 파일 → 묶어 구현. 우선순위 = NT-11b 동급(보류). **수용 기준**: ① Neo4j 컨테이너 down → FAIL/WARN ② up → 노드 수 출력 ③ 어떤 출력 경로에도 시크릿 풀 값 0. | 🆕신규 |
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



## NT-7 — marketpulse Beat schedule drift + 좀비 beat  [완료 2026-06-06]

- 증상: ① unregistered KeyError(regime 등) = Beat DB의 PeriodicTask 11개 task 컬럼이 옛 경로 `marketpulse.tasks.*` (코드는 `apps.market_pulse.tasks.*`). ② FileNotFoundError(anomaly) = 좀비 워커가 옛 yaml 경로 stat 실패 — 좀비 워커 사망으로 이미 정지(613).
- 원인: 코드 경로 이동(PR4) 후 Beat DB 미동기화(Bug #28 drift) + 인터랙티브 zsh에서 띄운 좀비 beat(PID 56670)가 정상 beat(15151)와 동시 가동(이중 디스패치).
- 처리세션(운영 안정화, 코드 0): (B) `kill -TERM 56670` → (A) Django shell ORM UPDATE 11 row(`task` 컬럼만, 옵션②) → 정상 beat 재기동(15151→86614) → 수동 트리거 검증(regime LATE_BULL 0.14s / anomaly CALM 0.09s, 둘 다 새 경로 succeeded). ※ `sync_beat_schedule`은 무용(marketpulse는 `setup_marketpulse_beat`로 DB 직접 등록).
- 검증: unregistered ∆=0 (1704→1705 후 정지, 06-07 신규 0건), FileNotFoundError 613 정체, 좀비 0 / 정상 1셋, `git diff` 빈 결과, 회귀 302 passed.
- 분기: D1(옵션3)대로 intraday 잔류, 구조 이동(STRUCT-CLEANUP)은 DORMANT 유지.

> 기각·보류는 `DECISIONS.md`에 "왜"를 남긴다(미래 세션 오해 방지). 표 행에는 결정 링크/커밋만 박는다.

---

## Trash 청산 트랙 후속 (TR-3/4/4b/NV-2 / 2026-06-11)

> 2026-05-16 `~/.Trash/stock_vis.icloud_backup.20260516_144329` 박제 셸 cwd에서 좀비 Beat 발생(NT-10) → Trash 트리 청산 + 시크릿 전수 회전(FMP `KF9E`→`qA1W` / Anthropic 재발급 / NEO4J `rByK`→재회전) + `.env` 소비자 4종 재기동 완료. 본 표는 청산 트랙의 잔여 후속 9건.

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|-----------------|
| TRASH-1 | `archive/trash-20260516/*` 로컬 태그 5건 — **90일 후(2026-08-14) 처분 검토**. 원격 미push 유지. | orchestrator | - | hold | 재검토일 2026-08-14 |
| TRASH-2 | Trash test 묶음 3건 **cherry-pick 평가 → Tier 2 연계** (~1,662줄, 5/16 기준). 흡수 가치 판정 후 채택/폐기. | @qa | TRASH-1 | todo | - |
| TRASH-3 | **slice8 PROGRESS 정합** — 종결 기록 vs 미흡수 tip 2건 규명 | @qa | - | todo | PROGRESS.md |
| TRASH-4 | **untracked 보존 파일 3건** (`docs/etc/`, `docs/trading_bot_api/{api_decision_handoff,consumer_directive}.md`) commit 여부 결정 | orchestrator | - | todo | - |
| TRASH-5 | **PROGRESS.md L25 stale 해시 갱신** | orchestrator | - | todo | PROGRESS.md |
| TRASH-6 | **Trash 트리 사건 종결 기록** — origin(셸 cwd 박제) + 조치 요약 + D 포렌식 링크 | orchestrator | - | todo | DECISIONS.md |
| TRASH-7 | **worker 로그 FMP 키 평문 기록** — 로그 마스킹 검토 (저위험·위생). 구 `KF9E` 키는 이미 401 dead. | @infra | - | todo | - |
| TRASH-8 | **LLM 인증 실패 가시화** — health_check 기동 ping 검토 (NT-11c 묶음). Anthropic/FMP 키 회전 누락 시 조기 감지. | @infra | NT-11c | todo | `scripts/health_check.py` |
| TRASH-9 | **`.env` 소비자 4종 launchd 일원화** — worker/beat/worker-neo4j는 launchd, daphne만 수동 기동 → daphne plist 등록으로 다음 회전 = `kickstart 4건`. 소비자 목록 문서화. | @infra | - | todo | LaunchAgents + 문서 |
| TRASH-10 | **마스킹 로그 스캔 표준 스크립트 작성** (`scripts/scan_logs_masked.py`) — raw 로그 직접 grep 금지의 구조적 대체. 시크릿 패턴(apikey/api_token/password 등 쿼리파라미터·헤더)을 **값 진입 전 차단**(Python에서 파싱·마스킹, 셸 파이프 미경유)하는 방식. 배경: NV-2/TR-5 마스킹 슬립 2회(`ps\|tr\|sed`, `sed`가 `api_token=` 누락) → 구조적 재발 방지. | @infra | - | todo | `scripts/scan_logs_masked.py` |
| TRASH-11 | **worktree 2건 거취 — DEAD 확정·remove 완료** (TR-7/8 정정). 기존 ALIVE 판정은 **stale 로컬 main 기준 오판**이었음. TR-8 STEP1: unique 커밋 5건(f483634/d4a9690/ce0be51/0b8399a/ef9d064) **전건 origin/main(d5212d4) REACHABLE = DEAD**. `sess-mgmt-phase1-catalog`·`sess-mp-phase1-cleanup` 디렉토리 소멸 + worktree registry 제거 완료(세션 간 외부 선제거, prune 정합). **잔여 결정**: 브랜치 2건 삭제 — 커밋이 origin/main 도달이나 **로컬 main 미도달**이라 `-d` 거부 예상 → 사용자 수동 `-D` 또는 `pull` 후 `-d`. + `sess-mp-kl-f1f3` 머지 시 `82afddb`(TASKQUEUE 9건) 중복은 main `cb5473e`와 동일 → 충돌 시 main 채택. **push/pull 통합 결정과 묶음**. | orchestrator | - | todo | 브랜치 삭제 + push/pull 통합 |
## market_pulse v2 Phase 1 잔여 (2026-06-07 카탈로그 역산 확정)

> 근거: `DECISIONS.md` "## [2026-06-07] Phase 1 PR 카탈로그 역산 확정". 백엔드 A~J done(J는 I 흡수), FRED fetcher done, Translation/Playbook은 Phase 1.5/1.6 이관(범위 외). 본 표는 출시 전 정리할 6 트랙.

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|----------------|
| MP1-K | Phase 1 프론트엔드 Layer0(메인 페이지) — Card A 헤더/지표/regime 표시 | @frontend | - | **완료 2026-06-10 (static 기준)** | `frontend/app/market-pulse-v2/page.tsx` (Layer0) + `cards/RegimeCardSummary.tsx` + `components/{TickerBar,StatusBanner}.tsx`. 5 card_id 라우팅 + `useOverview()` TanStack Query. 라이브 검증은 `MP-LIVE-VERIFY` 게이트로 분리(아래). 직전 "0%" 측정은 없는 src 경로 grep 오류(common-bugs #31) |
| MP1-L | Phase 1 프론트엔드 카드 컴포넌트 — Card B/C/D/E 4종 + news/health 위젯 | @frontend | MP1-K | **완료 2026-06-10 (static 기준)** | `frontend/app/market-pulse-v2/cards/` 5 Summary + `details/` 5 Detail(+Container) + `components/{AnomalyPanel,CardDrawer,NewsPanel,StatusBanner,TickerBar}.tsx` + `lib/api/marketPulseV2.ts` (30+ 타입 + 4 fetch). health 위젯은 `StatusBanner` 매핑 추정(`MP-KL-F3` 확인). 라이브 검증 `MP-LIVE-VERIFY` |
| MP1-C-stress | regime classifier `stress_input` 훅 (1줄 인터페이스, Phase 1.5 무재설계 전제) | @backend | - | **완료 2026-06-10** (`ce0be51`) | `apps/market_pulse/regime/classifier.py:classify_inputs(*, stress_input=None)` keyword-only Optional + 즉시 del. 회귀 138 passed (136+2 신규). 행위보존 |
| MP1-M | runbook task 경로 갱신 — `marketpulse.tasks.*` → `apps.market_pulse.tasks.*` (10 task 전건) | @infra(@qa) | - | **완료 2026-06-10** (`ef9d064`) | `docs/operations/marketpulse_v2_celery_tasks.md` 10건 전수 치환. grep 옛 경로=0 / 새 경로=10. NT-7 정합 잔재 정리 |
| MP1-N | market_pulse 능동 모니터링 자산 — `services/news.tasks.check_pipeline_alerts` 패턴을 market_pulse로 확장 (anomaly engine error rate / regime stale / news feed lag 등) | @infra | - | 신규 | `apps/market_pulse/tasks/alerts.py` (TBD) + runbook 모니터링 섹션 |
| MP1-A3-sep | A3 마이그레이션 3분리 (`BreadthSnapshot`/`SectorFlowSnapshot`/`ConcentrationSnapshot`을 `0002`/`0003`/`0004`로 분리) | @backend | - | 저우선 (미루기 가능, 행위보존) | `apps/market_pulse/migrations/` |
| MP1-test-gap | PR-I cards/health 도메인별 serializer 분리 + 통합테스트 / PR-B fetchers 테스트 모듈 | @backend + @qa | - | 신규 | `apps/market_pulse/api/serializers/` + `tests/marketpulse/{fetchers,api}/` |
| ~~**[GATE:release] MP-LIVE-VERIFY**~~ | **Phase 1 출시 전 필수 — 라이브 검증 게이트** | @qa + @frontend | MP1-K · MP1-L · MP-KL-F3 | ✅ **전건 통과 (2026-06-11)** — ⒜ 계약(C·D) 전건 PASS(d5212d4 검증: overview concentration 키·/cards/flow 404·i18n·5 카드 렌더·drawer detail) ⒝ Briefing 데이터 = MP-LV-D2 수리(`62d4025`) → brief 카드 재게이트 통과 ⒞ Concentration 데이터 = MP-LV-D1 옵션 B 수리(`c6b7aa0`) → SP500_MCAP 스냅샷 생성 + concentration 카드 재게이트 통과(top5 28.29%·HHI 0.0221, /cards/concentration 200·당일·값 정합, /cards/flow 404 유지). **Phase 1 종료 (2026-06-11)** — 게이트 전건 통과 = Phase 1 범위 완료. **출시는 별도 결정**(운영 자율 가동 확인 `MP-OPS-AUTOGEN-CHECK` + `MP-UX-POLISH` 이후 사용자 선언). 상세 DECISIONS "[2026-06-11] Phase 1 종료 선언" | 검증 보고서(curl + DOM 채증) + DECISIONS "[2026-06-11] 게이트 1차 결과"·"[2026-06-11] MP-LV-D1 옵션 B". 부분 재게이트 원칙(수리가 계약 무관 → 해당 카드 스모크만) 적용 |
| MP-KL-F1 | market-pulse-v2 프론트 테스트 신설 — `frontend/__tests__/` 내 0건 → vitest 기반 단위/통합 추가 | @frontend + @qa | MP1-K · MP1-L | **완료 2026-06-11** (`e538e7f`, 원본 `8f1ba79`) | `frontend/__tests__/market-pulse-v2/{fixtures.ts,page.test.tsx}` 12건 (page 로딩/에러/happy + StatusBanner OK숨김·STALE표시 + 5 카드 펼침 라우팅 + drawer 닫기) + `vitest.setup.ts` ResizeObserver 폴리필. vitest 162→174 |
| MP-KL-F2 | cardId `'flow'` → `'concentration'` 행위보존 리네임 (Summary/Detail 파일명 + `CardId` 타입 + `CARD_TITLE` 매핑 + API 계약 영향 범위) | @frontend | MP1-K · MP1-L | **완료 2026-06-11** (`902ec86`, 원본 `70a00c9`) — **게이트 선행 실행됨**(게이트 의존 표기 삭제, 근거 DECISIONS [2026-06-11] MP-KL-F2 게이트 선행) | BE 7곳(VALID_CARDS·enum·dispatch·overview 키·serializer·i18n·test parametrize) + FE 10곳(Flow→Concentration 파일·타입·page·container·hooks·lib·i18n) 원자적. 동명이의 3종(briefing Literal·flow_proxy·news_classifier) 보존. BE 138 / FE 174 / tsc 0 / card 'flow' 잔존 0 |
| MP-KL-F3 | health 위젯 명세 검증 — `MP1-L`의 "health 위젯"이 `StatusBanner` 매핑인지 별도 위젯 필요한지 `page.tsx` 본문 분석 + `OverviewView` health 필드 대조 | @frontend + @backend | MP1-K · MP1-L | **완료 2026-06-11** (`d5289a2`, 원본 `f16efcb`) — **StatusBanner 확정**(별도 위젯 불요) | 판정: 사용자 대면 health = `StatusBanner`(overview `_meta.status` 5값 전수 매핑, 3중 정합). `/health`는 IsAdminUser ops probe로 프론트 미통합 정상. MP-LIVE-VERIFY health 선결 해소. 📎 `docs/market_pulse_v2/mp_kl_f3_health_widget_verification.md` |
| MP-V1-DECISION | v1 `app/market-pulse/page.tsx` (310 lines, useMarketPulse v1 hook, `/api/v1/macro/pulse/`) 거취 결정 — 폐기 / 리다이렉트(v2로) / 보존(레거시) 중 택1. v1 내부 `MarketNewsSection` "TODO: 컴포넌트 미구현" 주석 처리 포함 | orchestrator + @frontend | - | **완료 2026-06-10 (옵션 D 채택)** | 결정: 보존 + Phase 2 흡수 예약. 가중합 D 3.90 vs C 3.55 (마진 0.35, 타이브레이커: 게이트 안전 순서 + Phase 2 정합). 상세 = DECISIONS "[2026-06-10] v1 거시 대시보드 거취 — 옵션 D". 후속 실행 = `MP-V1-ABSORB`(아래) |
| MP-V1-ABSORB | v1 위젯 5종(`FearGreedGauge` · `YieldCurveChart` · `EconomicIndicators` · `GlobalMarketsCard` · `MarketMoversSection`) v2 하위 페이지로 흡수 + `/market-pulse` → `/market-pulse-v2` 리다이렉트 전환 + v1 코드 제거 + 동결된 `MarketNewsSection` TODO 주석 일괄 처리 | @frontend | Phase 2 sub-pages 트랙 착수 | 🕒 **trigger-gated** — Phase 2 sub-pages 착수 전까지 다른 세션에서 먼저 꺼내지 말 것 | 흡수 PR 시리즈 + `/market-pulse` 리다이렉트 + `app/market-pulse/page.tsx` 삭제 + v1 hook(`useMarketPulse`) 정리. 트리거 도래 시 STEP 0로 흡수 대상 위젯 재확인(다른 위젯 추가됐을 가능성) |
| MP-LV-D1 | Concentration FMP `/stable/etf/holdings` 프리미엄 402 결함 — 비중 공급원 결정 | orchestrator + @backend | - | **완료 2026-06-11 (옵션 B 채택, `c6b7aa0`)** | 시총 가중 근사(S&P500 심볼 × FMP quote marketCap → weight=cap/Σcap). `fetchers/weight_source.py` seam 분리(MarketCapWeightSource 기본 / HoldingsWeightSource 휴면 / `ACTIVE_WEIGHT_SOURCE` 1곳 전환). 산식·모델·계약 불변, universe='SP500_MCAP'. 회귀 138→146. 호출 ~500 quote/일. 상세 DECISIONS "[2026-06-11] MP-LV-D1 옵션 B" |
| MP-D1-FMP-UPGRADE | FMP 플랜 업그레이드(holdings 엔드포인트 확보) 시 옵션 A 전환 — `weight_source.ACTIVE_WEIGHT_SOURCE`를 'holdings'로 변경 + CB[fmp_etf] 리셋 + Concentration 카드 스모크. 정확한 float-adjust holdings 비중 복원 + ~500 quote/일 호출 제거 | @backend | FMP 플랜 업그레이드 | 🕒 **trigger-gated** — 플랜 업그레이드 전까지 먼저 꺼내지 말 것 | seam 선택 1곳 변경(holdings 경로 휴면 보존 = 코드 그대로) + CB 리셋 + 스모크 |
| **MP-LV-D2** | Briefing task `ModuleNotFoundError: google.generativeai`(구 SDK) → CB[gemini] OPEN, 생성 이력 0 수리 | @backend | - | **완료 2026-06-11** (`62d4025`) | 신 SDK(`from google import genai`, v1.75.0 기설치) import + contents `parts` 포맷 `[string]→[{text}]` 정정(prompt.py+client.py, requirements 변경 0=case ⒜). 검증: `.apply()` SUCCESS → BriefingLog(OK, gemini-2.5-flash) + pytest 138 + brief 카드 재게이트 통과 |
| MP-UX-POLISH | market-pulse-v2 사용자 대면 표면 개선 — raw 전문어/약어 노출(HHI·top5·top10·dispersion·rotation·AD-line·coverage·momentum) + 단위/맥락 없는 raw 숫자(HHI 0.0211) + 용어 도움 인프라 부재(tooltip/glossary 0) + i18n en 백엔드 라벨 0(FE FALLBACK 의존) | @UI-UX-designer → @frontend | MP-LIVE-VERIFY ✅ 통과 | 🟢 **착수 가능** — 입력(UX 전수조사 2026-06-11) 확보 완료. `MP-I18N-EN`은 UX 세션에서 범위 함께 결정 | ⚠ Phase 1.5 Translation Layer와 범위 중첩 가능 — 착수 전 범위 조정. 근거: 2026-06-11 UX 전수조사 |
| MP-I18N-EN | i18n en 로케일 백엔드 라벨 부재 — `get_labels('en')` 빈 응답 + `_meta.warning='unsupported locale: en'`, FE FALLBACK_LABELS(8키)만 의존. ko 28키 대비 en 백엔드 0 | @backend | - | 🆕 minor (MP-UX-POLISH 세션에서 범위 함께 결정) | `apps/market_pulse/i18n/labels.py` EN_LABELS 추가 또는 의도적 ko-only 명문화 |
| MP-OPS-RESTART | 게이트 후 운영 정합 복구 (병진 수동) — 메인 디렉터리 `main` 복귀 + `git pull --ff-only`(70eb090↑ 정착) + 구 브랜치 `monorepo/sess-mp-kl-f1f3` `-D` + 운영 celery 재기동 + `setup_marketpulse_beat` 재실행(Bug #28 절차) | 병진(수동) | - | 🔧 **병진 수동** | 메인 디렉터리 main == origin/main + 운영 worker/beat가 최신 코드(weight_source 포함)로 가동 |
| MP-OPS-AUTOGEN-CHECK | 재기동 후 **다음 영업일** 5종 스냅샷(Regime/Breadth/Sector/Concentration/Briefing) beat **자율 생성** 확인 — 이번 게이트는 수동 트리거 검증이었으므로 자율 가동은 별도. ⚠ Briefing은 **LLM 일 1회 과금 시작점** | @infra + @qa | MP-OPS-RESTART | 🆕 신규 (출시 선행 조건) | 익영업일 5종 snapshot 당일 row + beat last_run 정상 + Concentration=SP500_MCAP 자율 생성 |
| MP-CONC-FREQ-TUNE | 시총 근사 Concentration task ~500 FMP quote/일 — 타 task(EOD/financials/movers) 합산 일 10k 한도 압박 시 주간 빈도 검토 | @infra | - | 🆕 저우선 | beat 스케줄 조정 또는 현행 유지 결정 |

---

## 보류 (On Hold)

| ID | Task | Agent | Reason | Resume Condition |
|----|------|-------|--------|-----------------|
| MM-L | Market Movers AWS Lambda 전환 | @infra | 비용 최적화 우선순위 낮음 | 트래픽 증가 시 |
| GA-1 | Graph Analysis REST API + Frontend | @backend + @frontend | 모델/서비스만 완료 | Chain Sight 안정화 후 |
| SR (트랙) | 서비스 리모델링 — Dashboard / Chain Sight / Portfolio 3탭 전환 (옛 SR-1~4) | orchestrator + @backend + @frontend + @qa | 미시작 계획서. 44일 정체(2026-04-14~). 브랜치 `data_structure_remodeling_V1` 부재. 재개 시 현 시스템(Slice 14~17) 기준 재설계 필요 | 사용자 명시 재개 신호 + 현 코드 기준 설계 재검증. 설계 사고는 `docs/stock_vis_service_remodeling/` 보존 |

---

## [보류·DORMANT] STRUCT-CLEANUP — 초기 배포 버전 확정 후 구조 정리

- **상태**: 보류(trigger-gated). 재개 트리거 = **(a) 앱 초기 배포 버전 확정**, OR **(b) 실제 경계 충돌 발생**.
  - ⚠ 명확화(2026-06-11): "(a) 초기 배포 버전 확정" = **출시 선언 시점**을 가리킴. **Phase 1 종료(2026-06-11)로는 미발동** — Phase 1 종료 ≠ 출시. 근거 DECISIONS "[2026-06-11] Phase 1 종료 선언".
- **트리거 전까지**: 세션에서 먼저 꺼내지 않음. (단, 실제 충돌이 생기면 즉시 꺼낼 것)
- **항목**:
  - **intraday(regime/anomaly) → dashboard 도메인 이동.** [STEP 0 완료, **D1 = 보류**, 2026-06-06]
    - 진실의 소스: `DECISIONS.md "D1 — intraday(regime/anomaly) 거취 (2026-06-06)"`.
    - 재개 시 권장: **시나리오 C(포트+레지스트리, BOUNDARY-3 패턴 재활용)** + 모델은 SeparateDatabaseAndState 수동 마이그레이션(자동 makemigrations 금지 — DROP+CREATE = prod 데이터 손실).
    - 재개 시 선결 결정: D1~D5 (dashboard 정의 재정의, anomaly 거시 결합 해소 방향, market_pulse overview 화면 분할 등).
    - dashboard 타 프로젝트 소유 → 양 세션 직렬화(SESSION_CONTRACT.C.3) 필요.
  - *(추가)* 초기 배포 버전 확정 시 함께 정리할 구조 항목들 — 확정 시점에 채움.
- **NT-7과의 관계**: 본 보류에 흡수되지 않음. **NT-7 운영 안정화(Beat 재동기화 + 좀비 워커 정리)는 별도 실행 세션에서 즉시 진행** — 구조 이동과 무관한 운영 트랙.

---

## 하네스 구조 개선 (HARN)

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|-----------------|
| HARN-1 | 하네스 4문서(DECISIONS/PROGRESS/TASKQUEUE/common-bugs)의 **append 충돌 구조적 재발** — `.gitattributes merge=union` 적용 또는 세션별 로그 분리 검토 (별도 결정 사안) | orchestrator | - | **backlog** | 2026-06-12 MAIN-SYNC 머지에서 4문서 전건 충돌 재발(양쪽 append 위치 겹침, 수동 해소). 동반: common-bugs **#33 중복**(좀비 Beat ↔ fetch baseline, origin 비고가 예견) 채번 정리 |

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
