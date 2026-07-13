# TASKQUEUE.md — 에이전트 간 오케스트레이션 큐

> 에이전트는 자신에게 할당된 태스크 중 `depends_on`이 모두 `done`인 것만 착수한다.
> 상태: `todo` → `in_progress` → `review` → `verified` → `done` / `blocked`

---

## credit_signals — Phase 1 라이브 종결 + Phase 2/2.5 대기 (2026-07-09)

> 출처: credit_signals Phase 1 실가동(origin/main `a27fd14`, ff land). DECISIONS "credit_signals 신규 앱 (§7.2-B)". 소비처(Dashboard) 착수는 **별도 결정** — 현재 수집·계산·API 백본만 가동, 실전 노출 없음(Heat Score 원칙).

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|-----------------|
| CS-CREDIT-P1 | credit_signals Phase 1 실가동 (FRED 6종 수집·MAD z·strip API·beat) | @infra | - | **🏁 종결 2026-07-10** (fresh 07:30 cron tick GREEN, verify OK, unregistered 0) | origin/main `004ba61`, 원장 4600+행, beat 2종 enabled |
| CS-CREDIT-P2 | Phase 2: FMP HYG/LQD ETF flow + 차환 절벽(refinancing cliff) 지표 | @backend | 별도 결정 | **대기(착수 미정)** | - |
| CS-CREDIT-P2.5 | Phase 2.5: SEC 424B2/FWP 발행 신호 파이프라인 | @backend | 별도 결정 | **대기(착수 미정)** | - |
| CS-CREDIT-CONSUME | Dashboard 프론트에 크레딧 신호 스트립 노출 (소비 시작) | @frontend | 별도 결정 | **🏁 종결 2026-07-11** (MacroStrip 라이브 렌더, gray5+yellow1) | `MacroStrip`+`GradeChip`, origin/main `50ec128` |
| CS-CREDIT-MEANING | 의미 2층: 헤드라인(규칙 자동문장) + 하단 리드아웃(정의·상태·밴드) | @frontend | - | **🏁 종결 2026-07-13** (628 GREEN, 라이브 렌더) | `lib/credit/creditMeaning.ts` |
| CS-CREDIT-CAPTION-FIX | 리드아웃 밴드를 백엔드 grading 규칙에서 도출(신호별, signed z·orange 무상한·red 절대레벨) | @frontend | - | **🏁 종결 2026-07-13** (632 GREEN, 라이브 렌더) | `lib/credit/creditGrading.ts` (백엔드 무변경) |
| CS-CREDIT-INFOPANEL | ⓘ 확장 패널 — **TH 밴드 대시보드 합류 시 재검토** (이번 범위 제외) | @frontend | TH 밴드 합류 | **대기(범위 제외)** | - |
| OPS-API-TREE-SYNC | `worker_sync.sh`에 daphne api 트리(`sv-api-runtime`) 포함 + --dry-run + 단계간 health 체크 | @infra | - | **🏁 종결 2026-07-10** | api 트리 포함=`803e9a9`(DAPHNE-BUILD)·자기가드=`942a991`(기해소) + --dry-run/health 체크=`3e774c3`. real run 검증: 3트리 동기화·worker ping·daphne 401·strip 200·기존 서비스 무영향 |

> **배포 절차 (재발 방지)**: credit_signals도 #28 계열 — 신규 task는 ① worktree/api/web/worker 트리 origin/main 동기화(`worker_sync.sh` = worker+web만, **daphne api 트리 `sv-api-runtime`은 별도 수동 sync 필요**) → ② worker+beat+daphne 재시작 → ③ runtime `.env`(Desktop 심링크)에 `CREDIT_SIGNALS_ENABLED=true` → ④ `register_credit_beats` + `PeriodicTask enabled=True`. **worker_sync.sh가 sv-api-runtime 미포함**은 부채(DAPHNE-BUILD 후속) — API 라우트 배포 시 수동 sync 필수.

---

## Theme Heat runtime 배포 — 오늘 배포 포기·C8 1주 연기 (2026-07-10)

> 출처: credit_signals 종결 관찰(TH beat 2종 unregistered 에러). A-0 실측: TH 코드는 `sv-theme-heat`(branch `monorepo/sess-cs-theme-heat`, 26커밋 미머지 WIP)에만 존재, origin/main·runtime worker에 없음. 경로②-머지불가 판정.

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|-----------------|
| TH-RUNTIME-DEPLOY | TH 트랙(sess-cs-theme-heat) 정식 머지 → worker_sync + 재기동 → TH beat 3종 재활성화(C8 EstimateSnapshot 포함) | @infra (TH 소유 세션) | TH 트랙 클린 체크포인트 머지 | **blocked (오늘 배포 포기, 미머지 WIP)** | beat 3종 현재 `enabled=False` |
| TH-BEAT-REENABLE | UNREGISTERED 3 beat(collect-theme-filings·theme-heat-daily·snapshot-analyst-estimates) 재활성화 | @infra | TH-RUNTIME-DEPLOY | **대기** | `PeriodicTask enabled=True` |

> **오늘 조치(완료)**: UNREGISTERED 3 beat `enabled=False`(에러 플러드 + 깨진 C8 발화 차단). 정상 배포 beat(heat-score-daily·seed-snapshot-cleanup) 무접촉. **C8 첫 EstimateSnapshot(금 16:30 ET) 1주+ 연기** — 시한 때문에 미머지 26커밋 강행 머지 금지(최악). 재개는 TH 트랙 소유자/디렉터가 클린 머지 후.

## 🔴 [P0] chainsight-pair-aggregation beat DB 등록 (버그 #28)

> 출처: RelationPairSnapshot 적립 작업(2026-06-29, 브랜치 `monorepo/sess-cs-pair-relevance`). DECISIONS "RelationPairSnapshot 쌍 relevance 적립 [해자]".

- **증상**: dict 정의 beat(`config/celery.py` `chainsight-pair-aggregation`)가 DatabaseScheduler에서 무시됨 → prod에서 일간 집계 미실행(침묵 실패).
- **영향**: RelationPairSnapshot이 prod에서 적립 안 됨 = **해자 궤적이 안 쌓임**(이 작업 전체의 목적 무력화). GREEN인데 prod 침묵이라 "왜 스냅샷이 안 쌓이지?"로 몇 주 뒤 헤맴.
- **조치 (완료, `bdba71c`)**: B안 — `register_chainsight_beats` BEATS에 pair 엔트리 추가(timezone/day_of_week optional 키 additive 확장). task=`apps.chain_sight.tasks.relation_tasks.aggregate_relation_pairs_task`, **America/New_York 11:30 매일**(confidence 11:00 ET 직후, DST 자동). A안=migration 철회(CI 오염·repo 수동-register 표준 충돌).
- **⚠ 타임존 정정**: 조치 초안의 "11:30 EST"는 부정확 → 실제 celery TZ = **America/New_York(ET, DST 자동)**. confidence도 동일 ET라 순서 보장.
- **Gate 1 (통과, 이번 세션)**: 등록 확인(1행)·import resolve·DatabaseScheduler 스케줄 로드(ModelEntry `30 11 매일 ET`)·idempotent(재실행 updated·중복0·기존 3개 UTC/평일 불변).
- **🔴 migrate 누락 발견 (2026-07-01 실측)**: 마이그레이션 0014가 **dev/prod DB에 미적용**이었음(`showmigrations` `[ ] 0014`). 테스트는 별도 테스트 DB(--reuse-db)에서 돌아 GREEN이었으나 **운영 DB엔 `chainsight_relation_pair_snapshot` 테이블 자체가 없었다**. → beat가 돌아도 task가 `ProgrammingError: relation does not exist`로 crash = **register만으로는 부족, `migrate`가 배포 선행 필수**(claude.ai 체크리스트가 놓친 단계). dev는 `migrate chainsight 0014` 적용 완료.
- **Gate 2 파이프라인 (통과, 2026-07-01 수동 실행 증명)**: migrate 후 `aggregate_relation_pairs_task.apply()` → `{'pairs': 9562, 'created': 9562}` 성공. **period=`2026-07-01` 단일**(중복 주간 행 0) → **드리프트 ⒜는 순수 표기 문제로 확정**(period 로직 정상, 매일 캐이던스 OK). opp 상위 = 순수 truth 쌍(SNDK/WDC opp=0.722). 남은 것 = **beat 자율 틱**(스케줄러가 11:30 ET에 자동 호출)만 익일 로그로 관찰.
- **⚠ 배포 절차(B안 약점 — 순서 필수)**: 배포마다 ① `python manage.py migrate` (0014 — 테이블 선행) → ② `python manage.py register_chainsight_beats` (beat 등록) → ③ 검증. migrate 빠지면 register돼도 task crash(더 깊은 침묵). 배포 체크리스트 영구 등재.
- **드리프트 (목록만, 이번 PR에서 수리 X)**: ⒜ `update_relation_confidence` docstring "주 1회 일요일" vs 실제 매일 11:00 ET — **2026-07-01 실측으로 순수 표기 문제 확정**(당일 단일 period, 로직 정상). ⒝ beat 패턴 혼재(relation_tasks=full-path+ET vs register 기존 3개=별칭+UTC).
- **관찰(PR 밖)**: 11:00→11:30 30분 갭이 confidence 완료를 보장하는지 — 갱신 소요시간 로그 확인 후 갭 재검토.
- **ops 폐기 기록 (재발 방지, 2026-07-02)**: "worker/beat launchd KeepAlive 감독 신규 설치" PR은 **폐기**. STEP 0 실측 = 기존 `com.stockvis.celery-worker`·`celery-beat` 둘 다 이미 `KeepAlive=true`+`RunAtLoad`+`ThrottleInterval`, worker-neo4j·watchdog까지 존재 → 신규는 중복 + **beat 2개 = 스케줄 2배 발화(능동 오작동)**. 07-02 crash 원인은 KeepAlive 부재 아닌 코드 리로드 누락(해법=`kickstart -k`). 향후 "감독 추가" 논의는 이 실측표부터 확인. 대신 관찰가능성만 보강 = `verify_pair_aggregation.py` C항목(직전 11:30 ET 틱 succeeded 부재 시 ALERT — upsert+updated_at 부재라 로그가 유일 증거).

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|-----------------|
| CS-PAIR-BEAT | chainsight-pair-aggregation PeriodicTask DB 등록 (+ migrate 0014 선행) | @infra | - | **Gate1+파이프라인 done / beat 자율틱 익일** | `register_chainsight_beats` (머지 `bdba71c`), dev migrate 완료 |
| CS-PAIR-DEPLOY | prod 배포: migrate 0014 → register_chainsight_beats → 검증 (아래 체크리스트) | @infra | 머지·배포 | todo | 배포 체크리스트 |

### [배포] Chain Sight #28 beat — 순서 필수 (건너뛰면 prod 침묵 실패)

> ⚠️ 이 단계를 건너뛰면 코드가 머지돼도 prod는 RelationPairSnapshot 0으로 침묵한다(등록·테이블은 "코드"가 아니라 "배포 행위"로만 반영됨). migrate→register 순서 준수.

1. [ ] **migrate (테이블 선행)**: `python manage.py migrate chainsight 0014` — 없으면 task가 `relation does not exist`로 crash.
2. [ ] **beat 등록**: `python manage.py register_chainsight_beats` (1회).
3. [ ] **🔴 beat + worker 둘 다 재시작**: `launchctl kickstart -k gui/$(id -u)/com.stockvis.celery-beat` **및** `...celery-worker`(+`worker-neo4j`). **worker 재시작을 빠뜨리면** beat는 발화해도 worker가 신규 task를 모름 → `Received unregistered task ... KeyError` crash(2026-07-02 dev 실측). beat만 재시작하면 안 됨.
4. [ ] **즉시 검증**: `celery -A config inspect registered | grep aggregate_relation_pairs`(등록 확인) + `PeriodicTask...filter(name="chainsight-pair-aggregation")` 1행·enabled·`11:30 America/New_York`.
5. [ ] **익일 검증(진짜 GREEN)**: 다음 11:30 ET 경과 후 ⓐ worker 로그 `aggregate_relation_pairs succeeded`(unregistered 아님) + ⓑ 당일 `period` 행이 **단일 period·count 정상(중복 없음)**.
   > **[v2 멱등 성격 정정]** `RelationPairSnapshot`은 unique `(canonical_a, canonical_b, period)` = **upsert형**이고 **`updated_at` 필드 없음**(created_at만). 따라서 같은 period 재실행은 **count·타임스탬프 모두 불변** → **발화 증거는 ⓐ worker 로그가 유일**(count "안 늘어남"을 실패로 오판 금지 = 위음성 차단). ⓑ count는 **중복(≈2배=멱등 위반) 감지용**이지 발화 증거 아님. verify_pair_aggregation.py가 A(로그)+B(count) 병행으로 이미 커버.
