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
| TRASH-11 | **worktree 2건 거취 — DEAD 확정·remove 완료** (TR-7/8 정정). 기존 ALIVE 판정은 **stale 로컬 main 기준 오판**이었음. TR-8 STEP1: unique 커밋 5건(f483634/d4a9690/ce0be51/0b8399a/ef9d064) **전건 origin/main(d5212d4) REACHABLE = DEAD**. `sess-mgmt-phase1-catalog`·`sess-mp-phase1-cleanup` 디렉토리 소멸 + worktree registry 제거 완료(세션 간 외부 선제거, prune 정합). **잔여 결정**: 브랜치 2건 삭제 — 커밋이 origin/main 도달이나 **로컬 main 미도달**이라 `-d` 거부 예상 → 사용자 수동 `-D` 또는 `pull` 후 `-d`. + `sess-mp-kl-f1f3` 머지 시 `82afddb`(TASKQUEUE 9건) 중복은 main `cb5473e`와 동일 → 충돌 시 main 채택. **push/pull 통합 결정과 묶음**. | orchestrator | - | todo | 브랜치 삭제 + push/pull 통합 |
## market_pulse v2 Phase 1 잔여 (2026-06-07 카탈로그 역산 확정)

> 근거: `DECISIONS.md` "## [2026-06-07] Phase 1 PR 카탈로그 역산 확정". 백엔드 A~J done(J는 I 흡수), FRED fetcher done, Translation/Playbook은 Phase 1.5/1.6 이관(범위 외). 본 표는 출시 전 정리할 6 트랙.

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