6. [ ] **근본 수리(권장·별도 태스크)**: 위 migrate+register+재시작을 배포 스크립트/릴리스 훅에 넣어 수동 의존 제거 — B안의 "사람이 까먹음" 함정(#28이 한 층 위로 옮겨간 것)의 완결.

---

## Chain Sight M2 v1.1 — theme_tags → EventGroup reader 전환 (Phase 1)

> 보드를 섹터형 theme_tags → 코어-위성 EventGroup + 정합 leadership으로 전환. 2026-06-27 **Phase 1 완료(go-live)**. 결정: DECISIONS "Chain Sight 보드 EventGroup 전환 (2026-06-27)".

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|-----------------|
| CS-EG1 | EventGroup 리더 어댑터 (kept만·n3·core/satellite) | @backend | - | **done** | `event_group_reader.py` (머지 `d787499`) |
| CS-EG2 | C 비대칭 leadership 재컴퓨트 (코어 LOO/위성 코어평균) + L3 오라클 | @backend | CS-EG1 | **done** | `leadership_eventgroup.py` + migration 0013 (머지 `269d1eb`) + prod eg 114행 |
| CS-EG3 | 보드 리스트+드릴다운 플래그 배선 (`CHAINSIGHT_GROUP_SOURCE` OFF 기본) | @backend/@frontend | CS-EG2 | **done** | `flags.py`·attach_leadership_eg·EventBoard.tsx (머지 `202a840`) |
| CS-EG4 | C 컴퓨트 daily beat (22:15 UTC) + 캐시 | @infra | CS-EG3 | **done** | `register_chainsight_beats` + `chainsight-event-group-leadership-daily` 등록·worker 재기동 |
| CS-EG5 | go-live: 플래그 ON + 서버 재시작 = Phase 1 완료 | orchestrator | CS-EG4 | **done** | `.env event_group` + daphne/celery 재시작, beat `.delay()` 검증 |
| CS-EG6 | 옛 theme_tags leadership/그룹핑 디프리케이션 (파괴적, 한참 뒤) | @backend | CS-EG5 안정화 | todo | — (전환 안정 후) |

### Chain Sight Phase 2 백로그 (Phase 1 라이브 후, 2026-06-27 등록)

> 출처: Phase 1 마무리 정리 세션. LLM 묶음은 BOUNDARY-LLM 트랙 의존(메모리 `project_boundary_llm_track`).

| ID | Task | Agent | Depends On | Status | 비고 |
|----|------|-------|------------|--------|------|
| CS-P2-LLM | LLM 의존 묶음 (LLM 레이어 통합 / 10-K 관계추출 / FRED 해석) | @rag-llm/@backend | **BOUNDARY-LLM 슬라이스① land** | todo | shared LLM 래퍼 통합 선행 필요 |
| CS-M3 | Path Watchlist (코어-위성 경로 추적) | @backend/@frontend | 독립 | todo | EventGroup 코어-위성 위 경로 추적 |
| CS-P2-GRAPH | 그래프 화면 정제 (EventGroup 시각화) | @frontend | 독립 | todo | redesign v1 그래프 캔버스 위 EventGroup 반영 |
| CS-P2-13F | 13F 버그 + CUSIP 매핑 수정 | @backend | 독립 | todo | 위성 cohold_institutions 정확도 |

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
| CS-RD2 | 관심도 M1 엔진 (모델·배치·API, Phase 2) | @backend | CS-RD1 | **done** (StockAttentionScore+migration0009 / attention_service(M1+ADV_FLOOR $45.8M 유동성가드) / Celery task / API 2개(events·events/<theme>/stocks) / 테스트 20. 670→634계산 0.16s, score 15.6~99.9, low_liq 34, 멱등Δ0, api/views.py diff0) | v2 지시서 `Cs redesign 02 attention m1 backend v2.md` |
| CS-RD3 | 이벤트 보드·관심도 랭킹 프론트 (Phase 3–4) | @frontend | CS-RD2 | **done** (2026-06-23, `8c276b5`) — QA 4슬라이스 + Slice 2-B(바 정규화 전역0~100) + ⓑ URL 인코딩(common-bugs #38) + ⓐ 소규모 그룹 노출+저신뢰 표식. vitest 387/0·pytest 74/0, 라이브 검증 완료(daphne 재기동) | `docs/chain_sight/redesign(26.06)/Cs redesign 03 event board frontend .md` |
| CS-DATA-HYGIENE | 기존 0행 10종목·<20일 8종목 가격 공백 원인 점검 (z-score 불가 → 관심도서 해당일 제외 중) | @backend | - | **backlog** | CS-RD2 STEP0 발견. 상폐 8종(CTRA·DAY·FI·HOLX·IPG·K·MMC·WBA) 유니버스 정리 포함 |
| CS-BACKFILL | DailyPrice 120일 백필 — `/full` days=200 멱등. ≥120일 7→659/670 | @backend | - | **done** (666 성공·멱등·M1 scorable 634→659. 미달 11=IPO1/상폐8/프리미엄2) | DB 데이터(코드변경 0) |
| CS-M2 | 주도주 지표 엔진 v1 — 종목레벨 4지표(T2/T3/theme_beta/capture) | @backend | CS-RD2·CS-BACKFILL | **done** (StockLeadershipScore+migration0010 적용 / 640행 산출 / beat 2종 등록(leadership+M1 attention 부채) / **옵션Y: T2주·T3보조, ρ실측0.84**) | DECISIONS "CS-M2 (2026-06-16)" |
| CS-M2-DISPLAY | RD3 serializer/프론트에 옵션Y 노출 적용 — T2(trend_quality) 주, theme_beta·capture_spread 주, T3(theme_alpha) 보조 강등. window 파라미터 노출 | @frontend | CS-M2·CS-RD3 | **ready** | CS-M2 6지표 serializer 라이브 |
| CS-M2-V11 | 테마 레벨 지표(응집도·확산도·선행후행) — 테마 재정의(섹터≠테마) 후. O(n²) 상관판 | @backend | CS-M2 | **backlog** (테마 재정의 선행) | STEP0: 현 테마=GICS 섹터 중복 |
| MAIN-SYNC-FIX | 나이틀리 자동화가 로컬 main에 직접 commit(push 없이) → origin과 분기 재발(CS-M2-MERGE에서 ff 거부·잘못된 머지 사고). 자동화가 별도 브랜치 사용 or commit 후 즉시 push하도록 수정 | @infra | - | **자동화 부분 done 2026-06-18** (hook hardening 잔여) | **활성 스크립트 `run_tier3_audits.sh`를 dated 브랜치(`monorepo/nightly-<date>`) 격리로 수정 — 메인 트리 main 무오염 입증**(6/2 결정이 비활성 `nightly_v3.sh`에 오적용됐던 것 정정). DECISIONS "MAIN-SYNC-FIX 적용 (2026-06-18)". ⚠️launchd 재가동(`launchctl load`)은 사용자 승인 대기(현재 unload). **잔여 = hook 근본 hardening**(`scripts/hooks`+`core.hooksPath`, HARNESS-KB S3 .git/hooks 새 클론 미적용 한계) |
| NIGHTLY-BRANCH-GC | dated 나이틀리 브랜치(`monorepo/nightly-<YYYYMMDD>`) 누적 정리 — 매일 신규 브랜치라 시간이 지나면 local·origin에 쌓임. 보존기간/머지정책(리포트를 main에 주기 머지할지 vs N일 후 삭제) 결정 + GC 스크립트 or 주기 작업 | @infra | MAIN-SYNC-FIX | **backlog** | MAIN-SYNC-FIX 적용(2026-06-18)에서 파생. 격리는 됐으나 GC 미정 |
| KB-NIGHTLY-LINK | `docs/nightly_auto_system/reports` 고립 해소 — 나이틀리 감사 리포트가 KB 검색·1차소스로 흘러드는 소비 고리 설계(현재 생성만 되고 KB로 안 옴). 소비 고리 설계 필요 → **HARNESS-KB 범위 밖, 등록만** | @qa/@infra | - | **backlog** (범위 밖) | HARNESS-KB S4-3에서 등록. KB-CENSUS 'nightly 고립' 항목 |
| CS-EXT1 | 외부 API 직접 호출 4곳 → shared FMP 래퍼 경유로 이전 | @backend | - | **backlog** (이번 개편 범위 외 — 등록만) | `insider_tasks.py:38`, `sensitivity_tasks.py:80`, `neo4j_loader.py:132,144` (FMP `requests.get` 직접 호출) |
| CS-COV | 정식 섹터 분류 기반 그룹핑으로 커버리지 확장 검토 (ETF 비중 1% 미만 잔여 편입) | @backend | - | **backlog** | NarrativeTag(LLM) 태깅 병합 + w<1.0 잔여 종목 편입 검토 |
| CS-UNIV | 유니버스 확장 범위 분석 — 디렉터 지시서 발행됨, 별도 read-only 세션에서 실행. 확장 자체는 확정, tier 결정은 측정 후 디렉터 세션 | @backend | - | **active** (측정 완료 `9d80cdc`, 디렉터 결정 대기) | `docs/chain_sight/univ_analysis/REPORT.md` — T1 포화/T2 품질우위, 러셀 프록시 차단 |
| CS-EXP | 테마 ETF holdings 확대 + 유니버스 U2 편입 + 백필 (디렉터 지시서) | @backend | CS-RD1·CS-UNIV | **done** (핵심 목표=게이트 통과 달성: STEP0→(c)복구→GATE/SOURCE 측정→LOAD(ETF 추가)→U2SIM→**U2EXEC 편입으로 게이트 X=8 통과 중앙값26**. 잔여 NEO4J/SECTOR/P1·P2는 별도 트랙) | `Cs exp universe expansion.md` + univ_analysis/CS-EXP-*.md 6종 |
| CS-EXP-U2 | **유니버스 편입(U2)** — 테마 ETF holdings의 비SP500 US 종목을 Stock 유니버스에 편입해 그룹 밀도↑ | @backend | CS-EXP | **done** (U2EXEC로 실행 완료) | `CS-EXP-U2SIM.md` / DECISIONS "CS-EXP-U2 결정" |
| CS-EXP-U2EXEC | U2 실행 — 편입 + DailyPrice 백필 + 게이트 재측정 | @backend | CS-EXP-U2 | **done** (135종 편입·백필 0%실패·**게이트 X=8 통과 중앙값26**·유니버스535→670. `CS-EXP-U2EXEC_measurement.md`) | 예측26=실측26 일치 |
| CS-EXP-NEO4J | Neo4j 그래프 편입 — 신규 테마 ETF(XBI/KRE/PAVE) + 편입 135종을 `ETF_THEME_MAP`(load_themes_to_neo4j.py)에 추가해 :Theme/HAS_THEME MERGE | @backend | CS-EXP-U2EXEC | **todo** (ETF_THEME_MAP 코드 편집 — U2EXEC 범위 밖) | `load_themes_to_neo4j.py` ETF_THEME_MAP |
| CS-EXP-SECTOR | 신규 135종 sector/industry 채움 — FMP profile 엔드포인트 동기화(quote는 미반환) | @backend | CS-EXP-U2EXEC | **backlog** | `StockSyncService` profile sync |
| CS-EXP-P1 | generic 파서 확장 — Roundhill/Amplify 다중펀드 통합 CSV(Account=<ticker> 필터 + `StockTicker`/`Weightings` 컬럼) 지원 → HACK·BETZ holdings 적재 | @backend | CS-EXP | **todo** (shared 파서 코드 변경 — CS-EXP 세션 범위 밖) | URL 확보됨(amplifyetfs/roundhill), `etf_csv_downloader.py` `_parse_csv` 확장 |
| CS-EXP-P2 | KWEB Cloudflare 우회 — `download_holdings` httpx가 Cloudflare 403, curl는 200. 우회 수단 + `parser_map` `kraneshares` 키 누락 보정 | @backend | CS-EXP | **todo** (downloader 코드 변경) | URL 확보됨(date-based), `etf_csv_downloader.py` |
| CS-EXP-P3 | `_parse_ark_csv` 버그 수정 — 면책행 `ticker=None` → `str(row.get("ticker") or "").strip()`. 수정 시 ARKK/ARKG를 ark 파서로 복귀 가능 | @backend | CS-EXP | **todo** (파서 버그) | `etf_csv_downloader.py:786` |
| CS-EXP-TAN | TAN(Invesco Solar) holdings 소스 — Invesco 다운로드 엔드포인트 403, 공개 직접 CSV 부재. 대안 소스 탐색 필요 | @backend | CS-EXP | **backlog** (소스 부재) | 대안: 타 제공자 holdings 또는 수동 |

---

## Monitor 허브 재건 (구 Thesis Control — D-MONITOR-REBUILD 2026-07-08)

> 구 thesis 앱 **전량 폐기 후 재건**. 아래 TC-* 는 **폐기 앱 대상이라 무효화** → Monitor 신축 P2~P3로 승계.

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|-----------------|
| MON-P1 | 아카이브 + thesis 앱 철거 | orchestrator | ADR | ✅ 완료 2026-07-08 (9커밋, **main 랜딩 `c80783a`** `--no-ff` B안) |
| MON-P2-S1 | Monitor·Claim 모델 + ScopeResolver(종목) + 테스트 | @backend | MON-P1 | ✅ 완료 2026-07-08 (`f9754c7`, apps/monitor 신설, 10 passed) |
| MON-P2-S2 | MonitorIndicator·IndicatorReading·Snapshot 모델 + `_reuse` 엔진 4종 이식 + 테스트 | @backend | MON-P2-S1 | ✅ 완료 2026-07-08 (`e62760f`, 모델 3+엔진 4, 테스트 37 누적, BE _reuse 소진) |
| MON-P2-S3 | 파이프라인 서비스 + `api/v1/monitor/` REST + 실 DB migrate + 테스트 | @backend | MON-P2-S2 | ✅ 완료 2026-07-09 (`e37a87e`, **P2 완결**, 테스트 50, 실 DB 5테이블 적용) |
| MON-P2-BEAT | Monitor 평가 beat 주기 등록 (EOD 창 18:00~18:35 ET 경합 설계 + DB PeriodicTask #28) | @infra | MON-P2-S3 land | ✅ 완료 2026-07-09 (**origin/main `924ef96`** `--no-ff`, 배포+워커등록 검증). `sync_monitor_beat` 멱등커맨드·`refresh_monitors_task`(가드+재시도)·health 13항목·구 thesis 4beat 회수. DECISIONS `D-MONITOR-BEAT`. 첫 발화=평일 18:45 ET | ADR §결정6 |
| MON-P3-S0 | FE 데이터 레이어 (types·monitorService·useMonitor 훅) | @frontend | MON-P2 land | ✅ 완료 2026-07-09 (`d281813`, 브랜치 `sess-monitor-p3`, 테스트 5·tsc 0) |
| MON-P3-S1 | IA-2 리스트 페이지 (서버측 트리아지 정렬·필터 + 스코프/가설만 칩 + 빈상태 CTA + 카드) + MoonPhase·Arrow 이식 | @frontend+@backend | MON-P3-S0 | ✅ 완료 2026-07-09 (`278f7b6`·`ede1160`, FE 14·BE 13·tsc 0, _reuse MoonPhase/Arrow 소진) |
| MON-P3-S2 | 빌더 4단계 + 지표 카탈로그(BE) + FE `_reuse` 완전 소진 | @frontend+@backend | MON-P3-S1 | ✅ 완료 2026-07-09 (`f908188`·`49a3fbe`, 카탈로그 3종+source_key, 빌더 4단계, _reuse 소멸, BE 17·FE 16·tsc 0) |
| MON-P2-INGEST | 지표 판독 이식 — `source_key`→EODSignal→IndicatorReading (백필 N=120일, 멱등 unique 0004, 수동 커맨드 ingest_readings·refresh_monitors) | @backend | MON-P3 land | ✅ 완료 2026-07-09 (`6458da5`, E2E: AAPL score 0.1698·display 실값, 테스트 68·collect 3668). 다음=**MON-P2-BEAT** |
| MON-P3-DISPLAY-FILL | (선택, 급하지 않음) BE `display`에 `fill_percent` 포함(FE `scoreToFillPercent` 흡수) — 달 채움도 API 단일 소스로 | @backend | - | 🕒 선택 과제 | ADR 재계산 원칙 |
| MON-P3-S3 | 전역 내비 6칸+아바타 + My 서브탭 M-3 (+ 실렌더 스모크 3화면 + 캐시 무효화 fix) | @frontend | MON-P3-S2 | ✅ 완료 2026-07-09 (`4222e7e`·`65975f7`, 스모크 통과, vitest 544·tsc 0). **MON-P3 = P3 완결** → 병합 대기 |
| MON-P3-PAGINATE | (조건부 메모) DRF 페이지네이션 도입 시 → IA-2 **칩 카운트를 서버 집계로 전환**(현재 list 전량 반환 전제라 클라 카운트. 페이지네이션 켜지면 카운트 정확성 깨짐 → count 엔드포인트 or `?facets=` 응답). 트리거 = REST_FRAMEWORK `DEFAULT_PAGINATION_CLASS` 도입 | @frontend+@backend | 🕒 트리거: 페이지네이션 도입 시 | ADR §결정5 |

> **MON-P3 완료 판정(DoD)**: 단위 테스트(FE vitest·BE pytest·tsc 0) **+ dev 서버 실렌더 스모크 3화면**(리스트 IA-2 / 빌더 4단계 / 전역 내비) — auth 세션 하 실제 브라우저 렌더 확인(좌표 아닌 실 렌더, lesson_visual_verify). 스모크 미수행 시 P3 미완결.
>
> **FE 스모크 정식 항목(MON-CLOSE 추가, 2026-07-13)**: 위 3화면 + **① 대화형 빌더로 두 번째 모니터를 실제 생성**(빌더 4단계 관통 → 생성 후 목록에 반영 확인 — 회귀 시 빌더 경로 생존 보장) + ② authed 픽셀: 데이터 보유 모니터 카드의 StateBandSparkline 렌더(색 밴드+선). 빌더 실사용 검증은 owner 세션에서 수행(owner-scoping).
| MON-P4 | 시장/섹터 scope — shared 수집 태스크 신설(EOD 창 경합 명시) | @backend+@infra | MON-P2 | todo | - |
| MON-P5 | 테마 바스켓(편집 UI + EODSignal 내부 집계) | @backend+@frontend | MON-P4 | todo | - |
| MON-P6 | 펀드 scope (ETF만, 공모펀드 보류) | @backend | MON-P5 | todo | - |
| ~~TC-3~6~~ | ~~대화형빌더·지표설정·관제실·알림마감~~ | - | - | ❌ 무효 (폐기 앱) → MON-P3 승계 | - |
| MON-P3-ALERT | 전이 알림·다이제스트·상태밴드 스파크라인 (AlertEvent + 인앱 벨 + 이메일 + FE 스파크라인) | @backend+@frontend+@infra | MON-P2-BEAT land | ✅ 완료 2026-07-09 (land `8433fe1`). **배포 완료 2026-07-13**(FIRSTFIRE Case A green → sv sync + migrate 0005 + env `MONITOR_ALERT_RECIPIENT` + 재기동, ALERTFIRE 첫 알림코드 무인 발화 alerts=0 정상). DECISIONS `D-MONITOR-ALERTCLOSE` | ADR §결정1~4 |
| MON-CLOSE | Monitor 검증 단계 4 DoD 종결 + 부수 정리 5건 + 결정 봉인 | @infra+@frontend | MON-P3-ALERT 배포 | ✅ 완료 2026-07-13 (`monorepo/mon-close`). 4 DoD 완결(authed 픽셀=goid545 세션 스파크라인 렌더)·63fa58cb 삭제·라벨 Thesis→Monitor·T-1 정정 각주·common-bugs #51·빌더 스모크 항목화. OWNERFIX 폐기. DECISIONS `MON-CLOSE` | - |
| MON-VIZ-ROTATIONMAP | 모니터 회전 맵(RRG 동형 2축 분포) — 상태밴드 스파크라인의 후속 시각화 | @frontend+@backend | **착수조건: 활성 모니터 ≥5** | 🕒 예약(조건 미충족) | ⚠ market_pulse 컴포넌트 **직접 import 금지** — shared 승격 vs 재구현은 착수 시 결정(D-MONITOR-ALERTCLOSE 1b) |
| MON-WALLET | Wallet 금융 API(증권사) 연동 — **별도 트랙**(본 프로젝트는 My 서브탭 자리+thesis 접점만) | (미배정) | - | 💤 별도 트랙 | ADR §결정7 |

---

## 테스트 부채 상환 — pytest 선존 실패 120건 (MON-P2-BEAT §0에서 고정, 2026-07-09)

> **출처**: MON-P2-BEAT preflight에서 전체 pytest 베이스라인 실측 → `18 failed / 102 errors = 120건` 선존 확인(전부 `apps/monitor` disjoint, 신규 회귀 아님). **SSOT 스냅샷** = [`docs/harness/pytest_baseline_failures.md`](../docs/harness/pytest_baseline_failures.md). 세션 게이트가 "green" 대신 **"이 베이스라인 대비 델타 0"**으로 판정되도록 고정. 상환 시 SSOT 목록에서 개별 삭제(줄어드는 방향으로만).

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|-----------------|
| DEBT-TEST-BOUNDARY-LLM | `test_news_deep_analyzer`(102e) + `test_csv_url_resolver`(4f) mock을 **shared LLM 래퍼 seam으로 재작성** (옛 `patch('...genai')` → 래퍼 mock). 근본원인=BOUNDARY-LLM 이관으로 직접 genai import 제거, 코드 정상·테스트 stale | @qa+@rag-llm | - | todo | SSOT C1·C2 / BOUNDARY-LLM backlog와 동일건 |
| DEBT-TEST-CHAINSIGHT | `test_attention`(6f, `assert 'SEMICON' in []`) + `test_leadership_api`(7f, `404==200`) + `test_upward_learning`(1f) = 14f. **pristine 체크아웃 재현으로 판정** — 오탐(stale `_dormant`+공유 test DB, lesson_...)이면 격리 픽스처/시드, 진성이면 코드 수정 | @qa+@backend | - | todo | SSOT C3·C4 |

> **판정 원칙**: DEBT-TEST-CHAINSIGHT는 `.claude/worktrees/`의 stale 워크트리·`_dormant` 잔재가 공유 test DB를 오염시킨 오탐일 수 있음(메모리 `lesson_visual_verify`가 아닌 stale-artifact lesson) → **pristine 격리 체크아웃에서만 진위 확정**. DEBT-TEST-BOUNDARY-LLM은 시그니처가 명확(genai attr 부재)해 즉시 착수 가능.

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
| NT-12 | 2026-06-23 | 2026-06-23/대시보드 보고서없음 | ops | `~/stock-vis-nightly/publish_reports.sh` + `run_tier3_audits.sh` 배선(사용자 수동) | **진행** | 인증 A(NT-13) 선결 — 발행 살아도 생성 죽으면 신규 0 | **B-2 발행 단계.** 격리 worktree 리포트 → reader read 경로 단방향 복사. 스크립트 작성 + 6/18·19 backfill(각 12/12, reader 인식 검증 완료) + `.gitignore` 발행본 무시(로컬 커밋). 잔여 = nightly 커밋 phase 다음 1줄 배선(사용자 수동). 📎 DECISIONS "[2026-06-23] B-2 발행본 = 미추적 + gitignore" | 🆕신규 |
| NT-13 | 2026-06-23 | 2026-06-23/tier3 로그 401 | ops | 사용자 수동 (`claude setup-token` + plist `ANTHROPIC_API_KEY`) | **신규(라이브 블로커)** | - | **인증 A.** `run_tier3_audits.sh`의 `claude -p` 호출이 6/20~22 전부 `401 Invalid authentication credentials` → 12 audit 생성 0건. 키체인 OAuth가 launchd 비대화형에서 만료/무효. 처방: 장기 토큰 발급 후 `com.stockvis.nightly.plist` EnvironmentVariables에 `ANTHROPIC_API_KEY` 주입 → unload/load. B-2(NT-12)와 독립. | 🆕신규 |
| NT-14 | 2026-06-23 | NT-12 후속 | ops | 사용자 결정 (선택) | **보류(선택)** | B-2 안정화 후 git 위생 정리 원할 때 | **역사 리포트(≤6/16) 선택 정리.** pre-6/16 리포트가 main에 추적(커밋)된 상태로 잔존 — MAIN-SYNC-FIX 이전 안티패턴 잔재. `git rm --cached docs/nightly_auto_system/reports/<역사경로>`로 untrack 가능(파일 보존). **선택 사항** — 안 해도 기능 무영향(gitignore가 신규만 차단). 사용자 명시 지시 전까지 미실행. | ➡️유지 |
| NT-15 | 2026-06-23 | STEP 0-6 발견 | ops | 사용자 결정 (범위 밖) | **보류** | - | **`monorepo/nightly-reports` 브랜치 처분.** STEP 0 실측 = 집계 타깃 아님(feature 커밋 최신, reports 16일까지뿐 = stale 일반 브랜치). B-2 미사용 확정. 브랜치 자체 삭제/정리는 본 트랙 범위 밖 — 파괴적 작업이라 후보만 등록. | 🆕신규 |
| NT-16 | 2026-06-23 | investigate 부산물 | ops | `agent_reports.py`/`daily_report.py` + 인프라 (NT-11c 연계) | **신규** | - | **이메일 배달 메커니즘 + neo4j down 건강 점검.** ① 대시보드 메일 발송부가 LaunchAgents·daily_report.py grep에 안 잡힘 → 배달 경로 불명확, 확인 필요. ② `neo4j_alive False`(launchd에 neo4j 잡 0) — 실제 down. ③ TL;DR `beat=DOWN` vs 상세 `celery_beat_alive True` 키 표기 불일치(`collect_system_health`). neo4j 건강은 NT-11c와 묶어 처리 권장. | 🆕신규 |
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
| TRASH-11 | **worktree 2건 거취 — DEAD 확정·remove 완료** (TR-7/8 정정). 기존 ALIVE 판정은 **stale 로컬 main 기준 오판**이었음. TR-8 STEP1: unique 커밋 5건(f483634/d4a9690/ce0be51/0b8399a/ef9d064) **전건 origin/main(d5212d4) REACHABLE = DEAD**. `sess-mgmt-phase1-catalog`·`sess-mp-phase1-cleanup` 디렉토리 소멸 + worktree registry 제거 완료(세션 간 외부 선제거, prune 정합). **잔여 결정**: 브랜치 2건 삭제 — 커밋이 origin/main 도달이나 **로컬 main 미도달**이라 `-d` 거부 예상 → 사용자 수동 `-D` 또는 `pull` 후 `-d`. + `sess-mp-kl-f1f3` 머지 시 `82afddb`(TASKQUEUE 9건) 중복은 main `cb5473e`와 동일 → 충돌 시 main 채택. **+ `monorepo/sess-mgmt-llm-decision`(cbc6041, BOUNDARY-LLM 기록): origin push됨·미머지 → consolidation 시 main 머지 후 브랜치 삭제 대상.** **push/pull 통합 결정과 묶음**. | orchestrator | - | todo | 브랜치 삭제 + push/pull 통합 |
## market_pulse v2 Phase 2 로드맵 (2026-06-23 진입 순서 확정)

> 근거: `DECISIONS.md` "[2026-06-23] Phase 2 진입 순서"·"Alerts 트랙 경계 = O3 하이브리드". Phase 1 종료(코어 대시보드+Translation+화면게이트 조건부통과) 후 진입. 순서 = Analog → Alerts → sub-pages → 데이터게이트(FedWatch/GEX) → cross-surface(게이트). P2 roadmap recon(2026-06-23, [E]~[H]) 기반.

| ID | Track | 우선 | Agent | Status | 근거/게이트 |
|----|-------|------|-------|--------|------------|
| MP2-ANALOG | historical regime matching(유추 분석) — 현재 regime 입력 vs 과거 유사 국면 매칭 + **MOVE 동봉**. **채택 설계**(un-dorm 시) = 입력벡터 z-정규화 최근접(라벨 매칭 아님, D-ANALOG-GATE) | **#1** | @backend | 🟢 **UN-DORMANT (2026-07-10, B1-S2-FIRE)** — B-1 소급 백필 완료로 트리거 (a)(b) 동시 충족: 완전벡터 **683행**(구 22)·비-LATE_BULL 475일(TRANSITION469+CRISIS6)·LATE_BULL 228 = 다양성 게이트 개방. **analog 코드 착수 가능**. 앵커 설계 = 입력벡터 z-정규화 최근접(라벨 매칭 아님, D-ANALOG-GATE) | **#1** | @backend | 🟢 **착수 가능** — 게이트 개방(2026-07-10). 소급 벡터 = 라이브와 동일 문법(as_of 매개변수화, D-B1-SYNTH)이라 최근접 비교 유효. vintage 규약 = 전 구간 현재 개정판(D-B1-VINTAGE) |
| MP2-ALERTS | 능동 알림. 알림 코어 = `packages/shared/alerting` 신설(D-ALERTS-BOUNDARY-R1), 3단 파이프라인(D-ALERTS-ARCH), 이메일(D-ALERTS-CHANNEL). **승계 게이트 해소 = D-ALERTS-GATE**(serverless 무접촉 격리). S0·S1 land | **#2** | @infra+@backend | ✅ **S0 마감 + S1 done(미머지)** | 다음 슬라이스 후보 = 채널 추가(슬랙 등, delivery port 구현체만) / 트리거 확장(anomaly·dashboard) |
| MP2-ALERTS-S1 | Slice 1(D-ALERTS-RENDER) = regime 알림 본문 **풀 리포트화**(전환 요약·델타·anomaly 활성·섹터 상위/하위). **단일 경로**=판단 화면과 동일 `overview._build_payload()` 소비(재계산 0). **폴백**=풀 렌더 실패 시 디스패처가 S0 최소 본문으로 대체(발송 무실패, `AlertDispatchLog.error` RENDER_FALLBACK 접두로 식별, status=SENT). registry에 fallback 슬롯 additive. 제목 불변·LLM 0·shared→apps 0·마이그레이션 0 | @backend | ✅ **done + 실메일 검증 완료 (2026-07-08 장부 마감)** — pytest 신규7/alerting8·경계3·api80 green·mig0. FE 0. **풀 리포트 실수신 확인**(status=sent·폴백 아님, jinie545@gmail.com) | 검증 완료 → 잔여 없음 |
| MP2-ALERTS-S0 | Slice 0 = regime 전환 트리거 → 3단 파이프라인 → 이메일 1통 + dedup. shared/alerting 신설(AlertSubscription·AlertDispatchLog·registry·dispatcher·EmailProvider) + market_pulse 훅·렌더러 + seed 커맨드. AST 경계 통과, migration 0001 **생성만** | @infra+@backend | ✅ **실적용 완료 (3eb06a7) — 장부 마감 2026-07-06**: migrate·worker_sync·seed·shell 수동 트리거·실발신 전 6단 완료. **실메일 일반 수신함 정상 도착 확정**(스팸 아님, 발신 신뢰도 이슈 없음) + `AlertDispatchLog` status=sent 1행. 멱등 close(이후 재마감 스킵). | 병진 수동 런북(6단, 2026-07-05 확정 — 완료 기록): **① `python manage.py migrate alerting`**(prod DB 테이블 2개 — 워커 재기동 전 선행: 재기동 창에서 실전환 시 테이블 부재 회피) → **② `bash scripts/worker_sync.sh`**(B′ 배포+워커 재기동 — 신규 task·regime.py 수정·신규 앱 로드 필수, 근거 `lesson_celery_task_registration`. beat 무변경이나 스크립트가 함께 kickstart=무해) → **③ `python manage.py seed_alert_subscription --email <주소>`**(멱등) → **④ shell 수동 트리거** `fire_regime_transition_alert(date="2026-07-05",…)`(직접 동기호출 — 워커 무관·이메일 경로 종단 검증, 07-05 과거날짜라 실전환 dedup 충돌 0) → **⑤ 실메일 확인**(제목·본문 링크·소요·스팸함 + `AlertDispatchLog` status=sent 1행) → **⑥ 첫 메일 "스팸 아님" 처리**. ⚠ **배포 전 prod `FRONTEND_BASE_URL` 도메인 설정 확인**(미설정 시 메일 링크=localhost:3000). **migrate 전까지 prod 미반영** |
| SCREENER-ALERT-CONVERGE | (휴면) serverless `ScreenerAlert`/`AlertHistory`(사용자 알림 프레임워크, delivery 미구현) → shared/alerting 코어로 수렴 여부. D-ALERTS-GATE로 현재 **무접촉 격리(KEEP 레거시)** 확정. 전수조사 CUT 판정 없음 → 소멸 예정 아님 | @backend | 🕒 **휴면** | 트리거 = screener 알림 **실활성화** 결정 시(그때 shared 코어 재사용 vs 독립 유지 재평가). 현 시점 착수 금지 |
| MP2-SECTOR-CD | 섹터 판단 화면(CD 4-상태). 순차 연속 슬라이스(D-TREND-CD-SEQ). rel_strength×momentum_5d 사분면 분류(신규 파생 0, baseline=0.0). RRG 회전 맵 = 서브스크린(D-SECTOR-NAV, Slice 3) | **#2.5** | @backend+@frontend | ✅ **트랙 종결 (2026-07-09)** — S1 `32c2390`·S2 `20d2734`·S3 land | 판정 로직 = payload builder 단독·FE 재분류 0 전건 준수. **차순위 = B-1(ANALOG·TREND S4 이중 언락 키)** |
| MP2-SECTOR-CD-S1 | Slice 1 = cd_state additive(payload) + 판단 카드(세그먼트 토글 [판단\|궤적], 디폴트=판단). `classify_cd_state` 순수함수 + `CD_REL_STRENGTH_BASELINE`/`CD_MOMENTUM_BASELINE`=0.0 상수 + FE CD_STANCE 정적 5문구(LLM 0) + 2×2 미니맵 + 유보 처리 | @backend+@frontend | ✅ **done (land `32c2390`)** | additive-only, 회전 맵 어포던스 미포함(Slice 3) |
| MP2-SECTOR-CD-S2 | Slice 2 = 모멘텀 시계열. sector_history[] per-date momentum_5d additive 노출(저장값) + `cd_momentum_baseline` 메타 + FE 모멘텀 모드(디폴트=순위 유지)+판정선 hline(서빙값)+국면 스트립 레인(D-SECTOR-MOM-LANE 변형2, `regime_history_30d` 소비) | @backend+@frontend | ✅ **done (land `20d2734`)** | momentum=저장 노출(재계산0, STEP 0-2: 528행/48일/NULL0). 변형2 확정 |
| CD-FLAP-WATCH | (측정 완료) cd_state 일간 반전 빈도 소급 측정(S3 STEP 0-2, 43일 집계 2026-05-19~07-09, 초기5일 제외). **결과: 총 289반전/11섹터/43일, 일평균 반전 섹터 6.72, 섹터당 일평균 반전율 0.611**(XLI 30 최다~XLV 22 최소). 판정선 근접 상습 섹터 없음(근접 최대 9일=21% → 플래핑 원인은 근접-호버 아닌 실 부호 변화). rel_strength=1일 차분 특성 | @backend | 📊 **측정 완료 — 히스테리시스 여부 디렉터 결정 대기** | 반전율 0.611은 높음(거의 매일 절반+ 섹터 반전). 후속(히스테리시스/장창 x축)은 디렉터 판단 사안. 현 시점 코드 수정 금지 |
| MP2-SECTOR-CD-S3 | Slice 3 = RRG 회전 맵 서브스크린(D-SECTOR-NAV 옵션 B, 라우트 `app/market-pulse-v2/rotation`) + 판단 카드 회전 맵 CTA 활성화 + `cd_rel_strength_baseline` 메타(x축 판정선). 데이터=기존 단일 fetch(sectors[]+sector_history, STEP 0-3 신규 엔드포인트0) | @backend+@frontend | ✅ **done (land, 트랙 종결)** | 사분면 맵(서빙 2축 판정선)+11점 cd_state색+출발섹터 하이라이트+꼬리 5일(D-CD-TRAIL) raw 폴리라인(재분류0). pytest 신규6·vitest 신규14·tsc0 |
| MP2-SECTOR-CD-S3-PERROW | S3 보완 = 판단 카드 per-row 회전 맵 진입(D-SECTOR-NAV 이행 결함 수정). 각 행 전체 탭→`rotation?from=<그 행 symbol>`, 상단 CTA는 "전체 보기"(from=리더)로 의미 교정 | @frontend | ✅ **done (land `ceab955`+`27b5667`)** | 트랙 종결 상태 유지(재개봉 아님). FE 국소·additive·RRGChart/라우트/BE 무변경. vitest 신규7·tsc0 |
| CD-STAB | (측정 완료 2026-07-09 → 처방 확정 D-CD-STAB) cd_state 안정성 축별 분해 + 처방 후보 소급 시뮬. **축별 분해(289반전)**: X기인 63.7% 주범·Y 20.8%·동시 15.6%. 1일유지 0.633. 후보 반전율(원본 0.611): A 0.332·A′ 0.326·B 0.209·C 0.175. **처방 = ③ C 순차 채택**(B→A′) | @backend | 🏁 **트랙 종결 (2026-07-09)** — B land + A′ land 완료. **차순위 = B-1 FRED 백필**(ANALOG·TREND S4 이중 언락 키) | B=STAB-B, A′=STAB-A′ 순차, 둘 다 종결 |
| STAB-B | Slice B = 2일 히스테리시스. `resolve_official_cd_state` 무상태 리플레이(저장 히스토리 결정론적 재생) + 서빙 `cd_state` 의미전환=공식(D-CD-STATE-SEMANTICS) + `cd_state_raw` additive. 수락 앵커=측정 B 재현(≤07-09 창 99반전/0.209) | @backend | ✅ **land (2026-07-09)** | FE 변경 0(전 소비자 서빙값 소비 확증). 모델·마이그레이션 0(무상태 리플레이) |
| STAB-A′ | Slice A′(C 순차 후속) = x축 = 5일 상대수익(mom_5d − bench 5일 수익률, bench=SPY MarketIndexPrice, 서빙 시점 파생·저장 0). rel_strength_5d additive(판단 계열만, D-CD-XAXIS-SCOPE)·기존 rel_strength(1일)·히트맵 무접촉 | @backend+@frontend | ✅ **land (2026-07-09, CD-STAB 트랙 종결 슬라이스)** | **STEP 0 관측**: 방법론 앵커 B=99/0.209 정확 재현. **A′ 서빙 앵커 = 84/0.1776**(저장 momentum_5d 기준, 규칙 #3). 시뮬 목표 83/0.175와 1반전 편차 = XLU 05-19 경계값 + 데이터 드리프트(디렉터 판정 수용). 0-2 실서빙 관측=07-09 이후 신규일 0(축적 대기) |
| CD-TRANSITION-INDICATOR | (선택) "전환 확인 중" 표시 — raw≠official 비교로 FE 파생(분류 아님, 두 서빙값 단순 비교). 히스테리시스 +1일 지연을 사용자에 투명화 | @frontend | ✅ **이행 (CD-READ, 2026-07-09)** — cd_state_raw 첫 소비(칩+보조문+점선 링). 라이브 첫날 실증으로 필요 확정 | D-CD-STATE-SEMANTICS 경계 제외분 소진 |
| CD-READ | 판단 표면 가독성 — RRG 변형 H(포커스 디폴트 + 전체 꼬리 토글) + 고정 3건(미니맵 라벨 제거·전환 확인 중·cache 제거). FE 중심, BE 무변경(표시 전략만) | @frontend | ✅ **land (2026-07-09, D-CD-READ)** | 채점 H 4.35/F 4.10/D 3.90(사용자 선택). vitest 295·tsc 0. **B-1 STEP 0(별도 진행분)와 독립 병렬 가능**(무의존) |
| MP2-SUBPAGES | v1 위젯 5종(FearGreedGauge·YieldCurve·EconomicIndicators·GlobalMarkets·MarketMovers) v2 하위 페이지 흡수 (= `MP-V1-ABSORB` 실행) | **#3** | @frontend | 🕒 trigger-gated | recon [G] sub-pages 라우팅 0·v1 위젯 4/5 `frontend/components/macro/` 확인. 트리거 = #1·#2 land 후. STEP 0로 흡수 대상 재확인 |
| MP2-DATA-FEDWATCH-GEX | FedWatch(fed funds futures)·GEX(감마 익스포저) 외부 데이터원 신설 | **#4** | @infra+@backend | 🔴 **데이터게이트** | recon [E] 코드베이스 흔적 **0**(클라이언트 미보유) → **데이터원 확보 전 착수 금지**. 별도 공급원 조사 선행 |
| MP2-CROSS-SURFACE | cross-surface 통합(대시보드↔chain_sight↔portfolio 교차 표면) | **#5** | TBD | 🔴 게이트 | 선행 트랙(#1~#3) land 후. 범위는 그 시점 재정의 |
| MP2-E2E-SAFETYNET | **E2E 화면 회귀 안전망** — Playwright/Cypress 등 `/market-pulse-v2` 라이브 렌더 회귀 테스트(**모바일 에뮬레이션 포함** = resize_window 도구 한계 보완). Phase 2 **첫 인프라** | (인프라) | @qa+@frontend | 🆕 등록 (P2 선행 인프라) | 화면게이트가 수동 브라우저 의존(FE 크래시 2회·모바일 미확보) → Phase 2 변경 전 자동 회귀망 우선. 모바일 뷰포트 에뮬레이션으로 P2-① 구조적 해소 |
| MP2-DATA-BREADTH-CONC | **Breadth/Concentration raw 미수집** 점검 — Breadth 종목별 등락(상승/하락/신고저 0) + Concentration 상위종목 일부 부재. 화면은 graceful fallback 정상(밴드·sense 렌더)이나 raw 데이터원 점검 | (데이터) | @infra | 🆕 등록 (데이터 파이프라인 트랙) | D-P1-SCREENGATE P2-②. 화면 결함 아님(graceful) → 데이터 수집 task/소스 점검. Analog(#1) 입력 품질과도 연관 가능 |
| MP2-MOBILE-EYECHECK | **모바일 실기기 눈확인**(P2-① 권고) — 실기기/브라우저 DevTools 모바일 모드로 `/market-pulse-v2` 1회 눈검증 | (권고) | 사용자/병진 | 🟡 **비차단 권고** | D-P1-SCREENGATE P2-①. resize_window 뷰포트 미반영 도구 한계 → 반응형 설계는 JS 코드 입증 완료, 실렌더 눈검증만 잔여. MP2-E2E-SAFETYNET land 시 자동 흡수 가능 |
| **MP1.5-FIX** | **단일 FE 슬라이스** — ⒜ A1 brief 모달 `body` fallback 매핑 ⒝ A2 authAxios refresh 인터셉터 401 재시도 ⒞ A3 `<Pie label>` 포맷터(`toFixed`)+레이블 겹침 처리 ⒟ "cache: MISS" 엔드유저 노출 정리 ⒠ **① 유효 종목 수(1/HHI) 카드 표시** | @frontend | ✅ **완료 (2026-06-25, `2c9fbca` + 시각검증) — A3-tail 종결로 "완전 통과"** | D-P15-SCREENGATE. 시각검증 실측: A1 본문·① 유효종목수(≈51종)·cache 가드(dev전용, 프로덕션 비노출 코드입증)·회귀 = PASS / A2 = vitest 갈음 / A3 = MP1.5-A3-TAIL(`77847ca`)로 겹침·클리핑 완전 해소. 커밋 `0f86e55`(A1)·`9529671`(A3)·`a079870`(cache)·`2c9fbca`(①)·`77847ca`(A3-tail) |
| **MP1.5-A3-TAIL** | **A3 도넛 좌상단 소형조각 라벨 겹침** — `ConcentrationDetail.tsx` 라벨 겹침 해소 | @frontend | ✅ **완료 (2026-06-25, `77847ca`)** | **leader-line 외부 라벨**(좌/우 midAngle 분기 + 수직 슬롯 분산) + 상단 클리핑 해소(컨테이너 height 260→320 + nudge 하향 + Y_MIN/MAX 경계 가드) + **전역 가변 제거**(`computeAllLabelLayouts` 순수함수 + useMemo/ref, 다중 인스턴스 안전). 라이브 :3000 데스크탑+모바일(390px) **11개 라벨 전수 가시·클리핑 0·겹침 0** 실측. tsc 0, vitest 신규 28/전체 418. 1차(겹침만 수정)에서 상단 클리핑 결함을 시각검증으로 발견→2차 수정(좌표≠실렌더 교훈) |
| MP2-ANALOG-COND-RESULT | **조건부-과거-결과 primitive (공유)** — D-CONC-RISK-LENSES ②③을 Analog 트랙 산하로 이동. ② 퍼센타일(현재값의 과거 분위) + ③ 조건부 과거결과(고집중→이후 분포, **분포+표본수+신뢰구간만·단일숫자 금지**) | @backend (Analog 산하) | 🔴 **데이터 게이트** | **시간만으로 안 열림**: ②=데이터 깊이(≥1년) + ③=**레짐 다양성**(저집중 표본 필요, 현재 top10 13/13 전부 고집중=변별 0). 집중도뿐 아니라 regime 전반 조건부결과의 공유 primitive로 설계. Analog(#1) 착수 시 통합 |
| **MP-VIX-SRC** | VIX provider 읽기 소스 교체 — `MarketIndex/MarketIndexPrice(volatility, 0건)` → `IndicatorValue(VIXCLS, 232행)`. regime degraded(normal 일색) 복구 | @backend | ✅ **완료 (2026-06-26, `bbe6b1b`)** | STEP 0 측정: volatility 소스 0건 → `_calculate_regime`이 항상 'normal'(EODDashboard 75행 전부). 단일 파일(`macro_vix_provider.py`), VIXProvider 포트 ABC·반환계약 불변(BOUNDARY-3 유지). 행위 델타 재계산 `{normal:75}`→`{normal:57,elevated:10,high_vol:8}`. 신규 6 + 회귀 384/1skip |
| **MP-VIX-BACKFILL** | EODDashboard 76행(2026-02-25~06-26) regime 소급 재적재(B-3) | @backend | ✅ **완료 (2026-06-29)** | `json_data['market_summary']['vix_regime']` 76행 재계산 UPDATE. **18행 변경**(03-03~04-07 고변동 → high_vol/elevated), 분포 `{normal:76}`→`{normal:58,elevated:10,high_vol:8}`. lookback 0부족(MP-VIX-STALE 백필로 전구간 커버) · 결정론적 · **백업 선행**(`eod_regime_backup_20260629.json` normal:76 원본) + 트랜잭션 원자적 + **멱등 재현**(재실행 0행). intraday RegimeSnapshot은 히스테리시스로 forward-only(백필 불가) — EOD만. **MP-VIX 트랙 3종(SRC·STALE·BACKFILL) 전체 종결** ✅ |
| **MP-VIX-STALE** | VIXCLS(+DGS 일간군) sync stale — 자동 재귀 beat 커버리지 갭 수리 | @infra | ✅ **완료 (2026-06-28~29, 코드 `20f0e6d` + 백필 + 워커 재기동)** | STEP 0: VIXCLS·DGS10·DGS2·T10Y2Y가 `FRED_RECURRING_SERIES`(7종) 밖 = 자동 재귀 미커버 → 수동 의존, 06-12 stale. **경우 P 확정**(FRED는 06-25까지 발행, 우리가 안 받음 — 실호출 검증, FRED 지연 Q 반증). 수리: `FRED_RECURRING_SERIES` **7→11**(일간 4종 편입, beat·task 무변경, 멱등 upsert) + PART2 백필 33행(06-13~25) + **워커 재기동**(celery-worker 33397→6413, `.delay()`로 11종 import 입증 7→11). beat `enabled`(평일 NY17:40). 재발방지 4축(코드·워커·sync·beat) 충족 |

> **집중도 카드 점진 공개 (D-CONC-RISK-LENSES)**: **① 유효 종목 수 = now**(MP1.5-FIX 동봉) / **② 퍼센타일 = 데이터 깊이 충족 시**(1년 미만이면 "표본 N일, 잠정" 정직 라벨 필수) / **③ 조건부 과거결과 = Analog 트랙**(MP2-ANALOG-COND-RESULT, 레짐 다양성 게이트). 가짜 절대리스크("40%→X%") 금지.
>
> **STEP 0 케이던스 실측(2026-06-25)**: beat `mp_calc_concentration_daily` = **평일 daily**(17:15 NY, cron `15 17 * * 1-5`). 최근 6/16~6/25 daily 정상. **단 5/7~6/11 35일 갭**(과거 운영 공백 — daily 의도이나 누락, 주간 의도 아님). → ② 타임라인: **현재부터 daily 누적 시 ~1년 후 가능**(과거 갭 미백필). 데이터 트랙 신규 항목 불요(beat 현재 정상 가동, 갭은 과거분).
>
> **Phase 1.5 게이트 = 완전 종결(2026-06-25, D-P15-SCREENGATE)**: MP1.5-FIX 5건 전부 PASS — A1 본문·① 유효종목수·cache 가드·회귀 실측 + A2 vitest 갈음 + **A3 = MP1.5-A3-TAIL(`77847ca`)로 겹침·상단 클리핑 완전 해소**(라이브 데스크탑+모바일 11라벨 전수 가시). 잔여 0. **→ Phase 2(#1 MP2-ANALOG) 진입 가능.** 기존 트랙 유지: MP2-ANALOG(#1, active)·MP2-ANALOG-COND-RESULT(②③ 데이터게이트)·MP2-DATA-BREADTH-CONC(B1)·MP2-E2E-SAFETYNET·MP2-MOBILE-EYECHECK.

---

## market_pulse v2 Phase 1 잔여 (2026-06-07 카탈로그 역산 확정)

> 근거: `DECISIONS.md` "## [2026-06-07] Phase 1 PR 카탈로그 역산 확정". 백엔드 A~J done(J는 I 흡수), FRED fetcher done, Translation/Playbook은 Phase 1.5/1.6 이관(범위 외). 본 표는 출시 전 정리할 6 트랙. **Phase 1 종료(2026-06-23, P1-close + 화면게이트 조건부통과) — 잔여는 위 Phase 2 로드맵으로 재배치.**

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|----------------|
| MP1-K | Phase 1 프론트엔드 Layer0(메인 페이지) — Card A 헤더/지표/regime 표시 | @frontend | - | **완료 2026-06-10 (static 기준)** | `frontend/app/market-pulse-v2/page.tsx` (Layer0) + `cards/RegimeCardSummary.tsx` + `components/{TickerBar,StatusBanner}.tsx`. 5 card_id 라우팅 + `useOverview()` TanStack Query. 라이브 검증은 `MP-LIVE-VERIFY` 게이트로 분리(아래). 직전 "0%" 측정은 없는 src 경로 grep 오류(common-bugs #31) |
| MP1-L | Phase 1 프론트엔드 카드 컴포넌트 — Card B/C/D/E 4종 + news/health 위젯 | @frontend | MP1-K | **완료 2026-06-10 (static 기준)** | `frontend/app/market-pulse-v2/cards/` 5 Summary + `details/` 5 Detail(+Container) + `components/{AnomalyPanel,CardDrawer,NewsPanel,StatusBanner,TickerBar}.tsx` + `lib/api/marketPulseV2.ts` (30+ 타입 + 4 fetch). health 위젯은 `StatusBanner` 매핑 추정(`MP-KL-F3` 확인). 라이브 검증 `MP-LIVE-VERIFY` |
| MP1-C-stress | regime classifier `stress_input` 훅 (1줄 인터페이스, Phase 1.5 무재설계 전제) | @backend | - | **완료 2026-06-10** (`ce0be51`) | `apps/market_pulse/regime/classifier.py:classify_inputs(*, stress_input=None)` keyword-only Optional + 즉시 del. 회귀 138 passed (136+2 신규). 행위보존 |
| MP1-M | runbook task 경로 갱신 — `marketpulse.tasks.*` → `apps.market_pulse.tasks.*` (10 task 전건) | @infra(@qa) | - | **완료 2026-06-10** (`ef9d064`) | `docs/operations/marketpulse_v2_celery_tasks.md` 10건 전수 치환. grep 옛 경로=0 / 새 경로=10. NT-7 정합 잔재 정리 |
| MP1-N | market_pulse 능동 모니터링 자산 — `services/news.tasks.check_pipeline_alerts` 패턴을 market_pulse로 확장 (anomaly engine error rate / regime stale / news feed lag 등) | @infra | - | 🟣 **재배치: Phase 2 백로그 (P1-close, 2026-06-23)** — 신규 기능(저우선 청소 아님) | STEP 0: alerts.py 신설 = 신규 모니터링 기능(코어 대시보드 동작과 무관·게이팅 아님). Phase 1 종료 범위 외 → Phase 2 로드맵 후보 풀로 자연 합류. 트리거 = Phase 2 착수 or 운영 알림 필요 |
| MP1-A3-sep | A3 마이그레이션 3분리 (`BreadthSnapshot`/`SectorFlowSnapshot`/`ConcentrationSnapshot`을 `0002`/`0003`/`0004`로 분리) | @backend | - | 🔴 **HALT/재배치 (P1-close STEP 0, 2026-06-23)** — 전제 stale·파괴적 | STEP 0 실측: marketpulse 0001~0006 **전부 [X] prod DB 적용**·0002~0005는 이미 `pr_a2_*`(field/rename/restructure) 점유·Snapshot 모델은 0001_initial에 통합 생성. 원문 가정("0002/0003/0004로 분리") stale → 적용된 history 사후분리 = 파괴적(행위보존 불가). **닫지 않음 — DORMANT 재배치**(squash는 신규 DB 재구축 시에만 의미) |
| MP1-test-gap | PR-B fetchers 테스트 모듈 (`fmp_weights.py` 커버) — ~~PR-I serializer 도메인별 분리는 STEP 0에서 저실익 판정 스킵~~ | @backend + @qa | - | ✅ **완료 (P1-close, 2026-06-23, `d455382`, 축소)** | STEP 0: serializer `overview.py` 13클래스 통합=145줄(비대 아님)·import 파급 5곳 → 분리 저실익 스킵(재배치 불요·실익 없는 구조변경 영구 보류). fetchers `fmp_weights.py` 테스트 11건 보강(파싱/정규화/rank/skip/가드). additive, pytest marketpulse 226→237. 마이그레이션 0 |
| ~~**[GATE:release] MP-LIVE-VERIFY**~~ | **Phase 1 출시 전 필수 — 라이브 검증 게이트** | @qa + @frontend | MP1-K · MP1-L · MP-KL-F3 | ✅ **전건 통과 (2026-06-11)** — ⒜ 계약(C·D) 전건 PASS(d5212d4 검증: overview concentration 키·/cards/flow 404·i18n·5 카드 렌더·drawer detail) ⒝ Briefing 데이터 = MP-LV-D2 수리(`62d4025`) → brief 카드 재게이트 통과 ⒞ Concentration 데이터 = MP-LV-D1 옵션 B 수리(`c6b7aa0`) → SP500_MCAP 스냅샷 생성 + concentration 카드 재게이트 통과(top5 28.29%·HHI 0.0221, /cards/concentration 200·당일·값 정합, /cards/flow 404 유지). **Phase 1 종료 (2026-06-11)** — 게이트 전건 통과 = Phase 1 범위 완료. **출시는 별도 결정**(운영 자율 가동 확인 `MP-OPS-AUTOGEN-CHECK` + `MP-UX-POLISH` 이후 사용자 선언). 상세 DECISIONS "[2026-06-11] Phase 1 종료 선언" | 검증 보고서(curl + DOM 채증) + DECISIONS "[2026-06-11] 게이트 1차 결과"·"[2026-06-11] MP-LV-D1 옵션 B". 부분 재게이트 원칙(수리가 계약 무관 → 해당 카드 스모크만) 적용 |
| MP-KL-F1 | market-pulse-v2 프론트 테스트 신설 — `frontend/__tests__/` 내 0건 → vitest 기반 단위/통합 추가 | @frontend + @qa | MP1-K · MP1-L | **완료 2026-06-11** (`e538e7f`, 원본 `8f1ba79`) | `frontend/__tests__/market-pulse-v2/{fixtures.ts,page.test.tsx}` 12건 (page 로딩/에러/happy + StatusBanner OK숨김·STALE표시 + 5 카드 펼침 라우팅 + drawer 닫기) + `vitest.setup.ts` ResizeObserver 폴리필. vitest 162→174 |
| MP-KL-F2 | cardId `'flow'` → `'concentration'` 행위보존 리네임 (Summary/Detail 파일명 + `CardId` 타입 + `CARD_TITLE` 매핑 + API 계약 영향 범위) | @frontend | MP1-K · MP1-L | **완료 2026-06-11** (`902ec86`, 원본 `70a00c9`) — **게이트 선행 실행됨**(게이트 의존 표기 삭제, 근거 DECISIONS [2026-06-11] MP-KL-F2 게이트 선행) | BE 7곳(VALID_CARDS·enum·dispatch·overview 키·serializer·i18n·test parametrize) + FE 10곳(Flow→Concentration 파일·타입·page·container·hooks·lib·i18n) 원자적. 동명이의 3종(briefing Literal·flow_proxy·news_classifier) 보존. BE 138 / FE 174 / tsc 0 / card 'flow' 잔존 0 |
| MP-KL-F3 | health 위젯 명세 검증 — `MP1-L`의 "health 위젯"이 `StatusBanner` 매핑인지 별도 위젯 필요한지 `page.tsx` 본문 분석 + `OverviewView` health 필드 대조 | @frontend + @backend | MP1-K · MP1-L | **완료 2026-06-11** (`d5289a2`, 원본 `f16efcb`) — **StatusBanner 확정**(별도 위젯 불요) | 판정: 사용자 대면 health = `StatusBanner`(overview `_meta.status` 5값 전수 매핑, 3중 정합). `/health`는 IsAdminUser ops probe로 프론트 미통합 정상. MP-LIVE-VERIFY health 선결 해소. 📎 `docs/market_pulse_v2/mp_kl_f3_health_widget_verification.md` |
| MP-V1-DECISION | v1 `app/market-pulse/page.tsx` (310 lines, useMarketPulse v1 hook, `/api/v1/macro/pulse/`) 거취 결정 — 폐기 / 리다이렉트(v2로) / 보존(레거시) 중 택1. v1 내부 `MarketNewsSection` "TODO: 컴포넌트 미구현" 주석 처리 포함 | orchestrator + @frontend | - | **완료 2026-06-10 (옵션 D 채택)** | 결정: 보존 + Phase 2 흡수 예약. 가중합 D 3.90 vs C 3.55 (마진 0.35, 타이브레이커: 게이트 안전 순서 + Phase 2 정합). 상세 = DECISIONS "[2026-06-10] v1 거시 대시보드 거취 — 옵션 D". 후속 실행 = `MP-V1-ABSORB`(아래) |
| MP-V1-ABSORB | v1 위젯 5종(`FearGreedGauge` · `YieldCurveChart` · `EconomicIndicators` · `GlobalMarketsCard` · `MarketMoversSection`) v2 하위 페이지로 흡수 + `/market-pulse` → `/market-pulse-v2` 리다이렉트 전환 + v1 코드 제거 + 동결된 `MarketNewsSection` TODO 주석 일괄 처리 | @frontend | Phase 2 sub-pages 트랙 착수 | 🕒 **trigger-gated** — Phase 2 sub-pages 착수 전까지 다른 세션에서 먼저 꺼내지 말 것 | 흡수 PR 시리즈 + `/market-pulse` 리다이렉트 + `app/market-pulse/page.tsx` 삭제 + v1 hook(`useMarketPulse`) 정리. 트리거 도래 시 STEP 0로 흡수 대상 위젯 재확인(다른 위젯 추가됐을 가능성) |
| MP-LV-D1 | Concentration FMP `/stable/etf/holdings` 프리미엄 402 결함 — 비중 공급원 결정 | orchestrator + @backend | - | **완료 2026-06-11 (옵션 B 채택, `c6b7aa0`)** | 시총 가중 근사(S&P500 심볼 × FMP quote marketCap → weight=cap/Σcap). `fetchers/weight_source.py` seam 분리(MarketCapWeightSource 기본 / HoldingsWeightSource 휴면 / `ACTIVE_WEIGHT_SOURCE` 1곳 전환). 산식·모델·계약 불변, universe='SP500_MCAP'. 회귀 138→146. 호출 ~500 quote/일. 상세 DECISIONS "[2026-06-11] MP-LV-D1 옵션 B" |
| MP-D1-FMP-UPGRADE | FMP 플랜 업그레이드(holdings 엔드포인트 확보) 시 옵션 A 전환 — `weight_source.ACTIVE_WEIGHT_SOURCE`를 'holdings'로 변경 + CB[fmp_etf] 리셋 + Concentration 카드 스모크. 정확한 float-adjust holdings 비중 복원 + ~500 quote/일 호출 제거 | @backend | FMP 플랜 업그레이드 | 🕒 **trigger-gated** — 플랜 업그레이드 전까지 먼저 꺼내지 말 것 | seam 선택 1곳 변경(holdings 경로 휴면 보존 = 코드 그대로) + CB 리셋 + 스모크 |
| **MP-LV-D2** | Briefing task `ModuleNotFoundError: google.generativeai`(구 SDK) → CB[gemini] OPEN, 생성 이력 0 수리 | @backend | - | **완료 2026-06-11** (`62d4025`) | 신 SDK(`from google import genai`, v1.75.0 기설치) import + contents `parts` 포맷 `[string]→[{text}]` 정정(prompt.py+client.py, requirements 변경 0=case ⒜). 검증: `.apply()` SUCCESS → BriefingLog(OK, gemini-2.5-flash) + pytest 138 + brief 카드 재게이트 통과 |
| MP-UX-POLISH | market-pulse-v2 사용자 대면 표면 개선 — raw 전문어/약어 노출(HHI·top5·top10·dispersion·rotation·AD-line·coverage·momentum) + 단위/맥락 없는 raw 숫자(HHI 0.0211) + 용어 도움 인프라 부재(tooltip/glossary 0) + i18n en 백엔드 라벨 0(FE FALLBACK 의존) | @UI-UX-designer → @frontend | MP-LIVE-VERIFY ✅ 통과 | ✅ **자기설명화 완결 close (P1-close, 2026-06-23)** — 중첩 정리 | S1(라벨 단일소스)·S2(의미 밴드)·S3a/S3b(BE history/margin)·TITLE-SOURCE·UX-S5 밴드 전건 완료 + **Translation Layer 본체(S2~S5)로 카드 LLM 해설 중첩분 닫힘**(prose 자기설명 = 사용자 대면 완비). **실질 잔여 = tooltip/glossary 인프라 + EN i18n** → 둘 다 **Phase 1 외 후속 폴리시 이월**(PROGRESS L31 결정, 한국어 모바일-solo 1차 surface, 비게이팅). Phase 1 자기설명화 범위 종료 |
| MP-UX-S1 | 라벨 카탈로그 단일소스화 — KO_LABELS metric/universe/indicator 14키 + raw→translate(요약 5 + detail 4 + StatusBanner) + status·regime detail 이중소스 해소 | @frontend | MP-UX-POLISH | **완료 2026-06-15** (`05e633a`) | KO_LABELS +14키 / 신규 vitest 10 / tsc 0·vitest 184·eslint 0. ff push(ffbe599→05e633a) |
| MP-UX-S2 | 의미 밴드 — 매크로지표 9종 한글 흡수 + Regime 단계 의미 밴드(단계별 색) + Anomaly 모드 의미 밴드 + rule actual↔경보선(`fired[].threshold` FE만) + 직전→현재 전환 | @frontend | MP-UX-S1 | **완료 2026-06-15** (`75eaadb`, rebase 경유) | `meaning.ts` 의미 카피 단일소스 / `indicator.*` 14종 완비(레이더축 raw 0) / 신규 vitest 7 / tsc 0·vitest 191·eslint 0. NEWS-AUTH(`a4c1cc4`) non-ff → rebase(충돌 0/파일 겹침 0) 후 ff push. 근거 DECISIONS "[2026-06-15] MP-UX-S2" |
| MP-UX-S3a | (BE) regime `history_30d` 엔드포인트 — `cards.py _regime_detail`에 추가(breadth/concentration 패턴 재사용) → 국면 타임라인 데이터원 | @backend | - | **완료 2026-06-15** (`abf262a`, S3 Part A) | RegimeSnapshot 41 distinct date → history 30 채움(백필 불요). 무마이그레이션(즉석 쿼리). pytest 4. FE 타임라인 렌더는 후속 FE 슬라이스 |
| MP-UX-S3b | (BE) regime "다음 단계까지 거리"(margin) payload 산출 — 현재 14지표값 vs rules.yaml 다음단계 임계 margin. rules.yaml 백엔드 단일소스 유지(FE 하드코딩 금지) | @backend | - | **완료 2026-06-15** (`6d358e8`, S3 Part B) | `regime/next_stage.py` classifier.load_rules 읽기(임계 하드카피 0) + serializer 즉석 산출(무마이그레이션, `makemigrations --check` No changes). pytest 6. ⚠ 게이지 의미값은 `MP-DATA-MACRO-COVERAGE` 선행. FE 게이지 렌더는 후속 FE 슬라이스 |
| MP-DATA-MACRO-COVERAGE | (ops/data) 거시 시계열 5종(`vix·nfci·hy_oas_pct·t10y2y_pct·t10y3m_pct`) `RegimeSnapshot.inputs` 데이터 공백. **코드 결함 아닌 운영 사안** — fetcher/backfill(`backfill_v2_a1`)/shared 래퍼(`fred_client`)/beat/게이지 경로 전부 기구현(STEP 0 cf82fe9), 원인 = `FRED_API_KEY` 미설정 + 미실행으로 stale(검증 시 5종 19~60일 경과). | @infra(@backend) | - | ✅ **데이터 적재·게이지 점등 검증 완료 (2026-06-16)** — 병진 수동 백필(Economic 153/Market 44 obs) 후 `GET /cards/regime/detail` HTTP 200, 5종 실값(vix 17.68 등)·sources 14/14 OK·coverage 1.0·대기 0·regime=LATE_BULL. serializer/FE 변경 0(신선도가 트리거). **단 지속성=beat 운영 의존**(수동 백필 기반 → beat 미가동 시 ~14일 후 stale 회귀 = 출시 체크리스트). | 신규 코드 0(중복 금지, 규약 10장). `.env.example`에 FRED_API_KEY 추가(재발 방지). 근거 DECISIONS "[2026-06-16] MP-DATA-MACRO-COVERAGE 검증 완결" |
| MP-UX-TITLE-SOURCE | 카드 제목 단일소스 — `card.regime`="시장 레짐"(KO_LABELS) vs CardShell 하드코딩 `"시장 국면"` 불일치(census #4). 표시 용어 '레짐/국면' 산재 → 단일 상수 `REGIME_TERM='국면'` 통일 | @frontend | - | **완료 2026-06-16** (S5 Part C `51303f1`, **origin/main 안착**) | meaning.ts `REGIME_TERM` 단일소스 → RegimeCardSummary/RegimeDetail/RegimeTimeline/page.tsx 치환(표시 문자열만, 로직·enum 불변). vitest +5. 행위보존 PASS(MGMT-FLUSH-2 Phase A) |
| MP-I18N-EN | i18n en 로케일 백엔드 라벨 부재 — `get_labels('en')` 빈 응답 + `_meta.warning='unsupported locale: en'`, FE FALLBACK_LABELS(8키)만 의존. ko 28키 대비 en 백엔드 0 | @backend | - | 🟣 **재배치: Phase 1 외 후속 폴리시 이월 (P1-close STEP 0 확정, 2026-06-23)** | STEP 0 충돌 점검: PROGRESS L31(2026-06-18) "**EN i18n·tooltip/glossary는 Phase 1 외 후속 폴리시로 이월**(게이팅 아님 — 한국어 모바일-solo가 1차 surface)" 명시 결정 존재 → P1-close에서 **닫지 않음**. 한국어 단일 surface 동안 비게이팅. 트리거 = EN surface 필요(국제화 결정) 시 |
| MP-UX-S5-B-SECTOR | 섹터 자금흐름 스파크라인 — SectorCardSummary/SectorDetail에 섹터별 추세선. **선행: `SectorDetail`에 sector history 시계열 부재** → BE 미니슬라이스(additive serializer 필드) 필요. 현재 합성 없이는 불가(합성 금지 원칙) | @backend(history) → @frontend(스파크라인) | MP-UX-S5(머지) | 🕒 **보류 (선행 의존)** — 집중도 스파크라인은 S5 Part B로 완료(`history_30d` 존재). 섹터만 history 부재로 분리 | S5 STEP 0 §0-3 실측: ConcentrationDetail.history_30d 존재 / SectorDetail history 0건. RegimeTimeline·집중도 스파크라인과 동일하게 history 데이터원 확보 후 FE 진행. ⓘ 단서(2026-06-16): FRED 백필로 XL 섹터 ETF bars(Market 44 obs) 신선화됨 → 착수 STEP 0에서 SectorDetail history 필드 존재 여부 재확인 시 선행이 풀렸을 가능성(추측 — 재확인 전 보류 유지) |
| MP-OPS-RESTART | 게이트 후 운영 정합 복구 (병진 수동) — 메인 디렉터리 `main` 복귀 + `git pull --ff-only`(70eb090↑ 정착) + 구 브랜치 `monorepo/sess-mp-kl-f1f3` `-D` + 운영 celery 재기동 + `setup_marketpulse_beat` 재실행(Bug #28 절차) | 병진(수동) | - | ✅ **완료 2026-06-15** | 메인 디렉터리 main 복귀 + merge worktree 제거 + 구 브랜치 `-D`(내용 origin/main 흡수 검증) + celery worker/worker-neo4j/beat kickstart(새 코드 적재) + `setup_marketpulse_beat`(updated=11). 검증 `ACTIVE_WEIGHT_SOURCE=market_cap`/SP500_MCAP + Beat 11종 enabled. 수용 기준 충족 |
| MP-OPS-AUTOGEN-CHECK | 재기동 후 **다음 영업일** 5종 스냅샷(Regime/Breadth/Sector/Concentration/Briefing) beat **자율 생성** 확인 — 이번 게이트는 수동 트리거 검증이었으므로 자율 가동은 별도. ⚠ Briefing은 **LLM 일 1회 과금 시작점** | @infra + @qa | MP-OPS-RESTART | ✅ **완료 (검증 충족, P1-close STEP 0 실측, 2026-06-23)** | STEP 0 실측 수용기준 충족: 5종 스냅샷 전부 당일 row(age=0d, 2026-06-23) + beat **18/18 enabled·최근 72h last_run 보유 18/18**(mp_calc_regime/breadth/sector/concentration·brief·finalize 자율) + Concentration=SP500_MCAP·mp_sync_fred 자율. 재기동(MP-OPS-RESTART 06-15) 후 8일간 매 영업일 자율 생성 지속 = "익영업일 자율 생성" 입증. ⚠ Briefing LLM 과금 가동 중(status=OK) |
| MP-CONC-FREQ-TUNE | 시총 근사 Concentration task ~500 FMP quote/일 — 타 task(EOD/financials/movers) 합산 일 10k 한도 압박 시 주간 빈도 검토 | @infra | - | ✅ **완료 (현행 유지 결정, P1-close 슬라이스 2, 2026-06-23, 코드 0)** | STEP 0 압박 실측: FMP 402/429/rate-limit 로그 **0건** + beat 정상 가동(CB 에러 0) = 일 10k 한도 압박 없음 → **현행 daily(mp_calc_concentration_daily, NY 17:15) 유지** 결정. 코드 변경 0. 재검토 트리거 = 타 task 합산 압박 발생(429/402) 시 |
| MP-OPS-FRED-FRESHNESS | (출시 체크리스트) 배포 환경에서 `update_economic_indicators` beat + RegimeSnapshot 생성 **지속 실행** 확인 → 거시 5종 14일 staleness 방어(미가동 시 게이지 "대기" 회귀). 배포 시 `setup_marketpulse_beat` 재실행(common-bugs #28) + beat DB drift 점검(NT-7) | @infra | MP-DATA-MACRO-COVERAGE | 🟡 **defer/DORMANT (P1-close 결정, 2026-06-23)** — 배포 절차 전용, 출시 없음 | STEP 0: 명시적 "(출시 체크리스트)·배포 환경" = 순수 배포 절차. 개발 중 화면 영향 0(FRED 거시 5종 null 0·regime 정상·mp_sync_fred 자율 3.0h 전). 출시 계획 없음 → defer. 트리거 = **실제 배포 결정 시**. 수용기준(beat 신선·14일 이내·FRED_API_KEY 배포 설정)은 그 시점 검증 |
| MP-OPS-FRED-ENTRYPOINT | v2 11종 + VIXCLS·T10Y2Y를 한 진입점에서 날짜범위 백필하는 **thin wrapper**(기존 `backfill_v2_a1`/`sync_marketpulse_v2_indicators`/`sync_all_indicators` 호출 조합, **신규 fetch 로직 0**). 동기 = VIXCLS·T10Y2Y가 `backfill_v2_a1` 기본목록 밖이라 현재 진입점 분기(`--series-id` 개별 또는 v1 sync 경로) | @infra | - | ✅ **완료 (P1-close, 2026-06-23, `1a25d2a`)** | `backfill_macro_all` 신규 — backfill_v2_a1(기본 econ11+market11) + EXTRA_FRED_SERIES(VIXCLS·T10Y2Y) 개별 호출 조합(**신규 fetch 0·shared 무접촉**). backfill_v2_a1에 `--econ-only` additive 플래그(EXTRA 호출 market 중복 재백필 방지). dry-run 실동작 검증(EXTRA Market=0). 테스트 6 + backfill_v2_a1 기존 7 회귀 0. pytest 237→243. 마이그레이션 0 |
| T-GAUGE-1 | regimeTone 톤 시각 검증 보류 — B-3 게이지(8b14dd8) 라이브 검증 시 5지표 전건 미돌파(LATE_BULL 안정)라 거리 바 중립 slate, regimeTone(돌파 시 강조)은 시각 미노출 = **설계 정합(버그 아님)**. DOM `data-breached=false` 5/5 확인 | @qa | B-3(8b14dd8) | 🆕 경미·데이터종속 | 재개 트리거 = regime 전환 임박/돌파(`to_threshold≤0`) 실발생 시 톤 렌더 재확인 |
| LINK-DATA-FAIL | (트리아지 종결) 메일 CTA 링크 → mp 화면 뜨나 데이터 로드 실패. read-only 트리아지 T1~T6 실측: FE :3000(CORS 포함)·BE :18765 기동·CORS 허용(ACAO 부여)·FE base 정합·CTA 딥링크 파라미터 없음 → **판정 = 인증 게이트(코드 버그 아님)**. overview/cards = `IsAuthenticated`, JWT=localStorage `access_token`. 미로그인 브라우저(로그아웃/토큰삭제/만료+refresh 실패)에서 CTA 오픈 → 401 → "데이터를 불러오지 못했습니다"(mp 페이지 인증 가드 부재). curl `/overview` = 401 실측 | @qa(read-only) | - | ✅ **종결 (2026-07-07, 커밋 0)** — 수리 불요. CORS/base/딥링크 전부 배제(실측). 운영 메모 = common-bugs 등재 | authed 경로 2차 데이터 결함은 미검증(토큰 엔드포인트 상이, 래빗홀 회피) — 인증이 첫 게이트임은 확정 |
| MP-401-MSG | (조건부) mp 페이지 401 구분 문구 — 미인증/세션만료 시 "데이터를 불러오지 못했습니다"(일반 실패)와 구분해 **세션 만료/로그인 안내** + 로그인 리다이렉트(return-to 딥링크). LINK-DATA-FAIL 부 판정(FE UX 갭)의 수리 후보 | @frontend | LINK-DATA-FAIL | 🔒 **조건부 보류** | 트리거 = **실사용 세션만료 혼동 발생**. 그 전 착수 금지 |
| T-GAUGE-2 | 금리차 라벨 절단 — `t10y2y_pct`·`t10y3m_pct` 둘 다 label `w-28`에서 "장단기 금리차(10..."로 절단, 좁은 폭 구분 모호(closest 볼드로 일부 완화). 정확성 문제 아님, 모바일 360px 무오버플로 확인 | @frontend | - | 🆕 경미·UX 저우선 | 후속 라벨 작업 시 묶어 처리(짧은 식별자 "10Y-2Y"/"10Y-3M" 또는 툴팁) |
| MP-UX-BREADTH-BAND | Breadth 의미밴드(변형 A: 종합 밴드 1줄 + 신고저·AD 부제) — `meaning.ts breadthBand`(0.5 중심 ±0.10/±0.20 사다리, 엇갈림 댐핑, FLOW_TONE) + Summary/Detail + `labels.py breadth.*`. **v2 정량 카드 자기설명화 완결**(Regime·Sector·Concentration·Breadth 4/4 밴드) | @frontend | MP-UX-S2 | **완료 2026-06-18** (`43ae93b`) | vitest market-pulse-v2 91→100(+9)·tsc 0·pytest 166·마이그레이션 0. BE serializer/차트 0. ⚠️ 임계 TUNE(dev n=1 미검증) → T-BREADTH-TUNE |
| T-BREADTH-LIVE | dev breadth 실데이터(beat 가동, advance/decline 채워진 뒤) 라이브 밴드 눈검증 — 현재 dev DB 거의 EMPTY(오늘 advance+decline=0→밴드 null)라 라이브 미확인. 컴포넌트 테스트로만 렌더 검증됨 | @qa | breadth beat 데이터 채움 | 🆕 경미·데이터종속 | 재개 트리거 = breadth snapshot 실데이터 누적 후 라이브 카드 밴드 1컷 |
| T-BREADTH-TUNE | 실 SPY breadth(~500종목) 누적 후 `BREADTH_THRESHOLDS`(lean 0.60/broad 0.70) 경계 실분포 재튜닝 — `concentrationBand` TUNE과 **묶음** 처리. 현재 0.5 중심·관례 앵커(STEP 0 dev n=1로 실분포 미검증) | @frontend | breadth 실분포 누적 | 🆕 저우선·TUNE | 실분포 히스토그램으로 5밴드 경계 검증/조정. concentration TUNE 동시 |

## market_pulse Phase 1.5 Translation Layer (2026-06-18 착수)

> 근거: `DECISIONS.md` "[2026-06-18] Phase 1.5 Translation Layer 토대 3결정". 카드 LLM 해설(prose/감각 유추) 레이어. **BOUNDARY-LLM(shared 래퍼)은 별도 트랙 이연 — 본 트랙 무접촉**(래퍼=Brief 패턴 in-zone 재사용). S2~S5 로드맵: TranslationLog → per-card prompt+task → envelope serializer+FE selector+fallback → golden/vcr.

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|----------------|
| MP-TRANSLATION-S1 | Brief LLM plumbing 단일출처 추출 → `apps/market_pulse/llm/` (행위보존 GATE) | @backend | - | **완료 2026-06-18** (`5104635`, origin/main 안착) | `apps/market_pulse/llm/` Brief 플러밍 단일출처. 토대 3결정 DECISIONS 흡수(① 래퍼 in-zone 재사용 ② 별도 translations envelope=TranslationLog ③ golden+vcr) |
| MP-TRANSLATION-S2 | TranslationLog 모델 (BriefingLog 미러, 신규 테이블 1개) — 1 LLM 호출의 카드별 감각 유추 문장 전부를 하루 1행에 담는 그릇 | @backend | MP-TRANSLATION-S1 | **완료 2026-06-18** (`daeef5b`, origin/main 안착) | `apps/market_pulse/models/translation.py` (TranslationLog) + 마이그레이션 0006(CreateModel only, 기존 Alter 0, dry-run No changes) + admin + 모델 테스트 18건. 토큰=BriefingLog 정확 미러(prompt/completion 분리) + created_at만(사용자 결정). 기존 모델 FK 0(decouple). 회귀 pytest marketpulse 166→184(+18). 다음=S3(per-card prompt+task) |
| MP-TRANSLATION-S3 | per-card prompt builder + 생성 task — 1 LLM 호출 → 4카드 감각 유추 JSON → TranslationLog 1행 upsert | @backend | MP-TRANSLATION-S2 | **완료 2026-06-18** (`84b3d76`, origin/main 안착, CS-RD3 drift rebase 경유) | `llm/translation_prompt.py`(SYSTEM_PROMPT+context builder, Brief 패턴 미러) + `llm/translation_safety.py`(validate_senses) + `tasks/translation.py`(`mp_generate_translation_daily`, 공용 `generate_with_circuit` 1회 + JSON 파싱 + `llm.safety` + `update_or_create` upsert) + tasks/__init__ + beat(NY 17:45) + 테스트 11건. **★ HALT 없음, 옵션(a) raw+정성지침(meaning.ts 임계 복제 0).** 마이그레이션 0. 회귀 184→195(+11). 수동 트리거 실 Gemini OK(4 senses, tokens 1129/115). ⚠ cost_usd=null(단가 단일출처 부재, Brief 동일). 다음=S4(envelope serializer+FE) |
| MP-TRANSLATION-S4 | envelope serializer + FE selector + fallback — overview 최상위 `translations` 블록(cards 무변경) + 카드 sense 소비 + 3상태 fallback | @backend + @frontend | MP-TRANSLATION-S3 | **완료 2026-06-18** (`bc01b1e`, origin/main 안착) | BE(`c9a0729`): overview `_build_payload`에 `translations` 블록(senses+model_version+generated_at+status, 없으면 null, 빈senses={}≠null) + `TranslationsSerializer` + cards 불변 가드. FE(`bc01b1e`): `selectSense` selector + 4카드 optional `sense` prop(dumb 유지) + `SenseNote`(없으면 미렌더) + fallback 3상태. 밴드·raw additive 불변. **★ 카드 키 정합, HALT 없음.** 마이그레이션 0. 회귀 pytest 195→200·vitest 100→107·tsc 0. 다음=S5(golden+vcr) |
| MP-TRANSLATION-S5 | golden + vcr 하네스 (+ Brief 동반 보강) — 실 LLM 출력 계약 가드 | @backend + @qa | MP-TRANSLATION-S4 | **완료 2026-06-23** (`4246d48`, origin/main 안착, ff 머지 — push 시 76c0e38→1b28b0c[infra/chainsight] drift는 직전 세션 rebase로 흡수[충돌 0·파일 겹침 0], 본 머지는 1b28b0c→4246d48 FF-SAFE) | **★ STEP 0: vcrpy 미설치·카세트 인프라 0 → HALT 보고 → 사용자 결정 스냅샷 fixture 방식**(실 Gemini 1회 녹화 JSON → golden 재생, 신규 의존성 0·CI 무네트워크). `record_snapshots.py`(수동 recorder) + `snapshots/*.json`(실 Gemini 5개 녹화) + `test_translation_golden.py`(JSON 구조·카드당 길이·`llm.safety` 금지어/refusal 0·**밴드 방향 모순 부재[약한 계약, meaning.ts 임계 복제 0=§10]**·결정론) + `test_brief_golden.py`(Brief golden 부재 종결). 회귀 pytest marketpulse 200→**226(+26, 1 skip)**·마이그레이션 0·프로덕션 로직 무변경(테스트만). **본체 완결(S2~S5) + BOUNDARY-LLM 트리거(a) 충족 플래그**(차터 무접촉) |

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

## [보류·DORMANT] BOUNDARY-LLM — shared LLM 래퍼 정합 (형식 CLOSED·옵션 C / 실행 DORMANT)

> 형식 결정 = `DECISIONS.md [2026-06-18] BOUNDARY-LLM 통합 래퍼 형식 = 옵션 C`. 상위 트랙 = `[2026-06-18] Phase 1.5 Translation Layer` ①이 이연. (라벨 주의: shared 경계 청소 `BOUNDARY-1/2/3`(2026-06-04 종결)과 무관한 별개 트랙.)

- **상태**: 형식 CLOSED, 실행 DORMANT(trigger-gated). 타 세션 소관 — 본 큐에서 먼저 꺼내지 않음.
- **실측 갱신 (STEP 0, HEAD=`feb999b`)**: 통합 대상 = **27파일 / 9 surface**(차터·Translation 인용 "3곳" 무효화). provider 분포 **Gemini 24 : Anthropic 3 : OpenAI 0**.
- **트리거 (차터 §1 "4번째 소비처" 폐기 — 이미 27개로 충족)**:
  - **(a)** Translation 기능이 in-zone 단일출처(`apps/market_pulse/llm/`)로 안정 land 후 "깨끗한 1회 lift" 적기, OR
  - **(b)** escape 없는 신규 LLM surface가 추가되어 보안 회귀가 번질 때, OR
  - **(c)** burn-down 착수 결정 사이클이 별도로 열릴 때.
- **슬라이스 큰그림 (순서·점수는 착수 시 별도 결정)**:
  - ① `packages/shared/llm` 코어 신설 (소비처 0 · portfolio+market_pulse client 합성 · escape/CB/재시도 공통화 · IDENTICAL)
  - ② `korean_overview` 이관 (shared 내부, 최안전 in-zone)
  - ③ 외부-LLM-직접호출 **가드 신설** (코어 land 후 회귀방지 — 현재 가드 부재 = 규약 부채)
  - ④ surface별 점진 (escape 부재 큰 surface 우선)
  - ⑤ rag = **타 surface, 위임/코디** (한 세션에 밀지 않음)
- **착수 전 정정 필요 (2026-06-18 델타 측정)**: DECISIONS BOUNDARY-LLM "코어 베이스 #2" 지칭을 `apps/market_pulse/briefing/client.py` → **`apps/market_pulse/llm/client.py`** 로 정정. (커밋 `5104635`에서 추출·prompt 파라미터화된 정제분; briefing은 위임 잔류, 이 모듈이 정책층 베이스에 더 근접. slice ① "market_pulse client 합성"도 이 경로로 읽을 것.) → DECISIONS 본문 fold-in은 **다음 mgmt 터치 또는 트리거 착수 시**(지금은 메모만).
- **HALT 주의**: 27개 광역 → 한 세션 일괄 금지. cost ledger·BriefingLog·usage 모델 이관이 prod 마이그레이션 건드리면 `makemigrations --dry-run` 후 멈춰 보고.
- **완료정의 (burn-down)**: `packages/shared/llm` 존재 + 27소비처 전부 단일 경유 + 외부-LLM-직접호출 가드 신설 후 위반 0.

### [test 위생 보류] (a)-large stale LLM seam 청소 — 전용 세션 (2026-06-29 등록)
- `tests/news/test_news_deep_analyzer.py` 102e — `mock_genai` fixture 17곳 `.models.generate_content` 직접참조.
- `tests/csv_url_resolver` 계열 `TestLLMAnalysis` 4f — `_llm_client=MagicMock` dead + 3곳.
- 분류 (a) 확정, 프로덕션 정상(이미 이관 완료). mock 본문 재작성이라 기계적 범위 초과 → BOUNDARY-LLM ②③④ 후 전용 세션에서 처리. 동결 카운트 무관.

### [후속 슬라이스] #12 gemini astream 정규화 델타 이관 + #8 shim 제거 (2026-07-02 등록)
- ③b에서 `StreamDelta`/`StreamFinal` 정규화 델타 계약 + anthropic astream 신설 완료. gemini astream은
  #12 IDENTICAL 보존 위해 raw 청크 pass-through 존치(코어가 anthropic만 StreamFinal 인지).
- 후속: `llm_service.py`(#12 gemini stream) 소비처를 정규화 델타(StreamDelta/StreamFinal)로 이관 →
  코어 astream의 gemini 경로도 정규화 yield로 통일 → adaptive #8의 shim(코어 타입→dict) 제거 가능.
- **자기 IDENTICAL 게이트**(delta 시퀀스·usage·봉투 byte 동일). 동결 카운트 무관(이미 #12는 이관 완료 상태).

### [별도 트랙] FMP test-debt — LLM 경계 무관 (2026-06-29 등록)
- `FMP_API_KEY` 요구로 setup 실패 34건: chain_sight 13e · enhanced_screener 12e · provider_factory 9f.
- LLM 경계 무접촉(버킷A/FMP). BOUNDARY-LLM 범위 밖 — FMP/버킷A 위생 트랙에서 처리.

---

## 하네스 구조 개선 (HARN)

| ID | Task | Agent | Depends On | Status | Output Artifact |
|----|------|-------|------------|--------|-----------------|
| HARN-1 | 하네스 4문서(DECISIONS/PROGRESS/TASKQUEUE/common-bugs)의 **append 충돌 구조적 재발** — `.gitattributes merge=union` 적용 또는 세션별 로그 분리 검토 (별도 결정 사안) | orchestrator | - | **완료 2026-06-23** (`642306a`) | 2026-06-12 MAIN-SYNC 머지에서 4문서 전건 충돌 재발(양쪽 append 위치 겹침, 수동 해소). **해소: `.gitattributes`에 4문서 `merge=union` 적용**(`642306a`) → BOUNDARY-LLM consolidation 머지(`63194cd`)에서 DECISIONS/TASKQUEUE 충돌 0 자동 해소 실증(직전 merge-tree는 DECISIONS content 충돌 예측). union=양쪽 라인 보존, 육안검수로 중복 0 확인. 동반: common-bugs **#33 중복**(좀비 Beat ↔ fetch baseline, origin 비고가 예견) 채번 정리 |

---

## dashboard 트랙 보류 (STEP 0 / 2026-06-27)

> dashboard STEP 0 전수 조사 발견 — 전수 조사 단계라 보류, 사라지지 않게 등재. 근거: 보고서 sess-dashboard-step0 @ bbe6b1b.

| ID | Task | 분류 | 트리거(보류시) | Status |
|----|------|------|---------------|--------|
| DASH-TEST | eod 표면 프론트 테스트 0건 (STEP 0 실측 — `app/page.tsx` + `components/eod/**` + `hooks/useEODDashboard` + `services/eodService` 대응 vitest 0건) | dashboard 트랙 직접 | dashboard 표면에 실작업(리팩토링/레거시 정리)이 잡히면 **그 직전 슬라이스** | 🆕 보류 |
| DASH-LEGACY | `app/dashboard/page.tsx`(레거시 계정/네비 페이지, eod 무관) 운명 **KEEP/CUT/MOVE** | 결정 안건 | 전 트랙 STEP 0 완료 후 **일괄 KEEP/CUT 사이클** | 🆕 보류 |
| DASH-VIEWS-EOD | `views_eod` REST API(`/api/v1/stocks/eod/{dashboard,signal,pipeline}`) — 현 프론트 **미소비**(static `/static/signals/*.json`만 소비, 코드젠 타입에만 존재). 존치 vs 폐기 | 결정 안건 | **타 트랙이 이 API를 쓰는지 확인된 뒤**(병렬 경로 안전 폐기 판단 가능) | 🆕 보류 |
## chain_sight 트랙 발견 (STEP 0 / 2026-06-29)

> chain_sight STEP 0 전수 조사 발견 — 사라지지 않게 등재. 근거: 보고서 sess-cs-step0 @ b457bbf.

| ID | Task | 분류 | 트리거(보류시) | Status |
|----|------|------|---------------|--------|
| CS-EXT-API | `insider_tasks`→Finnhub, `sensitivity_tasks`→FMP **직접 `requests.get`**(shared 래퍼·CircuitBreaker 미경유 = 의존 방향 규약 위반) | 결정 안건(이관 설계) + shared 위임 가능 | 전수 조사 후 우선순위 사이클. **※ 행위보존 검증 필수 — 즉시 실행 금지** 📌 **로드맵 Phase 3 선결 조건**(D-ROADMAP-V1) | 🆕 보류 |
| CS-LEGACY | 레거시 serverless Chain Sight v1(`chain_sight_service`·`neo4j_chain_sight_service`·`supply_chain_*`·migr 0009) 흡수 vs serverless 잔류 | 결정 안건(경계) | 전 트랙 STEP 0 완료 후 일괄. 📌 **로드맵 Phase 3 선결 조건**(D-ROADMAP-V1) | 🆕 보류 |
| CS-LAZY | `apps/chain_sight`→`services.{validation,news,serverless}` lazy import 정리 방향(교차 트랙 결합) | 결정 안건(경계) | 동일(전 트랙 STEP 0 후 일괄) | 🆕 보류 |
| CS-CHOICES | `RelationConfidence.RELATION_TYPE_CHOICES` ↔ DB drift — `PARTNER_WITH`(53)·`DEPENDS_ON`(41) 미정의, `HAS_THEME`·`HELD_BY_SAME_FUND` 0행 | **chain_sight 트랙 직접** | chain_sight 실작업 슬라이스 | 🆕 보류 |
| CS-TEST | EventBoard/Ranking 테스트 5건 404(`theme_tags` 플래그 OFF ↔ EventGroup 보드 기대, 라우트는 등록됨) | chain_sight 트랙 직접 | 동일(chain_sight 실작업 슬라이스) | 🆕 보류 |

---

## market_pulse + portfolio 트랙 발견 (STEP 0 / 2026-06-29)

> MP STEP 0(sess-mp-step0) + PF STEP 0(sess-pf-step0) 발견 — 사라지지 않게 등재.

| ID | Task | 분류 | 트리거(보류시) | Status |
|----|------|------|---------------|--------|
| MP-FMP-WEIGHTS | `fetchers/fmp_weights.py` raw `requests.get` → FMPClient 경유 통일 (※ **CircuitBreaker는 이미 경유** — 코드 일관성만, chain_sight CS-EXT-API와 급이 다름) | market_pulse 트랙 직접 | market_pulse 실작업 슬라이스 (시급도 낮음) | 🆕 보류 |
| MP-BREADTH-SRC | breadth/concentration **생산(`services.serverless`) ↔ 소비(market_pulse 모델)** 소관 명확화 | 결정 안건(경계) | 로드맵 재검토(Phase 2 촉발 데이터 연계, MP2-DATA-BREADTH-CONC). 📌 **로드맵 Phase 2 촉발 데이터 소관**(D-ROADMAP-V1) | 🆕 보류 |
| MP-NEWS-LAZY | `services/news_aggregator`→`services.news.providers` lazy import 정리 | 결정 안건(경계, news 공통) | 로드맵 재검토 | 🆕 보류 |
| PF-TEST | coach 테스트 **실측 43건**(큐 "5건" 과소평가) `mock.patch("portfolio.…")`·parametrize 문자열 + 경로 오프셋 `parents[2]→[3]` 수정(PR7 이관 후 stale). **✅ 완료** `monorepo/sess-pf-test`(cea40c9 문자열 31건 + e46bb97 오프셋 12건) — pytest apps/portfolio **43 failed→567 passed**(2026-07-13, `pytest apps/portfolio -q --maxfail=1000`), 회귀 0, 로직 회귀 0(전부 이관 잔재), architecture 7 passed. cost_guard 로거명/경로 데이터 3건은 stale 아님→무접촉 | portfolio 트랙 직접 | 완료 2026-07-13 | ✅ 완료 |
| SLICE18-CONTAINER | Slice 18 사용자 상태 그릇. STEP 0 HALT(원안 4모델 중 WalletHolding·WatchlistItem 중복+D1 전제 파기) → 디렉터 재설계(18-R). **✅ 18-R 완료(2026-07-13)** `monorepo/sess-slice18r-container`(base `8dd5ca9`, Part A~F). 신규 **2종만**(UserGoal `user` OneToOne·CashBalance `wallet` OneToOne, D2' house 컨테이너경유 정렬, ScopedManager.for_user)·migration 0002(신규 2 CreateModel만·기존 13 무접촉·--check clean)·services/my_container CRUD·격리 테스트(파라미터라이즈드 누수-0+등록가드+재사용 스모크). WalletHolding·WatchlistItem 재사용(생성 0). **pytest 574→582**(신규 8, 기존 깨짐 0)·architecture 7·health 12✅. 원안 지시서 rev2 교체+REUSE_WIRING. 미push | portfolio 트랙 | 다음=19a(목표대비 권유 엔진) | ✅ 18-R 완료 |
| SLICE18R-CARDINALITY-REVISIT | 18-R의 `OneToOne` 카디널리티 가정 2건 재검토(굳기 전). **CashBalance⇔Wallet OneToOne = 단일통화 현금만 표현** — **19a STEP 0에서 Wallet 통화 모델 실측** → 다통화 현금(예: KRW+USD) 보유/필요 시 **CashBalance를 `FK(Wallet)`+`unique(wallet,currency)`로 전환** 결정. **UserGoal⇔User OneToOne = 단일목표 MVP** — 다중목표(은퇴/주택 등) 필요 여부 함께 확인. prod 미적용(0002 dev만)이라 되돌림 가능. **이 트리거 미해결 시 19a는 카디널리티 확정 없이 진행 금지** | portfolio 트랙 | **19a STEP 0에서 강제 처리**(Wallet 통화 모델 실측 기반) | 🔶 재검토 트리거 |
| PF-LEGACY-FE | `app/portfolio`·`components/portfolio`·`services/portfolio.ts`(레거시 `users.Portfolio` 소비) 귀속 = portfolio 트랙 vs users·auth 표면 | 결정 안건(경계) | 로드맵 재검토(서비스 플로우 "포트폴리오 변화" 표면 연계). 📌 **로드맵 후속 phase**("포트폴리오 변화" 표면, D-ROADMAP-V1) | 🆕 보류 |
| PF-SCORING | `tests/scoring/**` 소속 확정(coach scoring — 소유권 지도 "[경계 보류]" 해소) | 결정 안건(경계) | 로드맵 재검토 | 🆕 보류 |
| PF-LLM-CLIENT | `apps/portfolio/llm/client.py`(anthropic·google.genai 직접) → `packages/shared/llm` 코어 합성 | 타 트랙 위임(BOUNDARY-LLM, portfolio+market_pulse client 합성) | BOUNDARY-LLM 트랙 작업 시 | 🆕 보류 |

---

## B-1 FRED 백필 트랙 처분 (STEP 0.5 / 2026-06-30)

> B-1 깊은 FRED 피처 백필의 STEP 0.5 게이트 결과 등재. 근거: DECISIONS D-B1-SCOPE-DEPTH. B-1 전 사이클 prod 쓰기 0(읽기전용).

> 🏁 **B-1 트랙 종결 보고(MGMT-BATCH-9 실측 정합, 2026-07-13, base origin/main `3b50612`)**: **B-1 코어 트랙 전건 종결 = origin/main에 완전 반영**. 실측 검증: `ef312d6`(S1 백필 land)·`307306d`(S2)·`b45ee1f`(TREND-S4) **전부 origin/main 조상**(머지됨), `monorepo/sess-b1-s2` tip `97f11d2`도 조상(머지됨). **잔여 슬라이스 = 0**(B1-S1 백필+Part4 통과·B1-S2 703행 합성+Part4 통과·B1-S2-FIRE 발화 완료). **두 언락 키 전부 발화**: ⑴ **MP2-ANALOG un-dorm**(D-ANALOG-GATE (a)(b) 충족, 착수 가능) ⑵ **MP2-TREND S4 land + 트랙 재종결**(`b45ee1f`). deferred 잔존 = B1-DEFER(Phase 5 재개 대기)·B1-C2(마이그레이션 결정 사안)·B1-OPS-BEAT(별도 ops 트랙) — B-1 코어와 무관. ⚠️ **stale 전제 정합화**: BATCH-9 지시서는 "ef312d6=s1-fix land, sess-b1-s2 **활성**"을 전제했으나, 실측 origin/main(`3b50612`)에서 s2·FIRE 모두 이미 종결 — 지시서 작성 이후 origin/main 전진(reference lesson: origin/main 세션 중 반복 전진). 종결 보고 요청은 본 실측으로 **자기충족**(별도 보고 세션 불요).

| ID | Task | 분류 | 트리거(재개) | Status |
|----|------|------|-------------|--------|
| B1-DEFER | B-1 FRED 깊은 백필 → Phase 5 Analog 설계 산하로 defer. 사유: 현행 소비자 0(Analog 미구축) + full-vector cap 미해결(조인트 벡터 깊이가 최단 시리즈 HY OAS 2023-06-30에 묶임). 확정 범위·깊이 = A1(활성 11)+B3(2018-01-01). 참조 D-B1-SCOPE-DEPTH. **★착수 STEP 0 필수(2026-07-09 SECTOR-CD S3 추가)**: momentum floor-0 초기 구간 식별·소급 처리 방침 결정 — 계산기가 룩백 부족 구간 momentum을 0으로 floor(SectorFlowSnapshot 초기 5 distinct일 위장), 가짜 0이 소급 차트·cd_state 분석 오염 방지(SECTOR-CD S3 STEP 0-2는 초기 5일 제외로 회피) | market_pulse 트랙(Phase 5 산하) | **Phase 5에서 Analog 매칭 방식(full-vector vs ragged) 확정 시 재개** | 🆕 보류 |
| B1-C2 | C2 처분: (a) PCEPI deprecate(활성 소비처 0), (b) 오라벨 2종(VIX3M·MOVE) data_source 'fred'→'yahoo' 정정. prod DB 필드 변경이라 유보. 참조 D-B1-SCOPE-DEPTH | 병진 수동 | 병진 승인 | 🆕 **보류 확정(B1-S1 STEP 0-5)** — 정정엔 `data_source` choices에 'yahoo' 추가 = 마이그레이션 필요(규칙 #3 HALT). **백필 전제 아님**(data_source=EconomicIndicator 시리즈당 1행, 값 백필이 라벨 증식 0). 별도 마이그레이션 결정 사안 |
| B1-OPS-BEAT | ops: 레거시 경제지표 beat 죽은 정황 — `update_economic_indicators`(celery.py:184)가 FEDFUNDS/UNRATE/CPIAUCSL 1개월 stale(#28 DatabaseScheduler가 dict beat_schedule 무시 패턴). PCEPI 포함 레거시 beat를 한 항목으로 트리아지(piecemeal 금지). B-1과 무관한 ops 트랙 | ops 트랙 직접 | ops 사이클 | 🆕 보류 |
| B1-STEP0 | **STEP 0 전수 실측 완료 (2026-07-09, 읽기전용·FRED 11콜 메타만·DB 쓰기 0, `monorepo/sess-b1-step0` base `e8ffedc`)**. 핵심: ⑴ regime 14지표 = 11 매크로(전부 EconomicIndicator, data_source=fred 라벨) + 3 SPY파생(MarketIndexPrice). ⑵ **FRED obs_start**: NFCI×4=1971-01-08(weekly), **HY pair BAMLH0A0HYM2/H0A3HYC=2023-07-10(daily)=조인트 천장**, T10Y2Y=1976, T10Y3M=1982, VIXCLS=1990. **VIX3M·MOVE=FRED 400(시리즈 아님)→실소스 yfinance `^VIX3M`/`^MOVE`**(현 DB 2026-02-02~, data_source 오라벨=B1-C2). ⑶ 소급경로: FRED 9종=get_series_observations, VIX3M/MOVE=yfinance --period, SPY=yfinance OHLCV → **소급 불가 지표 0**(단 깊이 상이, 조인트 완전벡터 천장=최단 실백필 깊이). ⑷ 완전벡터 **23행**(coverage≥0.999, 2026-07-09 최신, 구 22→23). ⑸ RegimeSnapshot 65행/unique[(date,)]/intraday전용/마이그레이션 불요(과거일 삽입=서빙창 필터). ⑹ **momentum floor-0 = 06-29 XLF 단 1행**(B1-DEFER의 "초기 5일 위장" 가정 **반증** — 초기일 실값 보유). **M8**: 07-09 이후 신규 거래일 **0개**(반전율 미측정, 시뮬 서빙앵커 0.1776 병기). **M9**: health_check 12→11은 항목 제거 아님 = OK/WARN 집계 차(당시 '실행 트리 정합' WARN, `f084cd6`/`ad3ae77`/`04a5b61`서 항목 추가만, 현 13항목). | market_pulse 트랙 | **범위 결정 세션 대기(디렉터)** — full-vector vs ragged·깊이(HY 2023-07-10 vs VIX3M/MOVE yahoo 실깊이)·floor-0 방침·M7 선택지 | ✅ **STEP 0 완료** |
| B1-S1 | 원시 시리즈 백필 (깊이 A 조인트 천장 **2023-07-10**, D-B1-SCOPE). 대상 = FRED 9(NFCI×4·HY×2·T10Y3M·VIXCLS·T10Y2Y) + yahoo 2(VIX3M·MOVE) + SPY OHLCV. 경로 = `backfill_v2_a1 --from 2023-07-10`(창·멱등·FREDClient 단일). 신규 커맨드 0, 스키마 무변경 | market_pulse 트랙(병진 수동 실행) | **병진 수동 백필 실행 대기(재실행)** → 실행 후 Part 4 검증 | 🔵 **장애 triage 종결(2026-07-10)** — 1차 실행서 FRED 전건 0행(Yahoo 3종 정상). 원인=`_fetch_fred`가 get_series_observations limit 미override(기본 100·desc→최신 100건 기존행만→skip). 수정 land(`7759265` limit=100000·asc + fetched/inserted 로깅, `edc25fc` 테스트, common-bugs 2건). 인증·CB·환경 무관. **병진 재실행 = 원 4개 명령 그대로**(멱등, Yahoo 3종 이미 완료분 skip). ✅ **백필 완료·Part 4 검증 통과(2026-07-10)**: 전 daily 시리즈(HY×2·T10Y2Y·T10Y3M·VIXCLS·VIX3M·MOVE·SPY) 최초일 **2023-07-10 정확 도달**(+0일), NFCI×4만 +4일(주간 금요일 구조=정상). 창내 행: HY 787·T10Y2Y/3M 750·VIXCLS 774·VIX3M 753·MOVE 748·SPY 768·NFCI 156(주). +갭(T10Y2Y +35 등)=휴장일(정상). **DGS10/DGS2 각 +507행**(후보리포트 skip 예측 벗어남 — 기본목록 경유 심화, 실 FRED·무해). 원시 14/14 가용=**150 영업일**(=금요일), 10/14=599일(NFCI×4 비-금요일 결측=S2 forward-fill 대상). NFCI 전 156행 **금요일**. **다음=B1-S2**(주간 forward-fill 정렬 + 14벡터 소급 합성 + rules.yaml 소급) |
| B1-S2 | 벡터 소급 합성 (D-B1-SYNTH) = **현행 로직 as_of 매개변수화**(별도 forward-fill 발명 없음 — max_age 캐리가 주간 NFCI 정렬 자연 수행) + 시계열 순차 hysteresis chaining + rules.yaml 소급 적용(과거 국면 재구성, D-ANALOG-GATE 원문 경로). S1 백필 land 의존 | market_pulse 트랙(커맨드 land=Claude Code / 합성 실행=병진 수동) | 커맨드 land(`60e9083`) → 병진 실행(2026-07-10) → Part 4 통과 | ✅ **트랙 종결(B-1 종결, 2026-07-10)** — 병진 합성 완료: **703행**(2023-07-10~2026-04-24)·완전벡터 **683**·분포 TRANSITION469/LATE_BULL228/CRISIS6. **Part 4 전건 통과**: 라이브 66행 불변(2026-04-27~07-10)·겹침0·total 769(66+703)·leading gap 정직(07-10 cov0.500 INSUF/07-11~13 cov0.643 OK)·**멱등 prod 확증**(재-dryrun synth0/skip703, 경계 붕괴 없음) |
| B1-S2-FIRE | **B-1 트랙 종결 발화(완료)** — 병진 합성 + Part 4 통과로 발화: ⑴ **MP2-ANALOG un-dorm** — D-ANALOG-GATE 트리거 (a)(b) 동시 충족(비-LATE_BULL 475일·CRISIS 6·완전벡터 683 재구성 검증 통과). ⑵ **MP2-TREND S4 동면 해제**. | market_pulse 트랙 | 발화 완료(2026-07-10) | ✅ **발화 완료** |

---

## Phase 1 제시 로깅 (STEP 0 / 2026-07-01)

> dashboard Phase 1 제시 로깅 STEP 0(sess-dash-p1-log) 발견. 근거 DECISIONS "[2026-07-01] Phase 1 제시 로깅 STEP 0"(D-P1-STEP0).

| ID | Task | 분류 | 트리거(보류시) | Status |
|----|------|------|---------------|--------|
| P1-REC-PROD | 추천 생산 방식 결정 — **EOD-bake 확장**(shared/stocks) vs **뉴스추천 승계**(services/news). 이게 제시 로그 스키마(signal_tag/horizon)·confidence 출처·impression write 경로를 확정 → 선결 결정 | 결정 안건 | ~~다음 결정 사이클~~ | ✅ **해소 (D-P1-RECPROD, 2026-07-02)** — EOD-bake 확장 + Baked impression + confidence v1 결정식. 실행은 shared/stocks 위임 대기 |
| P5-EXCESS-BACKFILL | `SignalAccuracy.excess_{h}d`(SPY 상대) 백필 — prod 3,611행(~12%)만 채워짐 vs return 29,962. **벤치마크 상대 채점 채택 시 선결**(raw return 채점은 즉시 가능하므로 조건부) | 트랙 위임(shared/stocks) | Phase 5 벤치마크 상대 채점 채택 시 | 🆕 보류 |
| HC-MARKER-TREADMILL | health_check "origin/main 해시" 마커가 **매 mgmt 머지마다 lag=1**(커밋이 자기 머지-후 해시를 스스로 못 적는 구조적 한계). 현재 tolerance N=3가 흡수해 대개 green이나, 마커 3커밋+ 미갱신 시 붉어짐(이전 STEP 0 세션 시작 시 실제 red 이력). **임시 규율**: 매 mgmt에서 마커를 현 origin/main으로 갱신해 lag=1 clean 유지(누적 방지). **durable**: health_check가 "메타-only·lag=1" 시그니처를 허용하도록 수정(하네스 코드 = 별도 슬라이스). **📌 보강(2026-07-02 preflight)**: N=3 tolerance가 lag=1을 흡수 재확인(5d35fa7 마커=3d670ed=HEAD~1 green). ❌는 lag>3에서만 발현 추정 → **durable 긴급도 하향**, 우선 tolerance 경계 문서화. | 하네스 개선(HARN) | durable = 하네스 코드 슬라이스(긴급도↓) / 임시 = 매 mgmt 상시 | 🆕 등재(임시 규율 상시 적용) |
| DASH-FE-GLOB | frontend 실경로 = `frontend/app/page.tsx`(≠ 소유권 글롭 `app/dashboard/**`, 레거시 계정 페이지) 재확인 → 소유권 지도 v2 **실경로 반영**(dashboard 불일치-A 후속) | mgmt | 다음 mgmt(급하지 않음 — 이미 D-P1-STEP0·소유권 지도에 사실 기록됨) | 🆕 보류 |
| P1-BUILD | 병합 스키마(**D-SCHEMA 9필드**)로 **발행 로그 모델 신설**(SignalAccuracy 형제, `packages/shared/stocks`) + **baker `recommend`/`thesis`/`carousel` 필드 add**(dashboard.json 추천 계약 서빙). 빌드용 worktree 브랜치 `monorepo/sess-p1-recprod`. **게이트**: 순수 add(dry-run `No changes` 기저 확인됨)·IDENTICAL(기존 6키 signal_cards 행위보존)·회귀 green·**write 표면 0**(serve 무변경). grain=`(stock,signal_date,signal_tag)`(D-P1-GRAIN) + confidence=formula v1·conf_ver=1(D-P1-CONF). **선결 결정 4종 완비**(참조 D-P1-RECPROD·D-SCHEMA·D-OWN·D-P1-GRAIN·D-P1-CONF) + 정렬·계약 확정(D-P1-REC-RANK·D-P1-REC-CONTRACT). **✅ land `1995f93`**(IssuanceLog 0009 순수 add + baker recommendations additive + 발행로그 write). 완료 근거: 게이트 전건 통과(순수 add·IDENTICAL·회귀 142 green·write표면0·구획 clean·health ✅) + `deece55` 위 rebase clean(4파일 무충돌) → **ff push `deece55..1995f93`**. 첫 실파이프라인 관측은 P1-OBSERVE(후속) | 트랙 위임(shared/stocks · **dashboard 디렉션** D-OWN) | 완료 2026-07-03 | ✅ 완료 |

---

## Phase 2 촉발(제품 로드맵) — ②Viewed defer (2026-07-02)

> 로드맵 Phase 2 촉발 두 축 중 ②만 defer(①촉발 표면화는 즉시 착수). 근거 DECISIONS D-MP2-SEQ. ※ 내부 MP2-ANALOG/MP2-ALERTS 트랙(TASKQUEUE 상단 'market_pulse v2 Phase 2 로드맵')과 **별개** — 라벨 충돌 주의.

| ID | Task | 분류 | 트리거(재개) | Status |
|----|------|------|-------------|--------|
| MP2-VIEWED | ②Viewed enrichment(per-user impression, `presented_as='viewed'`) → **defer**(drop 아님). 사전 조율: 발행 로그에 필요한 필드(`user_id`·`signal_date`·`ticker`·`horizon`·`presented_as`) 요구를 dashboard 세션에 전달. 참조 D-MP2-SEQ | Phase 2 촉발 ② | **Phase 1 발행 로그(shared/stocks) 스키마 land 시** | 🆕 보류 |
| P2-VIEWED-TABLE | **Viewed 별도 테이블 신설**(`presented_as='viewed'` 경로) — **D-SCHEMA의 baked/viewed 분리 결정 후속**. 발행 로그에서 `presented_as` 컬럼을 뺀 대가로, 노출 수준 채점은 이 테이블 join으로 복원(Phase 5). MP2-VIEWED enrichment의 **물리 저장소 스텁**(형제 항목). 참조 D-SCHEMA | Phase 2 촉발 ②(물리 스텁) | ✅ **P1-BUILD land(`1995f93`) 충족** — 잔여 트리거 = Phase 2 진입 결정(별건) | 🆕 트리거 충족·Phase 2 대기 |
| P2-IMPRESSION-BUILD | **ImpressionLog 축 구현**(D-P2-IMPRESSION 실체화 — "봤다"=뷰포트 50%×1초 IntersectionObserver, serve-time 로그, #43 경계 = IssuanceLog 무변경). **슬라이스 예정**: S1 shared 스키마(모델·마이그레이션) → S2 API 수신 엔드포인트 → S3 프론트 훅·표면 연결(5초 flush + visibilitychange/sendBeacon). **구획 메모**: S1·S2 = shared/백엔드 구획, S3 = dashboard 구획 — 슬라이스별 지시서에서 소유권 지도로 확정. **build 지시서는 본 등재 완료 후 별도 발급**(등재→build 규율) | S1·S2 @backend(shared)·S3 dashboard FE | Phase 2 진입·build 지시서 발급 시 | 🆕 **대기**(등재 완료·build 미착수) |
| P1-OBSERVE | 첫 EOD-bake 실행 후 **실파이프라인 관측**. **✅ 충족 2026-07-04**(D-P1-OBSERVE-DONE): JSON recommendations N=10·6키 IDENTICAL + DB IssuanceLog 10행=N·grain 중복 0(멱등 실증)·conf_ver=1·published_at·user_id null·매도 30%. 결함 2건(워커 표류·0009 미적용) 경유 해소 | 관측(dashboard 디렉션) | 완료 2026-07-04 | ✅ 충족 |
| P1-B-WORKER-WORKTREE | **worker 전용 worktree**(`~/worktrees/sv-worker-runtime` detached origin/main) + `celery-worker.sh` PROJECT_DIR/plist + 심링크(방향 반전 방식 Y) + `scripts/worker_sync.sh` 신설 — 브랜치 표류 트레드밀 종료. **✅ 완료 2026-07-05**(OPS-B-BUILD): 스크립트 land `921dc0c`, 검증 bake 2회(심링크 생존·6키 IDENTICAL·N=10·IssuanceLog 10행 멱등·HTTP 200). 심링크 방향 반전 = D-B-WORKER-AMEND-1 | ops/infra | 완료 2026-07-05 | ✅ 완료 |
| B-HARDEN-OUTPUT | (휴면) baker `OUTPUT_DIR` **env override** 추가 — 심링크 의존 제거. 트리거: **worker 트리 이전 또는 다중 출력 필요 발생 시**. 현재는 심링크(방식 Y)로 충분 | ops/infra(휴면) | worker 트리 이전·다중출력 시 | 💤 휴면 |
| B-CLEANUP-PREB | `frontend/public/static/signals_pre_b`(B′ 전환 전 백업) **제거**. 트리거: **정상 거래일 자동 beat 1주기(월~금) 무결 통과 후**. **카운트 5/5 도달**(7/6·7/7·7/8·7/9·7/10 전 행 무결 bake). **제거 완료**: 대상 = 5.0M·Desktop 트리·미추적(git 무관)·DB 무관(정적 백업 디렉토리) — STEP 0로 대상 실체 확정 후 **사용자 수동 rm 완료**(2026-07-13, MGMT-BATCH-9). Phase 1 잔여 0 해소의 한 축(D-P1-CLOSE) | ops(정리) | 5/5 발화 → 제거 완료 | ✅ **종결 (2026-07-13)** |
| P1-HC-ISSUANCE | 발행 로그 감시 = **C 계층**(D-HC-ISSUANCE): ⑴ bake 자가검증 ⑵ health_check 최소. **✅ done `2e3b91e`+`ad3ae77`(HC-BUILD)** — 회귀 155·migration 0·실관측 통과(07-08: issuance_verified 10/10 ok·검문소 07-07 행10 OK·무경보). 짝 = common-bugs #46 | ops(health_check) | 완료 2026-07-08 | ✅ done |
| P1-RUNBOOK-MIGRATE | 운영 절차(runbook): **land에 migration 포함 시 운영 DB `migrate`를 배포 단계로 명시**. 0009 미적용 재발 방지 | ops(docs) | 착수가능 | 🆕 등재 |
| P1-TAG-VOCAB | 검증: **signal_tag 어휘 대조** — 실데이터 관측치 `S2`가 등록 태그 집합에 속하는지 + D-P1-GRAIN 표기(V1/P2/S1 예시)와 대조. 불일치 시 장부 표기 정정 안건화(결정 무효 아님, 예시 표기 갱신) | 검증(read-only) | 착수가능 | 🆕 등재 |
| P1-BEAT-PRECHECK | ~~월요일 beat 전 공유 트리 re-detach 점검~~ **✗ 폐기 2026-07-05** — B′ 완료로 목적 소멸. 워커가 공유 트리 **비의존**(전용 worktree + worker_sync.sh)이라 공유 트리 표류가 bake에 영향 없음 | — | — | ✗ 폐기(B′ 완료) |
| CAROUSEL-BUILD | dashboard 추천 캐러셀 A+ 구현(components/eod + page.tsx, D-P1-CAROUSEL). **✅ 완료 2026-07-06**(land `24b0e47`): RecommendationCarousel+Card·types/eod Recommendation·Level 2.5 배선, vitest 7·tsc 0·하위호환 고정·shared 무접촉. ⚠ 화면 도달은 W′ 완료 시 | dashboard FE | 완료 2026-07-06 | ✅ 완료 |
| W-BUILD | **web 전용 서빙 worktree**(`~/worktrees/sv-web-runtime`) + next dev(:3000) 서빙 대상 전환 + `worker_sync.sh` 공통 동기화 확장 + node_modules `npm ci` 설치. **✅ 완료 2026-07-06**(OPS-W-BUILD, D-W-WEB-AMEND-1): 대상 정정(com.stockvis.web=daphne 오지목→next dev), worker_sync.sh land `75cb4d3`, 검증(:3000 web 서빙·bake 통주·공유 트리 무접촉·실화면 캐러셀 렌더). #45 web 판 해소 | ops/infra | 완료 2026-07-06 | ✅ 완료 |
| W-HARDEN-BUILD | (휴면) dev server → `next build`/`next start` 전환 검토. 트리거: **외부 노출 또는 성능 문제 발생 시**. ※ W-HARDEN-LAUNCHD와 한 안건 통합 검토 | ops/infra(휴면) | 외부 노출·성능 문제 시 | 💤 휴면 |
| W-HARDEN-LAUNCHD | (신규) next dev **데몬화**(현재 수동 `nohup`, 재부팅 시 수동 재시작 필요) — W-HARDEN-BUILD(next build/start 전환)와 **한 안건 통합**. 트리거: **재부팅 후 화면 다운 경험 또는 외부 노출** | ops/infra(휴면) | 재부팅 다운·외부 노출 시 | 💤 휴면 |
| DAPHNE-RUNTIME-SURVEY | (신규, read-only) daphne(`com.stockvis.web`, :18765)의 **공유 트리 결합 실측**(#45 세 번째 인스턴스) → B′/W′ 패턴을 daphne로 확장할지 결정 입력. **✅ 완료 2026-07-06** — 실측 입력으로 D-DAPHNE-RUNTIME 확정(마진 1.80). daphne는 API 관문이라 표류 시 백엔드 응답 자체가 구코드 = 피해 최대 | ops(조사) | 완료 2026-07-06 | ✅ 완료 |
| DAPHNE-BUILD | **daphne 전용 서빙 worktree**(`~/worktrees/sv-api-runtime` detached origin/main) + 기동 스크립트 PROJECT_DIR 전환 + `scripts/worker_sync.sh`에 daphne 추가. **✅ 완료 `803e9a9`** — baseline 전후 일치·CWD api트리·WS 101·:3000 200·공유 트리 무접촉. 런타임 3종 격리 완결. #45 세 번째 인스턴스 해소 | ops/infra | 완료 2026-07-06 | ✅ 완료 |
| DAPHNE-GRACEFUL | (휴면) daphne 재기동 시 WS 연결 끊김 → graceful reload. 트리거: **재기동 끊김이 실사용 불편으로 관측 시** | ops/infra(휴면) | 재기동 끊김 관측 시 | 💤 휴면 |
| CAROUSEL-COLOR-REVIEW | 캐러셀 방향 색 크로스-화면 정합 판단. **✅ 결정 완료 2026-07-06** → D-COLOR-SYSTEM(앱 표준 = 한국축: 상승·매수·긍정 rose / 하락·매도·부정 sky, sectorColor.ts 정합). 캐러셀 현행 emerald=매수는 Stage 1(COLOR-STAGE1)에서 rose=매수로 전환 예정, 과도기 반전 명시·수용 | dashboard FE(디자인) | 완료 2026-07-06 | ✅ 결정 완료 |
| COLOR-STAGE1 | **dashboard 구획 한국축 전환** — `components/eod` 로컬 `colorSemantics.ts` 도입, 방향성 색을 D-COLOR-SYSTEM(rose=긍정/매수·sky=부정/매도)으로 통일. **✅ 완료 `3a4706f`**(colorSemantics.ts 신설 + 6컴포넌트, tsc0·vitest509, 실화면 검수 통과 07-06) | dashboard FE | 완료 2026-07-06 | ✅ 완료 |
| COLOR-STAGE2-chain_sight | chain_sight 방향성 색 한국축 전환(EventRanking·MetricCell 등). **✅ 완료 `9fe326f`**(자기 구획 로컬 시맨틱, import 금지 준수) | 트랙 위임 | 완료 2026-07-07 | ✅ 완료 |
| COLOR-STAGE2-market_pulse | market_pulse regime/flow `meaning.ts` 한국축 전환. **✅ 완료 `3253cd1`(merge `9169ea9`)** — CRISIS→sky(라벨 보존)·FLOW_TONE 디커플링·잔여 rose 오버로드 2건 수용(DECISIONS 판정 기록) | 트랙 위임 | 완료 2026-07-07 | ✅ 완료 |
| COLOR-STAGE2-portfolio | portfolio 수익=rose/손실=sky 전환(PortfolioSummary·Table·Chart·Modal·RealtimePortfolio **5파일 글로벌축 잔존**). **💤 보류 확정**(D-COLOR-SYSTEM 추기) — 트리거 = **portfolio 트랙 재개 시 그 첫 슬라이스에 선행**(별도 색 슬라이스 신설 대신 흡수). D-COLOR-TOKEN에 따라 재개 시 shared 토큰 **직소비**(로컬 경유 없음) | portfolio FE | portfolio 트랙 재개 시 | 💤 보류 |
| S3-COLOR-ALIGN | MP2-TREND S3 z-score 멀티라인과 market_pulse 색 시맨틱 겹침 조율. **✅ done** — `CUT_STROKE.CRISIS = HEX_SIGNED` 소비 정합(regime 색 한국축 일치 확인) | market_pulse FE | 완료 2026-07-09 | ✅ done |
| COLOR-WARN-SCHEME | (휴면) rose 의미이동(위기→긍정)으로 발생한 **잔여 rose 오버로드 정리** — 경고/위기 표현을 색 아닌 별도 수단(아이콘·채도·라벨)으로 완전 분리. 트리거: 잔여 rose 오버로드가 실사용 오독으로 관측 시. 참조 D-COLOR-SYSTEM 판정 기록 | FE(디자인) | 오독 관측 시 | 💤 휴면 |
| COLOR-TOKEN-PROMOTE | `colorSemantics` shared 토큰 분할 승격(D-COLOR-TOKEN). **✅ done `694d6f5`** — components/common/colorSemantics.ts 신설(14 export, DIRECTION_HEX 축분리 D-COLOR-TOKEN-AMEND-1) | FE(shared) | 완료 2026-07-09 | ✅ done |
| TOKEN-RECLAIM-eod | eod 로컬 → shared 토큰 회수. **✅ done `d70d665`**(6소비처 전환·로컬 삭제, DIRECTION_HEX→HEX_CHANGE, tsc0·색단언 무수정 green) | dashboard FE | 완료 2026-07-09 | ✅ done |
| TOKEN-RECLAIM-market-pulse | market-pulse-v2 로컬 → shared 회수. **✅ done `8194fd7`**(DIRECTION_HEX→HEX_SIGNED, 행위보존) | market_pulse FE | 완료 2026-07-09 | ✅ done |
| TOKEN-RECLAIM-chainsight | chainsight 로컬 → shared 회수. **✅ done `c9310fb`**(순수 import swap, 행위보존) | chain_sight FE | 완료 2026-07-09 | ✅ done |
| SYNC-ENTRYPOINT | repo 스크립트 실행 고정 진입점(D-SYNC-ENTRYPOINT) = 래퍼 `~/bin/sv` + 자기가드. **✅ done `942a991`·`f084cd6`** — stale abort·health WARN·sv health 12/12·3종 트리 일치 실증. #47 구조 해소 | ops/infra | 완료 2026-07-09 | ✅ done |
| VERIFY-SUITE-BASELINE | full-suite 140 거짓 red 규명(검증 세션, 쓰기 0). **✅ done(판정 a — 환경 아티팩트)** — 격리 npm ci·v22.19.0에서 519/519 green(심링크 실패 파일 실설치 전건 통과). #48 실증 | @qa | 완료 2026-07-09 | ✅ done |
| TEST-ENV-POLICY | full-suite 게이트 환경 정책 결정. **✅ done** — D-TEST-ENV 등재(이원 정책 A)로 종결 | @qa | 완료 2026-07-09 | ✅ done |
| TEST-ENV-GUIDE | (신규, 소형 ops) `sv health`(또는 health_check)에 "**full-suite 전 npm ci 격리 확인**" 안내 추가. 참조 D-TEST-ENV | ops/infra | 트리거: 다음 ops 접점 | 🆕 등재 |
| THEME-HEAT-AUDIT | (신규) 공유 트리 세션의 **메타 직접 편집 흔적** + node_modules **심링크 오염 관여**(#48 원인 환경) 확인 — 4턴 이월 중이므로 큐 등재로 고정 | chain_sight 트랙 | 트리거: chain_sight 다음 접점 | 🆕 등재 |

---

## Phase 2 촉발 표면 구현 (MP2-SURFACE / 2026-07-02)

> D-MP2-SURFACE 확정(B 독립화면 + 변형1 위계). 근거 DECISIONS D-MP2-SURFACE.

| ID | Task | 분류 | 트리거 | Status |
|----|------|------|--------|--------|
| MP2-SURFACE | market-pulse-v2를 **변형1 위계**(regime hero + 국면별 판단 카피 + 촉발 카드 + 섹터 히트맵 + prose)로 재구성. **기존 breadth/concentration/brief 카드 행위보존**(떨어뜨리지 말 것). 국면별 판단 카피 = 정적 테이블(LLM 미사용). 참조 D-MP2-SURFACE | market_pulse 트랙 직접 | 구현 STEP 0 후 착수 | 🆕 착수가능 |

---

## MP2-SURFACE 잔여 (2026-07-02)

> MP2-SURFACE land 후 잔여. 근거 DECISIONS D-MP2-SURFACE / PROGRESS 2026-07-02.

| ID | Task | 분류 | 트리거 | Status |
|----|------|------|--------|--------|
| MP2-SECTOR-COLOR | 섹터 색 관례 불일치 — 신규 `SectorHeatmap`=상승 빨강(한국) vs 기존 `SectorCardSummary`/`SectorDetail` 드로어 `sectorFlow`=상대강세 녹색(서양). 같은 섹터가 요약↔상세 다른 색 → 혼란. 전면 한국 관례 통일(사용자 #1 한국). **완료** — sectorColor.ts 단일유틸(상승 rose/하락 sky) 4컴포넌트 통일, 요약↔상세 뒤집힘 0 | UI 결정+FE | — | ✅ **done (5459bce)** |
| MP2-SECTOR-SENSE | 섹터 요약이 히트맵으로 교체되며 sector 한국어 sense(TranslationLog) 미표시(translation_fallback 4→3). Brief prose는 유지. **완료** — SectorHeatmap에 selectSense sector sense 한 줄 복원(SenseNote, 없으면 미렌더) | FE | — | ✅ **done (5459bce)** |
| MP2-HEATMAP-FETCH | (관찰) 11-타일 히트맵이 요약 화면에서 sector 상세 eager fetch(로드 시 1콜 추가). 계약 무변경·기능 정상 = **버그 아님**. 선제 최적화 지양(측정 우선). overview 11섹터 additive 부착 전환은 실 성능 데이터 확보 후 판단 | 관찰(성능) | 실측 성능 이슈 시 | 🔵 관찰 |
| MP2-COLOR-AUDIT | (C안) 앱 전면 up/down 색 관례 감사 — sector 외(TickerBar·breadth·concentration·시그널 등). sector는 MP2-SECTOR-COLOR로 한국 통일 완료. **착수 트리거 = sector 외에서 실제 색 뒤집힘/불일치 관찰 시**. 선제 감사 지양(측정 우선) | 관찰(UI 일관성) | 색 불일치 관찰 시 | 🔵 관찰 |

---

## News AV broad 백필 옵스 (2026-07-07)

> 배치1 마감(표적 복구 06-18/19 + 갭 07-04~06, 10호출) 세션 잔여. 근거 project_news_av_broad_track / PROGRESS.

| ID | Task | 분류 | 트리거 | Status |
|----|------|------|--------|--------|
| NEWS-AV-SANITIZE-METRIC | sanitize 발동 카운터/메트릭 부재 — 방어 계층별(provider `url>2000` skip · `_save_articles` 기사별 savepoint skip) 발동 통계 없이는 **"포이즌 미조우 vs sanitize 선차단" 구분 불가**. sanitize 유지 가치 판단의 근거로 추후 필요. (배치1 전 창 `skip=0` 로그는 있으나 provider단 선차단 건수는 별도 미집계 — `skip=0`이 "오염 무"인지 "provider가 이미 걸러냄"인지 판별 불가) | @backend/@infra | sanitize 유지·제거 판단 필요 시 | 🆕 저우선 |
| EVENTGROUP-WINDOW | `event_group_pipeline._build_base`가 `ChainNewsEvent` **전량(무윈도우)** 소비, `as_of = max(published_at)`. 데이터 누적 시 오래된 co-mention이 현재 내러티브를 희석(그룹 구성이 최신 신호만 반영 못 함). **날짜 윈도우(half_life 기반 컷오프 또는 최근 N일) 도입 검토** — as_of는 max라 전진하나 클러스터링 입력은 전체라 신선도 편차. | @backend | 그룹 내러티브 신선도 이슈 관측 시 | 🆕 저우선 |
| NEWS-AGG-TEST-ENV | `NewsAggregatorService.__init__`가 `FinnhubNewsProvider`를 즉시 생성 → **Finnhub 키 하드 의존**. 키 부재 환경(settings_test)에서 `ValueError` → savepoint 회귀 테스트(`test_aggregator_savepoint`) 포함 뉴스 계열 테스트가 **침묵 실패**(env 사유로 red). `__init__` 의존 지연/분리(lazy provider init) 또는 테스트에서 provider mock 격리 검토. | @backend/@qa | 뉴스 테스트 green baseline 필요 시 | 🏁 **종결 2026-07-13 (지시서⑦ S5, `3a781a5`)** — finnhub/marketaux 키 조건부 + provider 주입 인자. `test_aggregator_savepoint` env 부재(FINNHUB=[]/MARKETAUX=[]) green 확인. 키 관용화 테스트 3건 |
| MKX-MATCHSCORE-BACKFILL | 기존 저장 `NewsEntity.source='marketaux'` **7,148행 match_score 가 [0,1] 밖**(min 1.75·max 299.6·avg 35.7 — 모델 validator 0~1 위반). S4(`ba…` 지시서⑦)가 **쓰기 경로만** 정규화(100 saturation clamp) → **신규분만 정상**. 기존 7,148행은 `raw/100 clamp` 로 일괄 정규화하는 멱등 backfill 커맨드 필요(읽기 소비처=API serializer 뿐, co-mention 미사용이라 파급 낮음). | @backend | match_score API 노출 정합 필요 시 | 🆕 저우선(backfill 후보) |
| NEWS-URLNORM-IDQUERY | 🔴🔴 **긴급 — S3 이미 배포·활성(게이트 지나침).** 지시서⑨ 실측: 워커 PID 80710이 07-13 11:31 재기동으로 S3 코드(쿼리 전량 제거) **로드·활성**. 기존 저장분은 raw 보존이라 **아직 collapse 미발생(예방 단계)** 이나, **다음 수집 발화(collect_av_broad_news 07-14 01:00 UTC)부터** finviz.com/quote?t=TICKER(AV **1,675**개)·youtube ?v=(FMP 1,961) 등 **공유경로 URL이 붕괴** → 서로 다른 티커가 1건으로 병합돼 **co-mention 조작(허위 공동언급)**. 골든셋: (a+b) 100,268행(88.4%) IDENTICAL 필수, 실위험 22그룹/3,695행(youtube·finviz 2도메인 집중). **교정 = "tracking만 제거, id-쿼리 보존"(+Hybrid 도메인 규칙) — 07-14 01:00 UTC 전 완료 시 순수 예방.** 설계=`docs/news/urlnorm_idquery_survey_2026-07-13.md`. | @backend | **⑩ 즉시(다음 발화 전)** | 🏁 **종결 2026-07-13 (지시서⑩ Blocklist 베이스, `64c8589`)** — normalize id-쿼리 보존(utm_*·fbclid·gclid·ref만 제거). 골든셋 (a)+(b) 100,245행 IDENTICAL 불일치 0, collapse 22그룹 완전분리. STEP1 beat 20건 가역정지→배포→재활성. 기존 저장분 무손상(예방 성공). DECISIONS `[2026-07-13] NEWS-URLNORM-IDQUERY` |
| NEWS-URLNORM-HYBRID | Blocklist 베이스(⑩)가 **과소병합** 잔존: AMBIG 8,856(msn 렌더링 파라미터·finviz 뷰 파라미터 등)이 보존돼 dedup 덜 됨(가역·무해). Hybrid = 도메인별 규칙(예: msn 렌더링 파라미터 제거, finviz 뷰 파라미터 정리)으로 안전 정리. ambiguous key(cid·ocid·mod·amp·lang) 개별 재판정 포함. | @backend | dedup 정밀도 개선 필요 시 | 🆕 저우선(⑩ 후속 최적화) |
| MKX-URLNORM-BACKFILL | S3(지시서⑦)가 AV/FMP url 정규화 forward-only 적용 → 기존 저장 raw url 무변경. **지시서⑧ 재산정**: 잉여 3,954행 중 **안전 병합=139행뿐**(tracking만 빼도 동일=진짜 중복, 대부분 FMP 스토리지 위생), 나머지 3,815=가짜충돌(오병합 위험). **AV 관련 안전 병합=단 1행** → cross-provider co-mention 왜곡 노출 무시가능. backfill 저가치 + **NEWS-URLNORM-IDQUERY 정밀화 선결**. | @backend | 정규화 정밀화 후 + co-mention 교정 필요 시 | 🆕 저우선(저가치, 선결조건 有) |

---

## MP2-DELTA — 촉발 심화 축1(어제 대비 변화) (2026-07-03)

> MP2-DEEPEN(전조+원인) 완료 후 남은 심화 축. 근거 D-MP2-DEEPEN / STEP 0 af08007.

| ID | Task | 분류 | 트리거 | Status |
|----|------|------|--------|--------|
| MP2-DELTA | 축1 어제 대비 변화(델타) — regime 전환 · sector rank 이동 · anomaly 신규/소멸. **유일 신규 파생**(데이터 시계열은 완비: RegimeSnapshot previous_regime · SectorFlowSnapshot date별 · AnomalySignalLog triggered_at, 단 2날짜 비교 서비스 신규). 전조·원인(MP2-DEEPEN)보다 손이 감. 참조 D-MP2-DEEPEN | market_pulse 트랙 직접 | 다음 촉발 심화 슬라이스 | 🆕 착수가능 |

---

## MP2-DELTA 슬라이스 (2026-07-03)

> 촉발 심화 축1(어제 대비 변화). 근거 D-DELTA-CALC/SCOPE/YDAY.

| ID | Task | 분류 | 트리거 | Status |
|----|------|------|--------|--------|
| MP2-DELTA-S1 | 슬라이스1 = regime from→to(previous_regime 재사용) + sector 순위 델타(조회-시 파생) + DeltaCard "어제와 달라진 것". prod 0·마이그레이션 0 | market_pulse 트랙 | — | ✅ **done (421fefe)** |
| MP2-DELTA-S2 | 슬라이스2 = **anomaly 신규/소멸/해소** 델타 + 무발동일 표시. "어제"=**직전 발동일 대비**. D-DELTA-QUIET(옵션2 해소 명시) + R3 실측=판별 불가 → **5c-ii 폴백(무발동일 항상 quiet)**. anomaly_delta additive(4상태). 참조 D-DELTA-QUIET | market_pulse 트랙 | — | ✅ **done (b29067e)** ⇒ **MP2-DELTA 트랙 종결** |
| ANOMALY-RUN-EVIDENCE | (관찰 항목, 측정-우선) anomaly engine 실행 흔적(run-marker) 도입 시 D-DELTA-QUIET의 resolving 활성화 가능. 현재 AnomalySignalLog는 발동 행만 적재 → 무발동일 quiet로만 수렴. **실제 오독 사례 관찰 시 착수**(계약엔 resolving/resolved_rules 자리 이미 존재) | market_pulse 트랙 | 오독 관찰 | 👁 관찰 |

---

## MP2-TREND 슬라이스 — 멀티라인 시계열 (2026-07-06) — ✅ **트랙 종결 (2026-07-07)**

> 공용 MultiLineTrendChart + 적용 N곳. 근거 D-TREND-PLAN/BASELINE/TOOLTIP.
> **종결**: S1·S2·S3(R1) 전건 land(origin/main). ~~S4(z-이상도 뷰)는 **동면** — 트리거 B-1 land(Phase 5)까지 착수 금지 유지.~~ → S4 동면 해제(2026-07-10, B1-S2-FIRE) → **S4 land(2026-07-10) = MP2-TREND 트랙 재종결**. z-이상도 뷰는 703 소급 시계열 baseline 위에서 구현 완료.

| ID | Task | 분류 | 트리거 | Status |
|----|------|------|--------|--------|
| MP2-TREND-S1 | 1호 = 공용 `MultiLineTrendChart`(recharts, 크로스헤어+고정 리드아웃·반전축·범위/범례 토글, overlays 타입만) + 11색 팔레트 + sector_history rank additive + 섹터 순위 궤적. emphasis=서버 rank leaders/laggards(FE 델타 재계산 금지). prod 0·마이그레이션 0 | market_pulse 트랙 | — | ✅ **done (c1cdba4)** |
| MP2-TREND-S2 | 2호 = 전환일 오버레이 공용 계약(previous_regime≠regime 파생) + breadth 궤적(A/D + 기준선 MA20) + overlays.vlines·refSeries 렌더 + 델타 강조 복원(옵션 B, D-TREND-EMPHASIS 안전판 통과). 전부 조회-시 파생·계약 additive·마이그레이션 0 | market_pulse 트랙 | — | ✅ **land (7678ec2)** — pytest 신규6/api72·vitest 신규9/전체518·tsc0·mig0 |
| MP2-TREND-S3 | 3호(개정 R1) = **국면 재료 판정-거리 소형 다중**(옵션 B). z-score 전제 STEP 0 반증(classifier=raw 복합 룰, D-TREND-BASELINE-R1) → 룰-구동 7지표 raw 스파크라인 + rules.yaml 실제 컷 hlines + 판정거리. 세그먼트 [판정거리 | 이상도(z)🔒 예약탭](D-TREND-VIEWMODE). 컷 하드코딩 0(rules.yaml 단일소스). 조회-시 파생·마이그레이션 0 | market_pulse 트랙 | — | ✅ **land (R1, 코드머지 `8842531`, COLOR-STAGE2 CUT_STROKE 정합 포함)** — pytest 신규8/api80·vitest 신규8/전체526·tsc0·mig0. **트랙 마지막 슬라이스 → MP2-TREND 종결** |
| MP2-TREND-S4 | 4호 = **z-이상도 뷰** — 예약 placeholder → 실 뷰(절충안 격자형, D-S4-FORM). 전용 엔드포인트 `regime/zscore`(고정 소급 모집단 baseline·serve-time z·24h 캐시·다운샘플 57.1KB, D-S4-ENDPOINT/BASELINE). baseline 순수함수=ANALOG 재사용 단일소스 | market_pulse 트랙 | B-1 land(충족) | ✅ **land (2026-07-10, `monorepo/sess-s4`: BE `e418829` + FE `a9cb79b`)** — pytest 358→374(+16)·vitest 295→304(+9)·tsc0·mig0·health13/0·payload 57.1KB. **MP2-TREND 트랙 재종결** |
| S4-REBASE | z baseline μ·σ **재기준** — 라이브 축적분을 모집단에 포함해 잣대 갱신(현재 = 소급 703 고정). 소급 vintage(D-B1-VINTAGE)와 라이브 실시간 값의 분포 차이 흡수. **재기준 동반: 성분 상관 가족 재판정(현 판정=2단, FAM1{ddown,vix,vix3m}·FAM2{9성분}, 가족간|ρ|0.178)+analog 카드 문턱(K·τ_radius·τ_alert) 재산정** | market_pulse 트랙 | **라이브 축적 1년 도달** | 🕒 예약(데이터 게이트) |
| A-S0 | analog 사후수익 SPY EOD 보존 예외 — 롤링 purge(`cleanup_old_data` 365일 blanket)가 백필 SPY 매주 삭제(683→199). `PRESERVED_INDEX_SYMBOLS={SPY}` exclude(방식 나, 모델 무변경). 참조 D-ANALOG-SPY-RETENTION | market_pulse 트랙 | — | ✅ **land (2026-07-13, `monorepo/sess-A-spy-restore` `01c99b1`)** — 회귀 3·마이그레이션 0 |
| A-PREP | SPY EOD 3년 재백필 — `backfill_spy_eod`(shared FMP 래퍼·dry-run 기본·멱등). 683 사후수익 모집단 회복. A-S0 의존(재소실 방지) | market_pulse 트랙(백필 실행=병진 수동 --commit) | **커맨드 land → --commit 병진 대기** | 🔵 **커맨드 land + dry-run 완료 (2026-07-13, `9dc663c`)** — prod dry-run: 신규 500행(2023-07-14~2025-07-11) → 683/683 완전 회복 전망. **--commit 병진 수동 대기**. **Slice B 지평 커버리지 실측(청정 FMP 거래일)**: ≤20d=**682/683**(1 비-FMP일)·**+60d=674/683**(9 우변절단 2026-04-15~04-24, 1.3% — 사이클2 "최근2개월" 과대추정 정정). **265vs250 차=주말/휴장 15행**(DB yfinance엔 有·FMP 거래일엔 無, 무해) |
| INDVAL-PURGE-LANDMINE | **동류 지뢰 등재** — `cleanup_old_data`가 IndicatorValue 3년 백필도 blanket 삭제 중(A-S0는 SPY만 보존). 현재 analog 벡터=stored(RegimeSnapshot.inputs)라 무영향이나 **S4-REBASE 재합성 시 71% 결손 재현**. 해소=A-S0 동형(시리즈/코드 보존 예외) | market_pulse 트랙 | **S4-REBASE 착수 시 선행** | 🕒 예약(재합성 게이트) — common-bugs [보존 함정] 등재 |
| S4-EXPAND | z 뷰 **카드 탭 확대 뷰 + 정렬 토글**(|z|순 ↔ 지표순) — S4 범위 밖(격자형만 land). 종합 이상도 지수도 후보 | market_pulse+FE 트랙 | **MP2-ANALOG 세션에서 순위/확대 시각 어휘 구축 시 함께** | 🕒 예약(어휘 게이트) |

## Carousel LLM 채움 (LLMFILL / 2026-07-09)

> 근거 DECISIONS `[2026-07-09] D-LLMFILL`. CAROUSEL-BUILD(`24b0e47`)가 심은 3키 placeholder(thesis·perspectives·risk)를 EOD-bake 조립 직후(삽입 지점 A)에 shared LLM 래퍼 경유로 채운다. 부분 실패 내성(카드별 개별 호출) + `pipeline_meta.llm_fill` 관측(#46형 검문소 짝).

| ID | Task | 분류 | 트리거 | Status |
|----|------|------|--------|--------|
| LLMFILL-BUILD | `packages/shared/stocks/llm/` 신설(card_fill_prompt + fill_service) + baker 삽입 지점 A additive 배선 + item 가드 테스트. **✅ done `9f2355d`** (scoped 161: 기존 150 IDENTICAL + 신규 11, 실호출 0, diff=자기 구획 6파일, ff push). 편차 1건=닫힌 집합 격리 patch(→ PM-CLOSEDSET-LLMFILL) | @backend (shared/stocks 구획) | 완료 2026-07-09 | ✅ done |
| PM-CLOSEDSET-LLMFILL | `pipeline_meta` 닫힌 집합 단언(test_eod_issuance_log)에 `llm_fill` **정식 등록** + `_bake_patches` 격리 patch 제거(issuance_verified 등록 방식 동형). BUILD의 구조 충돌 편차 정리 | @backend (소형) | 착수가능 | 🆕 등재 |
| LLM-GUARD-3 | 외부-LLM-직접호출 **가드 신설**(BOUNDARY-LLM 슬라이스③ 연동 — 코어 land 후 회귀방지). 본 슬라이스(LLMFILL) 스코프 분리분. 트리거: **다음 shared/llm 접점**(BOUNDARY-LLM 트리거 (b) 누적 또는 burn-down 착수) | @backend (BOUNDARY-LLM 연동) | 다음 shared/llm 접점 | 💤 등재(트리거 게이트) |
| LLMFILL-OBSERVE | LLMFILL-BUILD land 후 첫 무인 bake 관측. **✅ 종결·판정 (a) 전건 성공**(07-09 bake filled 10/10·실패 0·$0.001001·6832tok, 파일↔스냅샷 일치, 7 core 무결, IssuanceLog 10/10 ok, 홈 렌더·콘솔0, fundamental=null 정직 실증). D-LLMFILL 추기 | 관측(dashboard 디렉션) | 완료 2026-07-10 | ✅ done |
| LLMFILL-FUND-MATERIAL | **재료 확장으로 `fundamental` 채움률 개선(수리 아님)**. 관측(MGMT-BATCH-9): `fundamental=null`은 **영구 결손이 아니라 조건부** — 07-09 채움 **0/10**, 07-10 채움 **1/10**. 날조 억제 설계대로 작동(재료 부족 시 채우지 않음 = 정직 null, D-LLMFILL "fundamental=null 정직" 승계). 개선 경로 = **투입 재료(펀더멘털 컨텍스트) 확장**이지 프롬프트/파서 수리가 아님(현행 동작은 결함 아님). 착수 시 STEP 0 = null 사유 실측(재료 부재 vs 게이트 과보수) | @backend (shared/stocks 재료) | 재료 확장 우선순위 결정 시 | 💤 등재(재료 게이트) |

---

## MGMT-BATCH-7 후속 (theme-heat 감사·이주 + dedup 부채 / 2026-07-09)

> 근거 DECISIONS D-THEMEHEAT-AUDIT·D-OWN-HOME + common-bugs #44 강화·#49·#50. theme-heat land 게이트 + 선존 union 중복 정산 + stray 문서 회수.

| ID | Task | 분류 | 트리거 | Status |
|----|------|------|--------|--------|
| THEMEHEAT-LAND-GATE | `sess-cs-theme-heat` land 전 **mgmt 선행 정산 세션 필수** — ① 브랜치 #47 → 실측+1 재번호 ② mgmt 밖 등재 결정 3건(결정7·8·9) 정합 검토 ③ 메타 4종 union 중복 #44 전수 스캔. **단순 rebase-push 금지** | mgmt(chain_sight) | theme-heat land 착수 시 | 🔒 게이트(land 전 필수) |
| PROGRESS-DEDUP-MONITOR | PROGRESS 활성 Monitor 블록 **×5**(2939→5482자, 비-동일본) per-copy superset 검증 후 **5→1**. **blind collapse 금지**(#44 ⑶) | mgmt(dedup) | monitor-rebuild 트랙 접점 | 💤 트리거 게이트 |
| PROGRESS-DEDUP-MP2TREND | PROGRESS 활성 MP2-TREND Slice 3 블록 **×2**(2009 vs 2076자, 비-동일본) 동형 superset 검증 후 2→1 | mgmt(dedup) | MP2-TREND 트랙 접점 | 💤 트리거 게이트 |
| STRAY-DOCS-13 | primary 미추적 **13건** 트랙별 회수/폐기 분류(chain_sight redesign 6·thesis 2·trading_bot 2·mp 1·기타 2=.superpowers·worktree forensic) | mgmt(소형) | 착수가능 | 🆕 등재 |
| MGMT-WT-SWEEP | mgmt worktree 6종 tip **전수 측정 → 머지 완료분 제거 후보 보고**(제거는 사용자 수동). **STEP 0 실측(2026-07-13, base origin/main `3b50612`)**: 6종 **전부 ahead=0 = origin/main 완전 머지 = 전량 제거 후보** — sess-mgmt-flush `cf82fe9`·sess-mgmt-flush3 `b8b15cb`·sess-mgmt-ledger `cdbf79e`·sess-mgmt-ledger-s3 `3062bb0`·sess-mgmt-xapp-rule `079f233`·sess-mgmt-v2 `f892d90`. 제거 절차 = `git worktree remove <path>` + `git branch -d monorepo/<b>`(조상 검증 통과 시). **본 세션은 등재·측정만**(실 제거는 사용자 판단·수동, 활성 사용 여부 최종 확인 후) | mgmt(정리) | 사용자 제거 승인 시 | 💤 등재(측정 완료·제거 대기) |
| NEWS-ORPHAN-ASSIGN | 뉴스 무소속 재료 트랙 배정 — NT-2b(미핸드오프)·NT-6(보류)·뉴스 β A(파킹). **결정은 디렉터 사이클**. ※**갱신(2026-07-09, D-DASH-BFF)**: D3(뉴스 축 소비 표면)의 거처 블로커는 **BFF 배치로 해제**(apps/dashboard가 read 소비만) → 잔존 사유는 **NT-2b 등 뉴스 품질 작업 소유 배정**뿐 | 결정 안건 | 디렉터 결정 사이클 | 🕓 대기(결정) |
| BOUNDARY-EXT-5 | shared 미경유 외부 API 직접 호출 **5건**(NEWS-SURVEY N2: chain_sight neo4j_loader×2·insider_tasks·sensitivity_tasks·market_pulse fmp_weights) 처분. **결정은 디렉터 사이클** | 결정 안건 | 디렉터 결정 사이클 | 🕓 대기(결정) |
| PROVIDER-DUAL | 뉴스 provider 3종(Finnhub·Marketaux·AlphaVantage) `services/news/providers` 잔류 vs shared 승격 결정. **결정은 디렉터 사이클** | 결정 안건 | 디렉터 결정 사이클 | 🕓 대기(결정) |

---

## News Axis Phase 1 (하이브리드 뉴스 축 / 2026-07-09)

> 근거 DECISIONS D-NEWS-AXIS(표면 S1×경로 D3)·D-DASH-BFF(apps/dashboard BFF)·소유권 지도 v2 AMEND(apps/dashboard/**). 홈 상단 압축 스트립 + 전용 응축 API. dashboard 트랙 소유.

| ID | Task | 분류 | 트리거 | Status |
|----|------|------|--------|--------|
| NEWSAXIS-CONTRACT | 응축 API **응답 계약 설계** — 관련성 정의·가중, 동일 사건 접기 기준, 관계망 배지 규칙, 캐싱 정책. **✅ 종결**(D-NEWSAXIS-CONTRACT 4항 등재: F2 관련성·자체 접기+제목핵심어 안전핀·RelationConfidence θ배지·15/30 캐싱 + item 계약) | 결정 안건(dashboard) | 완료 2026-07-09 | ✅ done |
| NEWSAXIS-BUILD | `apps/dashboard` BFF(Slice1) + FE 스트립 S1(Slice2). **✅ done `90b04fe`** — BFF θ배지·티어 F2·자체접기 + FE 홈 상단 스트립, scoped BE 12·FE 6·config 예외 2줄. **실가동 확인 07-10**(스트립 라이브: T2/T3/T4 칩·`AAPL↔GOOGL` 배지 발화·카드 LLM 채움 렌더). 후속=STRIP-FOLD-TUNE·URL-V1-ALIGN·STRIP-BADGE-VARIETY | @backend + dashboard FE | 완료 2026-07-10 | ✅ done |
| STRIP-FOLD-TUNE | 접기 안전핀 강화 3종(D-STRIP-FOLD-TUNE): 일반 금융어 stopword·라운드업 배제(언급 심볼 수 상한)·그룹 크기 상한. **AAPL "+10건" 오접합 fixture 박제 의무**. 임계 상수는 STEP 0 실데이터 결정(하드코딩 금지). **✅ done `62eec71`** — 실서빙 실효 채증(MGMT-BATCH-9): "+10건"(오접합)→"+2건"(=`MAX_GROUP_SIZE−1` 상한 준수), 전 칩 ≤+2건. 검증 = live DB×배포 코드 직접 실행(JWT 만료로 서비스-레벨 갈음, 렌더 미변경 등가). 잔여 "+2건" 정밀도는 도그푸딩 관찰 지속, 근본 해소=v2 LLM 클러스터링 예약(D-STRIP-FOLD-TUNE 추기) | @backend (apps/dashboard in-zone) | 완료 2026-07-10(land) | ✅ **done** |
| STRIP-BADGE-VARIETY | 칩별 관련 엣지 다양화 — 동일 `seed↔seed` 배지(AAPL↔GOOGL) 반복 완화(chip이 seed 심볼 언급 시 seed↔seed 최강 선택되는 편향). 외부 노드 연결 우선 등 개선 | dashboard 트랙(개선) | 다음 strip 접점 | 💤 등재(트리거 게이트) |
| URL-V1-ALIGN | BFF 경로 `/api/dashboard/` → `/api/v1/dashboard/` 관례 정렬 + FE stripService의 base 우회(`/api/v1` 제거 로직) 제거. ~~TUNE과 동승 가능~~(TUNE은 `62eec71`로 이미 land). **config 접촉 사전 정당화**: D-DASH-BFF config 예외 범위가 URL-V1-ALIGN 포함으로 확장됨(MGMT-BATCH-9) — root `urls` include 경로 1줄 수정은 내재 산출물로 허용, 그 외 config 변경은 HALT. 착수 시 diff 원문 채증 의무 | @backend + dashboard FE | 다음 apps/dashboard 접점 | 💤 등재(트리거 게이트) |
| HEALTH-13TH-IDENT | sv health 검사 항목 **12→13 증가분** 정체 확인·기록(monitor refresh 신선도 = MON-P2-BEAT 귀속 추정, 실측 확정) | mgmt(소형) | 착수가능 | 🆕 등재 |

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

## NT-OPS-HCHECK-REDESIGN — health_check `origin/main-hash` 체크 재설계 [resolved 2026-07-02]
- 상태: **resolved** (D-OPS-HCHECK-B2). 해시 대조 → 시간기반(PROGRESS committer-ts, 임계 M=72h) 교체. 순수함수 `is_progress_stale` 분리 + 자기검증 2방향(`tests/test_health_check_freshness.py`) + 전체 health_check 10 OK.
- 원증상: fast-main(~20min land)+self-ref로 매 세션 blocking ERROR 오발 → resync land 게이트 HALT.
- ※ 병렬 브랜치 주의: `monorepo/sess-mgmt-v2`(미land, 0126af6)가 이 항목을 **open**으로도 추가함 → PHASE 2에서 v2 rebase·land 시 union-merge 중복 → **dedup 필요**(open 제거, 본 resolved 유지).

## NT-OPS-HCHECK-GATEINFO — health_check gate/info 2계층 분리 (C안, 후보)
- 내용: blocking gate(코드diff·경계·동결·arch guard) vs 비-blocking info(캐시 신선도)로 출력 모델 재구조화.
- 이유: 캐시성 체크가 늘면 개념적으로 가장 깨끗(PROGRESS=캐시 규약을 구조에 반영).
- γ규율: 지금은 소비자 미확정 → 짓지 않음. 트리거: 캐시성 blocking 후보 체크 ≥3 누적 시 결정 사이클.
## NT-P1-DELEGATE — Phase 1 발행 로그 + EOD-bake 추천 생산 → Dashboard 앱 위임
- 상태: ops 측정·설계·경계판정 완료. 빌드 실행은 Dashboard 프로젝트 소관(기능 코드).
- 스펙(단일 출처): HANDOFF_p1_recprod_spec.
- 확정: D-P1-GRAIN(wide 형제대칭, key=(stock,signal_date,signal_tag), horizon=컬럼, user_id nullable 예약, unique user 제외) · D-P1-CONF(B+ 발행값 캡처: confidence enum + composite_score float, 신규 생산 0).
- 부착: 모델=SignalAccuracy 형제 / bake=eod_json_baker _build_dashboard_json return / write=Stage6·baker 기존 표면(신규 표면 0) / serve=EODDashboardView 무변경 / Phase5 join 정합.
- open: #4 채점 모드(raw/excess, Phase 5) · user_id 스코프(멀티테넌트 시 unique 확장).
- 참고: D-P1-GRAIN·D-P1-CONF의 DECISIONS.md append는 Dashboard 빌드 커밋에 포함(원자적 land).

## OPS-LOG-FLOOD — celery-worker-error.log 폭주 (등재만, 2026-07-03)
- 상태: **등재만**(수리 안 함, 사용자 지시). 긴급도 낮음.
- 관찰: worker-error.log에 모든 INFO + `missed heartbeat`(고빈도) + 15분 regime 등 전량 적재 → 126MB, ~2,700줄/h.
- 영향: tail-window 로그 도구 오탐 유발(#28 verify E1의 근인). verify는 경계-timestamp 스캔으로 회피 완료 → 판정 정확도 무영향.
- 후속 트리거: 디스크 압박(수백 MB↑) 또는 타 tail-window 도구 오탐 재발 시. 방안 = 로그 레벨/분리/회전, heartbeat 억제.
- 상세: `docs/features/chain-sight/PR_ops_verify_enhancement.md`(등재 절).

## OPS-WORKTREE-ISOLATION — pair 작업 worktree 격리 (등재, 2026-07-04)
- 상태: 등재. **트리거 = pair→main 최종 통합 후** 착수(통합 전엔 pair가 공유 dir 점유 필요라 격리 시 워커 코드 갈림).
- 사건(근거): 2026-07-04 13:13:25 외부 세션이 공유 작업트리 `/Users/byeongjinjeong/Desktop/stock_vis`를 `git checkout origin/main`(detached 7c2f186)으로 탈취 → HEAD가 pair 이탈 + celery-worker 13:13:51 origin/main 코드로 재시작(aggregate 태스크 부재 = 다음 틱 unregistered 위험). 복구: pair(c690307) checkout + 워커 재기동(71696). pair/origin 무손상.
- 근본 원인: 다중 세션이 단일 작업트리(=celery 워커 코드베이스) 공유. 메모리 lesson "공유 main 작업트리 직접 편집 금지"의 구조적 미비(수동 규율만으론 동시 checkout 못 막음).
- **ADR 재평가 트리거(실증)**: DECISIONS:1338 "다중 세션 = **소프트 강제**(worktree 격리 + 계약 헤더, 훅 미도입 — 차선 이탈 반복 시 국소 승격)". 이번 사건(reflog `7c2f186 @2026-07-04 13:13:25 checkout origin/main`)이 소프트 강제가 못 막은 **첫 실증 이탈** → 통합 후 "국소 승격"(hook/worktree 물리격리) 재평가 대상.
- 07-05 후속: worker(71696) + **beat(36421→38604 재기동, 13:13:51 origin/main 재시작분 정정)** 양자 pair코드 정합. 밤사이 자율 틱 period 07-04 적립 = 복구 무인 검증.
- 방안: 활성 작업 브랜치를 `git worktree`로 분리(SESSION_CONTRACT worktree 규율 정합), 워커는 안정 브랜치 dir 고정 import.
- 통합 전 방어(잠정): 세션 시작 시 HEAD·워커 시작시각 대조 수동 스모크 + flag-on/merge 전 재확인(P-0 규율에 편입 검토).
- **2026-07-06 승격 = 대기열 선두**: 트리거("pair→main 통합 후") D2 v5.1 결정 ⑩로 충족 임박. 재발 2차 봉인 추가 — nightly `worker_sync.sh`가 sv-worker-runtime을 origin/main으로 리셋 → 기본 워커가 미머지 pair 태스크 미보유(unregistered) → 궤적 07-05 영구 갭. 遠因 = 본 트리거를 "통합 후"로 잡아 통합 전 재발을 못 막음. 착수는 D2 관찰 창과 겹치지 않게 사용자 호출(§7). 방안 = 워커 runtime을 안정 브랜치 고정 + 활성 트랙 worktree 물리격리 승격(DECISIONS:1338 소프트강제 재평가).
## NT-REHOME-GRAPH — graph_analysis CUT [resolved 2026-07-03]
- 상태: **resolved** (D-REHOME-GRAPH). 휴면 상관관계 엔진(1444줄) 제거. STAGE 1=drop-migration 0002 prod 적용(5테이블 DROP, 0 rows) / STAGE 2=INSTALLED_APPS+코드 git rm.
- 검증: makemigrations --dry-run=No changes · check 0 · health 10 · arch 7 · 회귀 delta 0(선존 chainsight 5실패 무관). 복구 SHA f892d90.
- 후속(무해·선택): django_migrations 고아행 정리 · STAGE1 브랜치 삭제 · CLAUDE.md/sub_claude_md 서술 doc 위생.
